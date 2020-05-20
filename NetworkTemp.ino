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
************************************************************/
#include <SPI.h>
#include <Wire.h>
#include <EthernetV2_0.h>
#include <Adafruit_Sensor.h>
#include "SparkFunMPL3115A2.h"


#include <DHT.h>
#include <DHT_U.h>

#define DHTPIN 2
#define DHTTYPE    DHT11     // DHT 11

// Enter a MAC address and IP address for your controller below.
// The IP address will be dependent on your local network:
byte mac[] = { 
  0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };
IPAddress ip(192,168,1, 177);

// Initialize the Ethernet server library
// with the IP address and port you want to use 
// (port 80 is default for HTTP):
EthernetServer server(80);
#define W5200_CS  10
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
   Serial.begin(9600);
   pinMode(SDCARD_CS, OUTPUT);
   digitalWrite(SDCARD_CS,HIGH);//Deselect the SD card
   // start the Ethernet connection and the server:
   Ethernet.begin(mac, ip);
   server.begin();
   Serial.print("server is at ");
   Serial.println(Ethernet.localIP());
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
   // Delay between measurements. (Modified to be non-blocking)
   if (next_read < ms_ticks)
   {
      ReadSensor();
      next_read = ms_ticks + delayMS;
   }
   // listen for incoming clients
   EthernetClient client = server.available();
   if (client) 
   {
      // an http request ends with a blank line
      boolean currentLineIsBlank = true;
      while (client.connected()) 
      {
         if (client.available()) 
         {
            char c = client.read();
            // if you've gotten to the end of the line (received a newline
            // character) and the line is blank, the http request has ended,
            // so you can send a reply
            if (c == '\n' && currentLineIsBlank) 
            {
               // send a standard http response header
               client.println("HTTP/1.1 200 OK");
               client.println("Content-Type: text/json");
               client.println("Connnection: close");
               client.println();
               client.print("{ \"temperature\" : ");
               client.print(temperature_c);
               client.print(", \"humidity\" : ");
               client.print(humidity);
               client.print(", \"pressure\" : ");
               client.print(pressure);
               client.print("}");
               break;
            }
            if (c == '\n') 
            {
               // you're starting a new line
               currentLineIsBlank = true;
            } 
            else if (c != '\r') 
            {
               // you've gotten a character on the current line
               currentLineIsBlank = false;
            }
         }
      }
      // give the web browser time to receive the data
      delay(1);
      // close the connection:
      client.stop();
   }
}
