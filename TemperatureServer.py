#!/usr/bin/python
##################################################################
# TEMPERATURE SERVER
# DESC: The temperature server is designed to store and provide stable
# temperature pressure and humidity information
# Author: Jonathan L Clark
# Date: 7/4/2020
##################################################################
# git clone https://github.com/adafruit/Adafruit_Python_DHT.git
from threading import Thread
import smbus
import time
import Adafruit_DHT
import flask.json
import os
import numpy as np
import time;
from flask import Flask, request, redirect
from flask import Response
from flask import jsonify
from datetime import datetime
from scipy import stats

DHT_11_SAMPLE_SIZE = 30
RECORD_RATE_SEC = 900

app = Flask(__name__)

@app.route('/local_environment', methods=['GET', 'POST'])
def control_post():
    global temp_sensor
    output = jsonify(temp_sensor.data)
    return output

class TemperatureSensor:
    def __init__(self):

        # DHT 11 Data points
        self.stored_temps = [] 
        self.temperature_times = []
        self.stored_humids = []
        self.humid_times = []

        # MPL3115A2 Data points
        self.stored_pressures = []
        self.pressure_times = []
        self.stored_temp2s = []
        self.temp2s_times = []

        # Parse command line parameters.
        sensor_args = { '11': Adafruit_DHT.DHT11,
                        '22': Adafruit_DHT.DHT22,
                        '2302': Adafruit_DHT.AM2302 }
        self.sensor = sensor_args['11']
        self.pin = '4'
        self.data = {"temp1" : 0.0, "temp1f" : 0.0, "temp2" : 0.0, "temp2f" : 0.0, "humidity" : 0.0, "altitude" : 0.0, "pressure" : 0.0,
                     "temp1_time" : 0.0, "temp2_time" : 0.0, "humidity_time" : 0.0, "pressure_time" : 0.0}

        dht11Thread = Thread(target = self.regular_read_dht11)
        dht11Thread.daemon = True
        dht11Thread.start()

        mpl3115a2Thread = Thread(target = self.regular_read_mpl3115a2)
        mpl3115a2Thread.daemon = True
        mpl3115a2Thread.start()

        server_thread = Thread(target = self.run_server)
        server_thread.daemon = True
        server_thread.start()

        data_thread = Thread(target = self.data_processor)
        data_thread.daemon = True
        data_thread.start()

        
    # Regularly read the dht11
    def regular_read_dht11(self):
        while (True):
            self.read_temp_humid()
            time.sleep(10)

    # Regularly read data from the mpl3115a2
    def regular_read_mpl3115a2(self):
        while (True):
            self.read_mpl3115a2()
            time.sleep(10)

    def ComputeAverage(self, list):
        a = np.array(list)
        standard_deviation = np.std(a)
        average = np.average(a)
        new_average_items = []
        items_to_remove = []
        if standard_deviation == 0.0:
            return average

        for x in range(0, len(list)):
            if abs((list[x] - average) / standard_deviation) < 3.0:
                new_average_items.append(list[x])

        if len(new_average_items) != len(list):
            a = np.array(new_average_items)
            average = np.average(a)

        return average

    # Process the temperature, humidity and other data
    def data_processor(self):
        index = 0.0
        recorded_temps = []
        recorded_temp_times = []
        recorded_humids = []
        recorded_humid_times = []
        recorded_pressures = []
        recorded_pressure_times = []

        file_name = '/home/pi/temperature_data.csv'
        if not os.path.exists(file_name):
            f = open(file_name, 'w')
            f.write('Date,Time,UTC,Temp1,TempSlope,Humidity,HumiditySlope,Pressure,PressureSlope\n')
            f.close()
        while (True):
            ts = time.time()
            time.sleep(RECORD_RATE_SEC)
            now = datetime.now()

            tempSlope = 0.0
            humiditySlope = 0.0
            pressureSlope = 0.0

            recorded_temp = self.data["temp1"]
            recorded_humidity = self.data["humidity"]
            recorded_pressure = self.data["pressure"]
           
            recorded_temps.append(recorded_temp)
            recorded_temp_times.append(ts)

            recorded_humids.append(recorded_humidity)
            recorded_humid_times.append(ts)

            recorded_pressures.append(recorded_pressure)
            recorded_pressure_times.append(ts)

            if len(recorded_temps) > DHT_11_SAMPLE_SIZE:
                tempSlope, intercept, r_value, p_value, std_err = stats.linregress(recorded_temp_times, recorded_temps)
                recorded_temps.pop(0)
                recorded_temp_times.pop(0)

            if len(recorded_humids) > DHT_11_SAMPLE_SIZE:
                humiditySlope, intercept, r_value, p_value, std_err = stats.linregress(recorded_humid_times, recorded_humids)
                recorded_humids.pop(0)
                recorded_humid_times.pop(0)

            if len(recorded_pressures) > DHT_11_SAMPLE_SIZE:
                pressureSlope, intercept, r_value, p_value, std_err = stats.linregress(recorded_pressure_times, recorded_pressures)
                recorded_pressures.pop(0)
                recorded_pressure_times.pop(0)
                
            f = open(file_name, 'a')
            date_str = now.strftime("%m/%d/%Y,%H:%M:%S")
            data_string = date_str + "," + str(ts) + "," + str(recorded_temp) + "," + str(tempSlope)
            data_string += "," + str(recorded_humidity) + "," + str(humiditySlope)
            data_string += "," + str(recorded_pressure) + "," + str(pressureSlope) + "\n"
            f.write(data_string)
            f.close()
            time.sleep(RECORD_RATE_SEC)

    def read_temp_humid(self):
        # Try to grab a sensor reading.  Use the read_retry method which will retry up
        # to 15 times to get a sensor reading (waiting 2 seconds between each retry).
        humidity, temperature = Adafruit_DHT.read_retry(self.sensor, self.pin)

        ts = time.time()
        self.data["humidity"] = humidity
        self.data["temp1"] = temperature
        self.data["temp1f"] = temperature * 9.0/5.0 + 32.0
        self.stored_temps.append(temperature)
        self.stored_humids.append(humidity)
        self.temperature_times.append(ts)
        self.humid_times.append(ts)

        if len(self.stored_temps) > DHT_11_SAMPLE_SIZE:
            #tempSlope, intercept, r_value, p_value, std_err = stats.linregress(self.temperature_times, self.stored_temps)
            average_temp = self.ComputeAverage(self.stored_temps)
            self.data["temp1"] = average_temp
            self.data["temp1_time"] = ts
            self.data["temp1f"] = average_temp * 9.0/5.0 + 32.0
            self.stored_temps.pop(0)
            self.temperature_times.pop(0)

        if len(self.stored_humids) > DHT_11_SAMPLE_SIZE:
            #humidSlope, intercept, r_value, p_value, std_err = stats.linregress(self.humid_times, self.stored_humids)
            average_humid = self.ComputeAverage(self.stored_humids)
            self.data["humidity"] = average_humid
            self.data["humidity_time"] = ts
            self.stored_humids.pop(0)
            self.humid_times.pop(0)

        #print("Temp: " + str(self.data["temp1"]) + " Humidity: " + str(self.data["humidity"]))
    
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

        ts = time.time()
        self.data["pressure"] = pressure
        self.data["temp2"] = temp2
        self.data["temp2f"] = temp2f

        self.stored_pressures.append(pressure)
        self.pressure_times.append(ts)
        self.stored_temp2s.append(temp2)
        self.temp2s_times.append(ts)

        if len(self.stored_pressures) > DHT_11_SAMPLE_SIZE:
            #tempSlope, intercept, r_value, p_value, std_err = stats.linregress(self.pressure_times, self.stored_pressures)
            average_pressure = self.ComputeAverage(self.stored_pressures)
            self.data["pressure"] = average_pressure
            self.data["pressure_time"] = ts
            self.stored_pressures.pop(0)
            self.pressure_times.pop(0)

        if len(self.stored_temp2s) > DHT_11_SAMPLE_SIZE:
            #tempSlope, intercept, r_value, p_value, std_err = stats.linregress(self.temp2s_times, self.stored_temp2s)
            average_temp2 = self.ComputeAverage(self.stored_temp2s)
            self.data["temp2"] = average_temp2
            self.data["temp2f"] = average_temp2 * 1.8 + 32
            self.data["temp2_time"] = ts
            self.stored_temp2s.pop(0)
            self.temp2s_times.pop(0)

        # Output data to screen
        #print "Pressure : %.2f kPa" %self.data["pressure"]
        #print "Altitude : %.2f m" %altitude
        #print "Temperature in Celsius  : %.2f C" %self.data["temp2"]
        #print "Temperature in Fahrenheit  : %.2f F" %fTemp

    # Runs the web server
    def run_server(self):
        app.run(use_reloader=False, debug=True, host="0.0.0.0", port=5000)

if __name__ == '__main__':
    temp_sensor = TemperatureSensor()

    while (True):
        time.sleep(1)
