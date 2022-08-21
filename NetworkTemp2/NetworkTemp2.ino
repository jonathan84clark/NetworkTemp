/*******************************************************************
* NETWORK TEMP
* DESC: Network Temp2 uses an AHT10 and BMP280 to provide temperature
* humidity and air pressure.
* Author: Jonathan L Clark
* Date: 8/20/2022
*******************************************************************/
#include <Adafruit_BMP280.h>
#include <Adafruit_AHT10.h>
#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <ESP8266WebServer.h>
#include <ESP8266mDNS.h>

Adafruit_AHT10 aht;
Adafruit_BMP280 bmp; // use I2C interface
Adafruit_Sensor *bmp_temp = bmp.getTemperatureSensor();
Adafruit_Sensor *bmp_pressure = bmp.getPressureSensor();

#ifndef STASSID
#define STASSID "JLC1"
#define STAPSK  "1990clark$fam1984"
#endif

bool offlineMode = false;
float temperature;
float humidity_value;
float temperature2;
float air_pressure;
unsigned int light_value = 0;

const char* ssid     = STASSID;
const char* password = STAPSK;

ESP8266WebServer server(80);

// Set your Static IP address
IPAddress local_IP(192, 168, 1, 200);
// Set your Gateway IP address
IPAddress gateway(192, 168, 1, 1);

IPAddress subnet(255, 255, 255, 0);
IPAddress primaryDNS(8, 8, 8, 8);   //optional
IPAddress secondaryDNS(8, 8, 4, 4); //optional

void handleRoot() 
{
   String dataString = "{\"temperature\" : " + String(temperature) + ",";
   dataString += " \"temperature2\" : " + String(temperature2) + ",";
   dataString += " \"air_pressure\" : " + String(air_pressure) + ",";
   dataString += " \"light_value\" : " + String(light_value) + ",";
   dataString += " \"humidity\" : " + String(humidity_value) + "}";
   server.send(200, "application/json", dataString);
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

void setup() 
{
   Serial.begin(9600);
   pinMode(A0, INPUT);
   int offlineIndex = 0;
   delay(5000);
   WiFi.begin(ssid, password);
   if (!WiFi.config(local_IP, gateway, subnet, primaryDNS, secondaryDNS))
   {
      Serial.println("STA Failed to configure");
   }
   Serial.println("");

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
   if (!bmp.begin()) 
   {
      Serial.println(F("Could not find a valid BMP280 sensor, check wiring or "
                      "try a different address!"));
      while (1) delay(10);
   }

   
   bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,     /* Operating Mode. */
                   Adafruit_BMP280::SAMPLING_X2,     /* Temp. oversampling */
                   Adafruit_BMP280::SAMPLING_X16,    /* Pressure oversampling */
                   Adafruit_BMP280::FILTER_X16,      /* Filtering. */
                   Adafruit_BMP280::STANDBY_MS_500); /* Standby time. */

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

      server.on("/", handleRoot);
      server.onNotFound(handleNotFound);
      server.begin();
      Serial.println("HTTP server started");
   }
   else
   {
      Serial.println("System starting in offline mode");
   }
}

void loop() {

   if (!offlineMode)
   {
      light_value = analogRead(A0);
      sensors_event_t humidity, temp;
      aht.getEvent(&humidity, &temp);
      temperature = temp.temperature;
      humidity_value = humidity.relative_humidity;
      sensors_event_t temp_event, pressure_event;
      bmp_temp->getEvent(&temp_event);
      bmp_pressure->getEvent(&pressure_event);
      air_pressure = pressure_event.pressure;
      temperature2 = temp_event.temperature;
      server.handleClient();
   }
}
