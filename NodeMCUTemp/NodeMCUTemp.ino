/********************************************************************
* RTC V2
* DESC: This is the second iteration of Anthony's RTC. This one being more advanced,
* with a WiFi interface. This device is able to automatically update for daylight savings
* time. It is also capable of providing a web interface for setting wakeup times. 
* Author: Jonathan L Clark
* Date: 10/22/2020
********************************************************************/
#include <DHT.h>
#include <DHT_U.h>
#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <ESP8266WebServer.h>
#include <ESP8266mDNS.h>
#include <Wire.h>

#define DHTTYPE DHT11   // DHT 11
#define DHTPIN 13     // Digital pin connected to the DHT sensor

float temperature;
float humidity;

#ifndef STASSID
#define STASSID "JLC1"
#define STAPSK  "1990clark$fam1984"
#endif

const char* ssid     = STASSID;
const char* password = STAPSK;
bool offlineMode = false;
unsigned long msTicks = 0;
unsigned long nextTick = 0;

DHT dht(DHTPIN, DHTTYPE);
ESP8266WebServer server(80);

// Set your Static IP address
IPAddress local_IP(192, 168, 1, 191);
// Set your Gateway IP address
IPAddress gateway(192, 168, 1, 1);

IPAddress subnet(255, 255, 0, 0);
IPAddress primaryDNS(8, 8, 8, 8);   //optional
IPAddress secondaryDNS(8, 8, 4, 4); //optional

const int led = LED_BUILTIN;


void handleRoot() 
{
   String dataString = "{\"temperature\" : " + String(temperature) + "}";
   dataString += ",{\"humidity\" : " + String(humidity) + "}";
   server.send(200, "text/plain", dataString);
  //digitalWrite(led, 0);
}

/******************************************************
* HANDLES THE PAGE NOT BEING FOUND
******************************************************/
void handleNotFound() 
{
   String message = "File Not Found\n\n";
   message += "URI: ";
   message += server.uri();
   message += "\nMethod: ";
   message += (server.method() == HTTP_GET) ? "GET" : "POST";
   message += "\nArguments: ";
   message += server.args();
   message += "\n";
   for (uint8_t i = 0; i < server.args(); i++) 
   {
      message += " " + server.argName(i) + ": " + server.arg(i) + "\n";
   }
   server.send(404, "text/plain", message);
}

void setup(void) {
  pinMode(led, OUTPUT);
  digitalWrite(led, 0);
  Serial.begin(115200);
  // Start the I2C interface
  Wire.begin();
  dht.begin();
  WiFi.begin(ssid, password);
  if (!WiFi.config(local_IP, gateway, subnet, primaryDNS, secondaryDNS))
  {
     Serial.println("STA Failed to configure");
  }
  Serial.println("");
  int offlineIndex = 0;

  // Wait for connection
  while (WiFi.status() != WL_CONNECTED) {
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
  if (!offlineMode)
  {
      Serial.println("");
      Serial.print("Connected to ");
      Serial.println(ssid);
      Serial.print("IP address: ");
      Serial.println(WiFi.localIP());

      if (MDNS.begin("esp8266")) {
          Serial.println("MDNS responder started");
      }

      server.on("/", handleRoot);

      server.onNotFound(handleNotFound);

      server.begin();
      Serial.println("HTTP server started");
   }
   else
   {
     Serial.println("System starting in offline mode");
   }
   //SetupLEDStates();
}

void loop(void) 
{
   msTicks = millis();
   if (!offlineMode)
   {
      server.handleClient();
   }
   if (nextTick < msTicks)
   {
      temperature = dht.readTemperature(true);
      humidity = dht.readHumidity();
      nextTick = msTicks + 1000;
   }
   
}
