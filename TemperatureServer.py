#!/usr/bin/python
##################################################################
# TEMPERATURE SERVER
# DESC: The temperature server is designed to store and provide stable
# temperature pressure and humidity information
# Author: Jonathan L Clark
# Date: 7/4/2020
##################################################################
# git clone https://github.com/adafruit/Adafruit_Python_DHT.git
# pip install smbus
# pip install Flask
# pip install numpy
# python -m pip install --user numpy scipy matplotlib ipython jupyter pandas sympy nose
# Use this command to start this on boot
# sudo -H -u pi python /home/pi/NetworkTemp/TemperatureServer.py &
# sudo apt-get install build-essential cmake pkg-config
# sudo apt-get install libjpeg-dev libtiff5-dev libjasper-dev libpng12-dev
# sudo apt-get install libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
# sudo apt-get install libxvidcore-dev libx264-dev
# sudo apt-get install libgtk2.0-dev
# sudo apt-get install libatlas-base-dev gfortran
# sudo apt-get install python2.7-dev
# cd ~
# wget -O opencv.zip https://github.com/Itseez/opencv/archive/3.0.0.zip
# unzip opencv.zip
# wget -O opencv_contrib.zip https://github.com/Itseez/opencv_contrib/archive/3.0.0.zip
# unzip opencv_contrib.zip
# wget https://bootstrap.pypa.io/get-pip.py
# sudo python get-pip.py
# sudo pip install virtualenv virtualenvwrapper
# sudo rm -rf ~/.cache/pip
# nano ~/.profile
# # virtualenv and virtualenvwrapper
# export WORKON_HOME=$HOME/.virtualenvs
# source /usr/local/bin/virtualenvwrapper.sh
# mkvirtualenv cv
# pip install numpy
# export WORKON_HOME=$HOME/.virtualenvs
# export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3
# export VIRTUALENVWRAPPER_VIRTUALENV=/usr/local/bin/virtualenv
# source /usr/local/bin/virtualenvwrapper.sh
# export VIRTUALENVWRAPPER_ENV_BIN_DIR=bin  # <== This line fixed it for me
# workon cv
# cd ~/opencv-3.0.0/
# mkdir build
# cd build
# cmake -D CMAKE_BUILD_TYPE=RELEASE \
#    -D CMAKE_INSTALL_PREFIX=/usr/local \
#    -D INSTALL_C_EXAMPLES=ON \
#    -D INSTALL_PYTHON_EXAMPLES=ON \
#    -D OPENCV_EXTRA_MODULES_PATH=~/opencv_contrib-3.0.0/modules \
#    -D BUILD_EXAMPLES=ON ..
# rc.local
# sudo -H -u pi python3 /home/pi/NetworkTemp/TemperatureServer.py &

try:
    from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
    from threading import Thread
    import smbus
    import socket
    import time
    import Adafruit_DHT
    import flask.json
    import os
    import numpy as np
    import time
    import json
    import requests
    import subprocess
    import sqlite3
    from sqlite3 import Error
    from flask import Flask, request, redirect
    from flask import Response
    from flask import jsonify
    from datetime import datetime
except Exception as ex:
    print(str(ex))
    file = open("/home/pi/errors2", 'w')
    file.write(str(ex))
    file.close()

DB_FILE = "/home/pi/temperature_data.db"
USER_DIR = os.path.expanduser("~")

PATH_TO_CERT = USER_DIR + "/.security/c039a05d5e-certificate.pem.crt"
PATH_TO_KEY = USER_DIR + "/.security/c039a05d5e-private.pem.key"
PATH_TO_ROOT = USER_DIR + "/.security/AmazonRootCA1.pem"

RECORD_RATE_SEC = 1800
STARTUP_TIME = 20
READ_DELAY = 10

OUTDOOR_SENSOR_IP = "http://192.168.1.191"

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def control_post():
    global temp_sensor
    output = jsonify(temp_sensor.data)
    return output

class TemperatureSensor:
    def __init__(self):
        # Create AWS connection
        self.shadow = {
            "state": { "desired": { "garage_temp" : -1.0, "garage_humid": -1.0, "garage_pressure" : -1.0, "outdoor_temp" : -1.0, "outdoor_humid" : -1.0, "system_temp" : -1.0, "indoor_tempC" : -1, "indoor_humid" : -1, "indoor_pressure" : -1, "indoor_cpu" : -1, "motion" : 0, "garage_door" : 0 } }
        }
        self.setup_aws()
      
        try:
            # Parse command line parameters.
            sensor_args = { '11': Adafruit_DHT.DHT11,
                            '22': Adafruit_DHT.DHT22,
                            '2302': Adafruit_DHT.AM2302 }
            self.sensor = sensor_args['11']
            self.pin = '4'
            self.data = {"garage_temp"   : 0.0, "garage_humid"  : 0.0, "garage_pressure" : 0.0, 
                         "outdoor_tempf" : 0.0, "outdoor_humid" : 0.0, "system_temp"     : 0.0, 
                         "indoor_tempC"  : 0.0, "indoor_humid"  : 0.0, "indoor_pressure" : 0.0, 
                         "indoor_cpu"    : 0.0, "motion"        : 0,   "garage_door" : 0,
                         "garage_temp2"  : 0.0, "garage_temp3"  : 0.0, "garage_pressure1" : 0.0}
            
            thread_functions = [self.regular_read_dht11, self.regular_read_mpl3115a2, self.GetOutdoorTemps, 
                                self.run_server, self.data_processor, self.GetIndoorTemps, self.monitor_garage_sensor, self.monitor_seismometer]
            
            for thread_func in thread_functions:
                newThread = Thread(target = thread_func)
                newThread.daemon = True
                newThread.start()

        except Exception as ex:
            file = open("/home/pi/errors", 'w')
            file.write(str(ex))
            file.close()
      
    def setup_aws(self):
        try:
            self.shadowClient = AWSIoTMQTTShadowClient("TemperatureServer")
            self.shadowClient.configureEndpoint("a2yizg9mkkd9ph-ats.iot.us-west-2.amazonaws.com", 8883)
            self.shadowClient.configureCredentials(PATH_TO_ROOT, PATH_TO_KEY, PATH_TO_CERT)
            self.shadowClient.configureConnectDisconnectTimeout(10)  # 10 sec
            self.shadowClient.configureMQTTOperationTimeout(5)  # 5 sec
            self.shadowClient.connect()
            self.device_shadow = self.shadowClient.createShadowHandlerWithName("TemperatureServer", True)
        except:
            print("Error setting up AWS retrying...")
            time.sleep(1)
            self.setup_aws()
    
    # Validates that there is data in the sqllite database file
    def test_db(self):
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT * FROM environment")
        
        rows = cur.fetchall()
        
        for row in rows:
            print(row)
        cur.close()
        
    # Writes the current data to the sql database      
    def write_db(self):
        conn = None
        timestamp = time.time()
        try:
            conn = sqlite3.connect(DB_FILE)
            
            #"indoor_tempC" : -1, "indoor_humid" : -1, "indoor_pressure" : -1, "indoor_cpu" : -1
            sql_create_table = """ CREATE TABLE IF NOT EXISTS environment (
                                        time_stamp text,
                                        system_temp float,
                                        garage_temp float,
                                        garage_humid float,
                                        garage_pressure float,
                                        outdoor_tempf float,
                                        outdoor_humid float,
                                        indoor_tempC float,
                                        indoor_humid float,
                                        indoor_pressure float,
                                        indoor_cpu float
                                    ); """
                                    
            insert = ''' INSERT INTO environment(time_stamp,system_temp,garage_temp,garage_humid,garage_pressure,outdoor_tempf,outdoor_humid,indoor_tempC,indoor_humid,indoor_pressure,indoor_cpu)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?) '''
            c = conn.cursor()
            c.execute(sql_create_table)
            conn.commit()
            data = (timestamp, self.data["system_temp"], self.data["garage_temp"], self.data["garage_humid"], self.data["garage_pressure"], self.data["outdoor_tempf"], self.data["outdoor_humid"],self.data["indoor_tempC"], self.data["indoor_humid"], self.data["indoor_pressure"], self.data["indoor_cpu"])
            c.execute(insert, data)
            conn.commit()
            c.close()
            print("Saved temperature to database...")
        except Error as ex:
            print("Unable to write to database: " + str(ex))
    
    # Monitors the seismometer in the garage for new data    
    def monitor_seismometer(self):

        UDP_IP = "0.0.0.0"
        UDP_PORT = 5153
    
        sock = socket.socket(socket.AF_INET, # Internet
                   socket.SOCK_DGRAM) # UDP
        sock.bind((UDP_IP, UDP_PORT))
        while (True):
            data, addr = sock.recvfrom(512) # buffer size is 1024 bytes
            #print(len(data))
            splitData = data.decode('utf-8').replace(" ", "").split(",")
            accXPoints = []
            accYPoints = []
            accZPoints = []
            recordStage = 0
            timestamp = float(time.time())
            for dataValue in splitData:
                if "AccX" in dataValue:
                    values = dataValue.split(':')
                    value = float(values[len(values)-1])
                    accXPoints.append(value)
                elif "AccY" in dataValue:
                    values = dataValue.split(':')
                    value = float(values[len(values)-1])
                    accYPoints.append(value)
                    recordStage += 1
                elif "AccZ" in dataValue:
                    values = dataValue.split(':')
                    value = float(values[len(values)-1])
                    accZPoints.append(value)
                    recordStage += 1
                elif ":" in dataValue:
                    if "Pressure" in dataValue:
                        values = dataValue.split(':')
                        value = float(values[len(values)-1])
                        self.data['garage_pressure1'] = value
                    elif "Temp2" in dataValue:
                        values = dataValue.split(':')
                        value = float(values[len(values)-1])
                        self.data['garage_temp2'] = value
                    elif "Temp" in dataValue:
                        values = dataValue.split(':')
                        value = float(values[len(values)-1])
                        self.data['garage_temp3'] = value
                else:
                    value = float(dataValue)
                    if recordStage == 0:
                        accXPoints.append(value)
                    elif recordStage == 1:
                        accYPoints.append(value)
                    elif recordStage == 2:
                        accZPoints.append(value)
            accXData = []
            accYData = []
            accZData = []
            for x in range(0, len(accXPoints)):
                dataPoint = {"time" : timestamp - ((len(accXPoints) - x) * 0.2), "value" : accXPoints[x]}
                accXData.append(dataPoint)
            
            for x in range(0, len(accYPoints)):
                dataPoint = {"time" : timestamp - ((len(accYPoints) - x) * 0.2), "value" : accYPoints[x]}
                accYData.append(dataPoint)
            
            for x in range(0, len(accZPoints)):
                dataPoint = {"time" : timestamp - ((len(accZPoints) - x) * 0.2), "value" : accZPoints[x]}
                accZData.append(dataPoint)
            
    
    # Monitor's the garage for activity
    def monitor_garage_sensor(self):
        UDP_IP = "0.0.0.0"
        UDP_PORT = 3030
    
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        sock.bind((UDP_IP, UDP_PORT))
        while (True):
            data, addr = sock.recvfrom(4) # buffer size is 1024 bytes
            #print("received message: %s" % data)
            if data[0] == 0xcd:
                if data[1] > 0:
                    print("Motion event")
                    self.data["motion"] = 1
                else:
                    self.data["motion"] = 0
                distValue = data[2] | (data[3] << 8)
                if distValue < 600:
                    self.data["garage_door"] = 1
                else:
                    self.data["garage_door"] = 0
                #if dataSet["motion"] == 1 or dataSet["garage"] == 1:
                #    RecordGarageStats()    
        
    # Regularly read the dht11
    def regular_read_dht11(self):
        while (True):
            self.read_temp_humid()
            time.sleep(READ_DELAY)

    # Regularly read data from the mpl3115a2
    def regular_read_mpl3115a2(self):
        while (True):
            self.read_mpl3115a2()
            time.sleep(READ_DELAY)

    # Gets the outdoor temperature for the log file
    def GetOutdoorTemps(self):
        while (True):
            try:
                response = requests.get(OUTDOOR_SENSOR_IP)
                data = json.loads(response.text)
                self.data["outdoor_tempf"] = data["temperature"]
                self.data["outdoor_humid"] = data["humidity"]
            except Exception as e:
                print("Except: " + str(e))
            time.sleep(RECORD_RATE_SEC)
            
    # Gets the outdoor temperature for the log file
    def GetIndoorTemps(self):
        while (True):
            try:
                response = requests.get('http://192.168.1.14:5000')
                data = json.loads(response.text)
                self.data["indoor_tempC"] = data["temp"]
                self.data["indoor_pressure"] = data["pressure"]
                self.data["indoor_humid"] = data["humid"]
                self.data["indoor_cpu"] = data["cpu_temp"]
            except Exception as e:
                print("Except: " + str(e))
            time.sleep(RECORD_RATE_SEC)

    # Custom callback
    def custom_callback(self, data, parm1, parm2):
        pass # Do nothing
   
    # Process the temperature, humidity and other data
    def data_processor(self):

        while (True):
            try:
                now = datetime.now()
                time.sleep(STARTUP_TIME)
                print("Send shadow")
                out = subprocess.Popen(['vcgencmd', 'measure_temp'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                stdout,stderr = out.communicate()
                system_temp = None
                system_temp_str = stdout.decode('utf-8').replace("'C\n", "").split('=')
                if len(system_temp_str) == 2:
                    system_temp = float(system_temp_str[1])
                    self.data["system_temp"] = system_temp
                self.shadow["state"]["desired"]["garage_temp"] = self.data["garage_temp"]
                self.shadow["state"]["desired"]["garage_humid"] = self.data["garage_humid"]
                self.shadow["state"]["desired"]["garage_pressure"] = self.data["garage_pressure"]
                self.shadow["state"]["desired"]["outdoor_temp"] = self.data["outdoor_tempf"]
                self.shadow["state"]["desired"]["outdoor_humid"] = self.data["outdoor_humid"]
                self.shadow["state"]["desired"]["indoor_tempC"] = self.data["indoor_tempC"]
                self.shadow["state"]["desired"]["indoor_pressure"] = self.data["indoor_pressure"]
                self.shadow["state"]["desired"]["indoor_humid"] = self.data["indoor_humid"]
                self.shadow["state"]["desired"]["indoor_cpu"] = self.data["indoor_cpu"]
                self.shadow["state"]["desired"]["motion"] = self.data["motion"]
                self.shadow["state"]["desired"]["garage_door"] = self.data["garage_door"]
                if system_temp != None:
                    self.shadow["state"]["desired"]["system_temp"] = system_temp
            
                payload = json.dumps(self.shadow)
                self.device_shadow.shadowUpdate(payload, self.custom_callback, 5)
                self.write_db()
                #self.test_db()
            except Exception as ex:
                print("Exception data processor: " + str(ex))
            time.sleep(RECORD_RATE_SEC)

    def read_temp_humid(self):
        # Try to grab a sensor reading.  Use the read_retry method which will retry up
        # to 15 times to get a sensor reading (waiting 2 seconds between each retry).
        humidity, temperature = Adafruit_DHT.read_retry(self.sensor, self.pin)
        
        if humidity != None and temperature != None:
            tempf = temperature * 9.0/5.0 + 32.0

            #ts = time.time()
            self.data["garage_humid"] = humidity
            self.data["garage_temp"] = temperature

    # Reads data from the mpl3115a2
    def read_mpl3115a2(self):
        # Get I2C bus
        bus = smbus.SMBus(1)# MPL3115A2 address, 0x60(96)
        # Select control register, 0x26(38)
        #		0xB9(185)	Active mode, OSR = 128, Altimeter mode
        bus.write_byte_data(0x60, 0x26, 0xB9)
        # MPL3115A2 address, 0x60(96)
        # Select data configuration register, 0x13(19)
        #		0x07(07)	Data ready event enabled for altitude, pressure, temperature
        bus.write_byte_data(0x60, 0x13, 0x07)
        # MPL3115A2 address, 0x60(96)
        # Select control register, 0x26(38)
        #		0xB9(185)	Active mode, OSR = 128, Altimeter mode
        bus.write_byte_data(0x60, 0x26, 0xB9)
        time.sleep(1)# MPL3115A2 address, 0x60(96)
        # Read data back from 0x00(00), 6 bytes
        # status, tHeight MSB1, tHeight MSB, tHeight LSB, temp MSB, temp LSB
        data = bus.read_i2c_block_data(0x60, 0x00, 6)
        # Convert the data to 20-bits
        tHeight = ((data[1] * 65536) + (data[2] * 256) + (data[3] & 0xF0)) / 16
        temp = ((data[4] * 256) + (data[5] & 0xF0)) / 16
        self.data["altitude"] = tHeight / 16.0
        temp2 = temp / 16.0
        temp2f = temp2 * 1.8 + 32
        # MPL3115A2 address, 0x60(96)
        # Select control register, 0x26(38)
        #		0x39(57)	Active mode, OSR = 128, Barometer mode
        bus.write_byte_data(0x60, 0x26, 0x39)
        time.sleep(1)
        # MPL3115A2 address, 0x60(96)
        # Read data back from 0x00(00), 4 bytes
        # status, pres MSB1, pres MSB, pres LSB
        data = bus.read_i2c_block_data(0x60, 0x00, 4)
        # Convert the data to 20-bits
        pres = ((data[1] * 65536) + (data[2] * 256) + (data[3] & 0xF0)) / 16
        pressure = (pres / 4.0) / 1000.0
        self.data["garage_pressure"] = pressure

    # Runs the web server
    def run_server(self):
        app.run(use_reloader=False, debug=True, host="0.0.0.0", port=5000)

if __name__ == '__main__':
    temp_sensor = TemperatureSensor()

    while (True):
        time.sleep(1)
