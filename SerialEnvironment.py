#!/usr/bin/env python
#################################################################
# SERIAL ENVIRONMENT
# DESC: The serial environment node reads serial data from an environmental
# sensor.
# Author: Jonathan L Clark
# Date: 6/20/2020
##################################################################
from threading import Thread
import json
import serial
import re

# Interacts with the Arduino serial sensor
class EnvironmentalSensor():
    def __init__(self):
        self.ser = serial.Serial('/dev/ttyACM0')
        self.ser.baudrate = 115200
        self.ser.close()
        self.ser.open()

    # Reads a single data string from the serial port
    def read(self):
        line = self.ser.readline()
        m = re.match(r"\Temperature1:(\d[0-9]+.[0-9]+):Humidity:(\d[0-9]+.[0-9]+):Pressure:(\d[0-9]+.[0-9]+)", line)
        self.temperature = float(m.group(1))
        self.humidity = float(m.group(2))
        self.pressure = float(m.group(3))
        print(self.temperature)

environ = EnvironmentalSensor()
environ.read()
