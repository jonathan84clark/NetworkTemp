####################################################################
# TEMP LOGGER
# DESC: The temperature logger is a python script that logs temperature
# data both from a remote and local source.
# Author: Jonathan L Clark
# Date: 12/5/2019
#####################################################################
# importing the requests library 
import requests 
import os.path
from datetime import date
from datetime import datetime
from threading import Thread
import time

csv_file = "C:\\Users\\jonat\\Desktop\\TempData.txt"

def GetLocalTemp():
    # api-endpoint 
    try:
        URL = "http://192.168.1.177"
  
        # sending get request and saving the response as response object 
        r = requests.get(url = URL) 
  
        # extracting data in json format 
        data = r.json() 
        return ((data["temperature"] * 9.0/5.0) + 32.0)

    except Exception as e:
        print("Exception Get Local Temp: " + str(e))
        return None

def GetNoaaWeatherData():
    URL1 = "https://api.weather.gov/points/47.688970,-117.283940"

    try:

        # sending get request and saving the response as response object 
        r = requests.get(url = URL1)

        # extracting data in json format 
        data = r.json() 
    
        forecast_url = data['properties']['forecastHourly']

        # sending get request and saving the response as response object 
        r = requests.get(url = forecast_url)
  
        data = r.json()

        weather = data['properties']['periods'][0]

        return weather['temperature']

    except Exception as e:
        print("Exception Get Noaa: " + str(e))
        return None

def WriteToCSV(local_temp, noaa_temp):
    if not os.path.isfile(csv_file):
        f = open(csv_file, "a+")
        f.write("Date,Time,GarageTemp,NoaaTemp\n")
        f.close()
    now = datetime.now()
    dt_string = now.strftime("%m/%d/%Y,%H:%M:%S")

    if local_temp == None:
        local_tmp_str = "Err"
    else:
        local_tmp_str = str(local_temp)
 
    noaa_tmp_str = ""
    if noaa_temp == None:
        noaa_tmp_str = "Err"
    else: 
        noaa_tmp_str = str(noaa_temp)

    dt_string += "," + local_tmp_str + "," + noaa_tmp_str + "\n"
    f = open(csv_file, "a+")
    f.write(dt_string)
    f.close()

def MainLoop():
    while (True):
        noaaTemp = GetNoaaWeatherData()
        localTemp = GetLocalTemp()
        print("Wrote temperature data...")
        WriteToCSV(localTemp, noaaTemp)
        time.sleep(3600)

if __name__ == "__main__":
	# Start up the server thread
    thread = Thread(target = MainLoop)
    thread.daemon = True
    thread.start()

    while (True):
        time.sleep(1)