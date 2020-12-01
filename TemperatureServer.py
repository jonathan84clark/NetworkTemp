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
            "state": { "desired": { "local_temp" : -1.0, "local_humid": -1.0, "local_pressure" : -1.0, "outdoor_temp" : -1.0, "outdoor_humid" : -1.0, "system_temp" : -1.0 } }
        }
        self.setup_aws()
      
        try:
            # Parse command line parameters.
            sensor_args = { '11': Adafruit_DHT.DHT11,
                            '22': Adafruit_DHT.DHT22,
                            '2302': Adafruit_DHT.AM2302 }
            self.sensor = sensor_args['11']
            self.pin = '4'
            self.data = {"temperature" : 0.0, "humidity" : 0.0, "pressure" : 0.0, "outdoor_tempf" : 0.0, "outdoor_humid" : 0.0, "system_temp" : 0.0}
            
            thread_functions = [self.regular_read_dht11, self.regular_read_mpl3115a2, self.GetOutdoorTemps, self.run_server, self.data_processor]
            
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
            
            sql_create_table = """ CREATE TABLE IF NOT EXISTS environment (
                                        time_stamp text,
                                        system_temp float,
                                        temperature float,
                                        humidity float,
                                        pressure float,
                                        outdoor_tempf float,
                                        outdoor_humid float
                                    ); """
                                    
            insert = ''' INSERT INTO environment(time_stamp,system_temp,temperature,humidity,pressure,outdoor_tempf,outdoor_humid)
                         VALUES(?,?,?,?,?,?,?) '''
            c = conn.cursor()
            c.execute(sql_create_table)
            conn.commit()
            data = (timestamp, self.data["system_temp"], self.data["temperature"], self.data["humidity"], self.data["pressure"], self.data["outdoor_tempf"], self.data["outdoor_humid"])
            c.execute(insert, data)
            conn.commit()
            c.close()
            print("Saved temperature to database...")
        except Error as ex:
            print("Unable to write to database: " + str(ex))
            
        
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
                response = requests.get('http://192.168.1.191')
                data = json.loads(response.text)
                self.data["outdoor_tempf"] = data["temperature"]
                self.data["outdoor_humid"] = data["humidity"]
            except Exception as e:
                print("Except: " + str(e))
            time.sleep(RECORD_RATE_SEC)

    # Custom callback
    def custom_callback(self, data, parm1, parm2):
        pass # Do nothing
   
    # Process the temperature, humidity and other data
    def data_processor(self):

        while (True):
            now = datetime.now()
            time.sleep(STARTUP_TIME)
            out = subprocess.Popen(['vcgencmd', 'measure_temp'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            stdout,stderr = out.communicate()
            system_temp = None
            system_temp_str = stdout.decode('utf-8').replace("'C\n", "").split('=')
            if len(system_temp_str) == 2:
                system_temp = float(system_temp_str[1])
                self.data["system_temp"] = system_temp
            self.shadow["state"]["desired"]["local_temp"] = self.data["temperature"]
            self.shadow["state"]["desired"]["local_humid"] = self.data["humidity"]
            self.shadow["state"]["desired"]["local_pressure"] = self.data["pressure"]
            self.shadow["state"]["desired"]["outdoor_temp"] = self.data["outdoor_tempf"]
            self.shadow["state"]["desired"]["outdoor_humid"] = self.data["outdoor_humid"]
            if system_temp != None:
                self.shadow["state"]["desired"]["system_temp"] = system_temp
            
            payload = json.dumps(self.shadow)
            self.device_shadow.shadowUpdate(payload, self.custom_callback, 5)
            self.write_db()
            #self.test_db()
            time.sleep(RECORD_RATE_SEC)

    def read_temp_humid(self):
        # Try to grab a sensor reading.  Use the read_retry method which will retry up
        # to 15 times to get a sensor reading (waiting 2 seconds between each retry).
        humidity, temperature = Adafruit_DHT.read_retry(self.sensor, self.pin)
        
        if humidity != None and temperature != None:
            tempf = temperature * 9.0/5.0 + 32.0

            #ts = time.time()
            self.data["humidity"] = humidity
            self.data["temperature"] = temperature

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
        self.data["pressure"] = pressure

    # Runs the web server
    def run_server(self):
        app.run(use_reloader=False, debug=True, host="0.0.0.0", port=5000)

if __name__ == '__main__':
    temp_sensor = TemperatureSensor()

    while (True):
        time.sleep(1)
