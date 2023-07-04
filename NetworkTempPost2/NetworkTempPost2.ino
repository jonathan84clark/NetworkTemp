/*******************************************************************
* NETWORK TEMP
* DESC: Network Temp2 uses an AHT10 and BMP280 to provide temperature
* humidity and air pressure.
* Author: Jonathan L Clark
* Date: 6/17/2023
*******************************************************************/
#include <Adafruit_AHT10.h>
#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <ESP8266mDNS.h>
#include <ESP8266HTTPClient.h>

Adafruit_AHT10 aht;

#ifndef STASSID
#define STASSID "JLC1"
#define STAPSK  "1990clark$fam1984"
#endif

bool offlineMode = false;
float temperature;
float humidity_value;
unsigned long next_post = 0;
int seconds_count = -1;

const char* ssid     = STASSID;
const char* password = STAPSK;

#define SERVER_IP "192.168.1.24"

void setup() 
{
   Serial.begin(9600);
   //pinMode(A0, INPUT);
   pinMode(BUILTIN_LED, OUTPUT);
   digitalWrite(BUILTIN_LED, HIGH);
   int offlineIndex = 0;
   delay(5000);
   WiFi.mode(WIFI_STA);
   WiFi.begin(ssid, password);

   // Wait for connection
   while (WiFi.status() != WL_CONNECTED) 
   {
      delay(500);
      Serial.print(".");
      if (WiFi.status() == WL_NO_SSID_AVAIL)
      {
         Serial.println("Internet not available!");
         offlineMode = true;
         offlineIndex++;
         if (offlineIndex >= 10)
         {
            break;
         }
      }
      else if (WiFi.status() == WL_CONNECT_FAILED)
      {
         Serial.println("Internet connection failed!");
         offlineMode = true;
         offlineIndex++;
         if (offlineIndex >= 10)
         {
            break;
         }
      }
   }
   Serial.println("Adafruit AHT10 demo!");

   if (! aht.begin()) 
   {
      Serial.println("Could not find AHT10? Check wiring");
      while (1) delay(10);
   }
   Serial.println("AHT10 found");

   if (!offlineMode)
   {
      Serial.println("");
      Serial.print("Connected to ");
      Serial.println(ssid);
      Serial.print("IP address: ");
      Serial.println(WiFi.localIP());

      if (MDNS.begin("esp8266")) 
      {
         Serial.println("MDNS responder started");
      }
   }
   else
   {
      Serial.println("System starting in offline mode");
   }
   next_post = millis() + 5000;
}

/***********************************************************
* POST DATA
* DESC: Posts data to the HTTP server
***********************************************************/
void PostData(float temperature, float humidity)
{
   if ((WiFi.status() == WL_CONNECTED)) 
   {
      WiFiClient client;
      HTTPClient http;

      // configure traged server and url
      http.begin(client, "http://" SERVER_IP "/data.json"); //HTTP
      http.addHeader("Content-Type", "application/json");

      // start connection and send HTTP header and body
      int httpCode = http.POST("{\"source\":\"garage_temp_sensor\", \"desc\" : \"garage_temp_sensor\", \"temperature\" : " + String(temperature) + ", \"humidity\" : " + String(humidity) + "}");

      // httpCode will be negative on error
      if (httpCode > 0) 
      {
         // file found at server
         if (httpCode == HTTP_CODE_OK) 
         {
            const String& payload = http.getString();
         }
      } 
      http.end();
   }
}

void loop() 
{
    if (next_post < millis())
    {
        if (seconds_count == 1800 || seconds_count == -1)
        {
           sensors_event_t humidity, temp;
           aht.getEvent(&humidity, &temp);
           temperature = temp.temperature;
           humidity_value = humidity.relative_humidity;
           PostData(temperature, humidity_value);
           seconds_count = 0;
        }
        seconds_count++;
        next_post = millis() + 1000;
    }
}
