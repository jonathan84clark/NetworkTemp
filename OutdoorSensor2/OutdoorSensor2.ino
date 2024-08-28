/********************************************************************************
* OUTDOOR SENSOR 2
* DESC: Monitors the outdoor temperature and reports the data to a webpage
* 
* Author: Jonathan L Clark
* Date: 8/15/2024
********************************************************************************/
#include <DHT.h>
#include <DHT_U.h>
#include <BME280I2C.h>
#include <Wire.h>
#include <Adafruit_AHT10.h>
#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <ESP8266mDNS.h>
#include <ESP8266WebServer.h>
#include <ESP8266HTTPClient.h>

#define DHTTYPE DHT11   // DHT 11
#define DHTPIN 12     // Digital pin connected to the DHT sensor

#define SERIAL_BAUD 9600

#ifndef STASSID
#define STASSID "JLC1"
#define STAPSK  "1990clark$fam1984"
#endif

#define SAMPLE_SIZE 10
#define SAMPLE_RATE_MS 5000

#define SERVER_IP "192.168.1.24"

bool offlineMode = false;

BME280I2C bme;    // Default : forced mode, standby time = 1000 ms
                  // Oversampling = pressure ×1, temperature ×1, humidity ×1, filter off,

DHT dht(DHTPIN, DHTTYPE);
const char* ssid     = STASSID;
const char* password = STAPSK;

String newHostname = "EnviroSensor2";

float temperature;
float dht_temperature;
float humidity_value;
float air_pressure;
unsigned long next_post = 0;
unsigned long ms_ticks = 0;
unsigned long next_sample = 0;

int seconds_count = -1;

float temperature_samples[SAMPLE_SIZE];
float air_pressure_samples[SAMPLE_SIZE];
float humidity_samples[SAMPLE_SIZE];
bool queue_full = false;
bool first_send = false;

int sample_index = 0;
ESP8266WebServer server(80);

/***********************************************************
* HANDLE ROOT
* DESC: Handles the root of the webpage which displays information
***********************************************************/
void handleRoot() 
{
   server.send(200, "text/json", "{\"source\":\"solar_temp_sensor\", \"desc\" : \"solar_temp_sensor\", \"temperature\" : " + String(temperature) + ", \"humidity\" : " + String(humidity_value) + ", \"air_pressure\" : " + String(air_pressure) + "}");
}

void setup()
{
   Serial.begin(SERIAL_BAUD);

   while(!Serial) {} // Wait
   Serial.begin(9600);
   pinMode(BUILTIN_LED, OUTPUT);
   digitalWrite(BUILTIN_LED, HIGH);
   dht.begin();
   int offlineIndex = 0;
   delay(5000);
   WiFi.mode(WIFI_STA);
   WiFi.hostname(newHostname.c_str());
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
   Serial.print("IP address: ");
   Serial.println(WiFi.localIP());
   server.on("/", handleRoot);
   server.begin();

   Wire.begin();

   while(!bme.begin())
   {
      Serial.println("Could not find BME280 sensor!");
      delay(1000);
   }
}

void loop()
{
    ms_ticks = millis();
    if (next_sample < ms_ticks)
    {
       float hum(NAN);
       BME280::TempUnit tempUnit(BME280::TempUnit_Celsius);
       BME280::PresUnit presUnit(BME280::PresUnit_Pa);
       dht_temperature = dht.readTemperature(true);
       humidity_value = dht.readHumidity();
       bme.read(air_pressure, temperature, hum, tempUnit, presUnit);
       temperature_samples[sample_index] = temperature;
       air_pressure_samples[sample_index] = air_pressure;
       humidity_samples[sample_index] = humidity_value;
       
       sample_index++;
       if (sample_index == SAMPLE_SIZE)
       {
          sample_index = 0;
          queue_full = true;
       }
       
       next_sample = ms_ticks + SAMPLE_RATE_MS;
    }
    if (next_post < millis())
    {
        if ((seconds_count >= 1800 || seconds_count == -1 || !first_send) && queue_full)
        {
           float average_temp = 0;
           float average_humid = 0;
           float average_pressure = 0;
           for (int i = 0; i < SAMPLE_SIZE; i++)
           {
               average_temp += temperature_samples[i];
               average_humid += humidity_samples[i];
               average_pressure += air_pressure_samples[i];
           }
           average_temp = average_temp / (float)SAMPLE_SIZE;
           average_humid = average_humid / (float)SAMPLE_SIZE;
           average_pressure = average_pressure / (float)SAMPLE_SIZE;
           Serial.printf("Sending -- Temperature: %d Humidity: %d Air Pressure: %d", (int)average_temp, (int)average_humid, (int)average_pressure);
           
           PostData(average_temp, average_humid, average_pressure);
           seconds_count = 0;
           first_send = true;
        }
        seconds_count++;
        next_post = millis() + 1000;
    }
    server.handleClient();
}

/***********************************************************
* POST DATA
* DESC: Posts data to the HTTP server
***********************************************************/
void PostData(float temperature, float humidity, float air_pressure)
{
   if ((WiFi.status() == WL_CONNECTED)) 
   {
      WiFiClient client;
      HTTPClient http;

      // configure traged server and url
      http.begin(client, "http://" SERVER_IP "/data.json"); //HTTP
      http.addHeader("Content-Type", "application/json");

      // start connection and send HTTP header and body
      int httpCode = http.POST("{\"source\":\"solar_temp_sensor\", \"desc\" : \"solar_temp_sensor\", \"temperature\" : " + String(temperature) + ", \"humidity\" : " + String(humidity) + ", \"air_pressure\" : " + String(air_pressure) + "}");

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
