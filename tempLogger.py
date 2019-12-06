####################################################################
# TEMP LOGGER
# DESC: The temperature logger is a python script that logs temperature
# data both from a remote and local source.
# Author: Jonathan L Clark
# Date: 12/5/2019
#####################################################################
# importing the requests library 
import requests 

def GetLocalTemp():
    # api-endpoint 
    URL = "http://192.168.1.177"
  
    # sending get request and saving the response as response object 
    r = requests.get(url = URL) 
  
    # extracting data in json format 
    data = r.json() 
  

    print(data)

def GetNoaaWeatherData():
    URL1 = "https://api.weather.gov/points/47.688970,-117.283940"

    # sending get request and saving the response as response object 
    r = requests.get(url = URL1)

    # extracting data in json format 
    data = r.json() 

    forecast_url = data['properties']['forecastHourly']

    # sending get request and saving the response as response object 
    r = requests.get(url = forecast_url)
  
    data = r.json()

    weather = data['properties']['periods'][0]

    print(weather['temperature'])

GetNoaaWeatherData()