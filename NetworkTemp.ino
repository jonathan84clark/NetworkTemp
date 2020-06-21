/***********************************************************
* NETWORK TEMP
* DESC: The network temp system reads temperature data from
* the DHT11 and serve it on a json webpage.
* Based on code created by
* David A. Mellis
* modified 9 Apr 2012
* by Tom Igoe
* Author/Modifier: Jonathan L Clark
* Date: 12/2/2019
* Update: 6/20/2020: Removed the code that uses the wifi shield.
************************************************************/
#include <SPI.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include "SparkFunMPL3115A2.h"


#include <DHT.h>
#include <DHT_U.h>

#define DHTPIN 2
#define DHTTYPE    DHT11     // DHT 11

// Initialize the Ethernet server library
// with the IP address and port you want to use 
// (port 80 is default for HTTP):
//EthernetServer server(80);
#define SDCARD_CS 4
DHT_Unified dht(DHTPIN, DHTTYPE);
MPL3115A2 myPressure;
uint32_t delayMS;
unsigned long ms_ticks = 0;
unsigned long next_read = 0;
float temperature_c = 0.0;
float humidity = 0.0;
float pressure = 0.0;

void setup() 
{
   Wire.begin();        // Join i2c bus
   // Open serial communications and wait for port to open:
   Serial.begin(115200);
   // start the Ethernet connection and the server:
   // Initialize device.
   dht.begin();
   // Print temperature sensor details.
   sensor_t sensor;
   dht.temperature().getSensor(&sensor);
   myPressure.begin(); // Get sensor online
   myPressure.setModeBarometer(); // Measure pressure in Pascals from 20 to 110 kPa
   myPressure.setOversampleRate(7); // Set Oversample to the recommended 128
   myPressure.enableEventFlags(); // Enable all three pressure and temp event flags
   // Set delay between sensor readings based on sensor details.
   delayMS = sensor.min_delay / 1000;
}

/*******************************************************
* READ SENSOR
* DESC: Reads the DHT11 sensor data
*******************************************************/
void ReadSensor()
{
   // Get temperature event and print its value.
   sensors_event_t event;
   dht.temperature().getEvent(&event);
   if (isnan(event.temperature)) 
   {
      Serial.println(F("Error reading temperature!"));
   }
   else 
   {
      temperature_c = event.temperature;
   }
   // Get humidity event and print its value.
   dht.humidity().getEvent(&event);
   if (isnan(event.relative_humidity)) 
   {
      Serial.println(F("Error reading humidity!"));
   }
   else 
   {
      humidity = event.relative_humidity;
   }
   pressure = myPressure.readPressure();
}

void loop() 
{
   ms_ticks = millis();
   ReadSensor();
   Serial.println("Temperature1:" + String(temperature_c) + ":Humidity:" + String(humidity) + ":Pressure:" + String(pressure));
   delay(500);
}
