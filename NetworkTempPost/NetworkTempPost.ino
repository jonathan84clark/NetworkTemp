/*******************************************************************
* NETWORK TEMP
* DESC: Network Temp2 uses an AHT10 and BMP280 to provide temperature
* humidity and air pressure.
* Author: Jonathan L Clark
* Date: 6/17/2023
*******************************************************************/
#include <Adafruit_BMP280.h>
#include <Adafruit_AHT10.h>
#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <ESP8266mDNS.h>
#include <ESP8266HTTPClient.h>

Adafruit_AHT10 aht;
Adafruit_BMP280 bmp; // use I2C interface
Adafruit_Sensor *bmp_temp = bmp.getTemperatureSensor();
Adafruit_Sensor *bmp_pressure = bmp.getPressureSensor();

#ifndef STASSID
#define STASSID "JLC1"
#define STAPSK  "1990clark$fam1984"
#endif

bool offlineMode = false;
bool bmpOnline = false;
float temperature;
float humidity_value;
float temperature2;
float air_pressure;
unsigned int light_value = 0;
unsigned long next_post = 0;
int seconds_count = -1;

const char* ssid     = STASSID;
const char* password = STAPSK;

#define SERVER_IP "192.168.1.25:8005"

// Set your Static IP address
IPAddress local_IP(192, 168, 1, 200);
// Set your Gateway IP address
IPAddress gateway(192, 168, 1, 1);

IPAddress subnet(255, 255, 255, 0);
IPAddress primaryDNS(8, 8, 8, 8);   //optional
IPAddress secondaryDNS(8, 8, 4, 4); //optional

void setup() 
{
   Serial.begin(9600);
   pinMode(A0, INPUT);
   pinMode(BUILTIN_LED, OUTPUT);
   digitalWrite(BUILTIN_LED, HIGH);
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
   }
   else
   {
      bmpOnline = true;
   }

   if (bmpOnline)
   {
       bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,     /* Operating Mode. */
                       Adafruit_BMP280::SAMPLING_X2,     /* Temp. oversampling */
                       Adafruit_BMP280::SAMPLING_X16,    /* Pressure oversampling */
                       Adafruit_BMP280::FILTER_X16,      /* Filtering. */
                       Adafruit_BMP280::STANDBY_MS_500); /* Standby time. */
   }

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
void PostData(float temperature, float temperature2, float humidity, float air_pressure, unsigned int lightLevel)
{
   if ((WiFi.status() == WL_CONNECTED)) 
   {
      WiFiClient client;
      HTTPClient http;

      // configure traged server and url
      http.begin(client, "http://" SERVER_IP "/data.json"); //HTTP
      http.addHeader("Content-Type", "application/json");

      // start connection and send HTTP header and body
      int httpCode = http.POST("{\"source\":\"outdoor_sensor\", \"desc\" : \"outdoor_sensor\", \"temperature\" : " + String(temperature) + ", \"temperature2\" : " + String(temperature2) + ", \"humidity\" : " + String(humidity) + ", \"light_level\" : " + String(lightLevel) + "}");

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
           //Serial.println("Sending...");
           light_value = analogRead(A0);
           sensors_event_t humidity, temp;
           aht.getEvent(&humidity, &temp);
           temperature = temp.temperature;
           humidity_value = humidity.relative_humidity;
           sensors_event_t temp_event, pressure_event;
           if (bmpOnline)
           {
              bmp_temp->getEvent(&temp_event);
              //bmp_pressure->getEvent(&pressure_event);
              //air_pressure = pressure_event.pressure;
              temperature2 = temp_event.temperature;
           }
           PostData(temperature, temperature2, humidity_value, air_pressure, light_value);
           seconds_count = 0;
        }
        seconds_count++;
        next_post = millis() + 1000;
    }
}
