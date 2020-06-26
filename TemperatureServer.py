#!/usr/bin/python
# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# git clone https://github.com/adafruit/Adafruit_Python_DHT.git
from threading import Thread
import sys
import smbus
import time
import Adafruit_DHT
from flask import Flask, request, redirect
from flask import Response
import flask.json
import flask.json
import os
from flask import jsonify
from datetime import datetime
from scipy import stats

app = Flask(__name__)

@app.route('/local_environment', methods=['GET', 'POST'])
def control_post():
    global temp_sensor
    output = jsonify(temp_sensor.data)
    return output

class TemperatureSensor:
    def __init__(self):
        # Parse command line parameters.
        sensor_args = { '11': Adafruit_DHT.DHT11,
                        '22': Adafruit_DHT.DHT22,
                        '2302': Adafruit_DHT.AM2302 }
        self.sensor = sensor_args['11']
        self.pin = '4'
        self.data = {"temp1" : 0.0, "temp1f" : 0.0, "temp2" : 0.0, "temp2f" : 0.0, "humidity" : 0.0, "altitude" : 0.0, "pressure" : 0.0}
        #self.temperature1 = 0.0
        #self.temperature1f = 0.0
        #self.humidity = 0.0
        #self.altitude = 0.0
        #self.cTemp = 0.0
        #self.fTemp = 0.0
        #self.pressure = 0.0

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

 
    # Process the temperature, humidity and other data
    def data_processor(self):
        temperatures = []
        humidities = []
        pressures = []
        x_values1 = []
        x_values2 = []
        x_values3 = []
        index = 0
        file_name = '/home/pi/temperature_data.csv'
        if not os.path.exists(file_name):
            f = open(file_name, 'w')
            f.write('Date,Time,Temp1,TempSlope,Humidity,HumiditySlope,Pressure,PressureSlope\n')
            f.close()
        while (True):
            now = datetime.now()
            temp1 = self.data["temp1f"]
            humidity = self.data["humidity"]
            pressure = self.data["pressure"]
            temperatures.append(temp1)
            humidities.append(humidity)
            pressures.append(pressure)
            x_values1.append(index)
            x_values2.append(index)
            x_values3.append(index)
            index += 1
            f = open(file_name, 'a')
            tempSlope = 0.0
            humiditySlope = 0.0
            pressureSlope = 0.0
            if len(temperatures) > 15:
                tempSlope, intercept, r_value, p_value, std_err = stats.linregress(x_values1, temperatures)
                temperatures.pop(len(temperatures) - 1)
                x_values1.pop(len(x_values1) - 1)

            if len(humidities) > 15:
                tempSlope, intercept, r_value, p_value, std_err = stats.linregress(x_values2, humidities)
                humidities.pop(len(humidities) - 1)
                x_values2.pop(len(x_values2) - 1)


            if len(pressures) > 15:
                tempSlope, intercept, r_value, p_value, std_err = stats.linregress(x_values3, pressures)
                pressures.pop(len(pressures) - 1)
                x_values3.pop(len(x_values3) - 1)

            date_str = now.strftime("%m/%d/%Y,%H:%M:%S")
            data_string = date_str + "," + str(temp1) + "," + str(tempSlope)
            data_string += "," + str(humidity) + "," + str(humiditySlope)
            data_string += "," + str(pressure) + "," + str(pressureSlope) + "\n"
            f.write(data_string)
            f.close()
            time.sleep(30)
        
    # Regularly read the dht11
    def regular_read_dht11(self):
        while (True):
            self.read_temp_humid()
            time.sleep(1)

    # Regularly read data from the mpl3115a2
    def regular_read_mpl3115a2(self):
        while (True):
            self.read_mpl3115a2()
            time.sleep(1)

    def read_temp_humid(self):
        # Try to grab a sensor reading.  Use the read_retry method which will retry up
        # to 15 times to get a sensor reading (waiting 2 seconds between each retry).
        humidity, temperature = Adafruit_DHT.read_retry(self.sensor, self.pin)
        self.data["humidity"] = humidity
        self.data["temp1"] = temperature
        self.data["temp1f"] = temperature * 9.0/5.0 + 32.0
        # Un-comment the line below to convert the temperature to Fahrenheit.
        # temperature = temperature * 9/5.0 + 32

        # Note that sometimes you won't get a reading and
        # the results will be null (because Linux can't
        # guarantee the timing of calls to read the sensor).
        # If this happens try again!
        #if humidity is not None and temperature is not None:
        #    print('Temp={0:0.1f}*  Humidity={1:0.1f}%'.format(temperature, humidity))
        #else:
        #    print('Failed to get reading. Try again!')
    
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
        self.data["temp2"] = temp / 16.0
        self.data["temp2f"] = self.data["temp2"] * 1.8 + 32
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
        self.data["pressure"] = (pres / 4.0) / 1000.0
        # Output data to screen
        #print "Pressure : %.2f kPa" %pressure
        #print "Altitude : %.2f m" %altitude
        #print "Temperature in Celsius  : %.2f C" %cTemp
        #print "Temperature in Fahrenheit  : %.2f F" %fTemp

    # Runs the web server
    def run_server(self):
        app.run(use_reloader=False, debug=True, host="0.0.0.0", port=5000)

temp_sensor = TemperatureSensor()
#temp_sensor.read_mpl3115a2()
#temp_sensor.read_temp_humid()

while (True):
    time.sleep(1)
