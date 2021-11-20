/***********************************************************************
* SEISMOMETER
* DESC: Simple device designed to detect and transmit any accelerations it
* detects. This device is designed to detect vibrations on the earth as
* well as earthquakes.
* Requires the BME280 library by Tyler Glenn
* Author: Jonathan L Clark
* Date: 11/13/2021
***********************************************************************/

#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>

#include <BME280I2C.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

#ifndef STASSID
#define STASSID "JLC1"
#define STAPSK  "1990clark$fam1984"
#endif

#define BUFFER_SIZE 512
#define MAX_SAMPLES 5
unsigned int localPort = 8888;      // local port to listen on
float accXSamples[MAX_SAMPLES];
float accYSamples[MAX_SAMPLES];
float accZSamples[MAX_SAMPLES];
float temperature = 0.0;

// buffers for receiving and sending data
char  sendBuffer[BUFFER_SIZE];       // a string to send back
unsigned long msTicks = 0;
unsigned long udpTime = 0;
int sampleIndex = 0;
int sampleCount = 0;
uint16_t lastAnalogRead = 0;

Adafruit_MPU6050 mpu;
BME280I2C bme;    // Default : forced mode, standby time = 1000 ms

WiFiUDP Udp;

void setup() {
  Serial.begin(115200);
  
  delay(5000);
  memset(sendBuffer, 0, 8);

  WiFi.mode(WIFI_STA);
  WiFi.begin(STASSID, STAPSK);
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print('.');
    delay(500);
  }
  Serial.print("Connected! IP address: ");
  Serial.println(WiFi.localIP());

  Wire.begin();

  while(!bme.begin())
  {
    Serial.println("Could not find BME280 sensor!");
    delay(1000);
  }
  
  if (!mpu.begin()) 
  {
     Serial.println("Failed to find MPU6050 chip");
     while (1) 
     {
       delay(10);
     }
   }

   mpu.setAccelerometerRange(MPU6050_RANGE_16_G);
   mpu.setGyroRange(MPU6050_RANGE_250_DEG);
   mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
   
   delay(100);
   Udp.begin(localPort);
  
}

void loop() 
{
   msTicks = millis();
   if (udpTime < msTicks)
   {
       if (sampleCount == 5)
       {
          char floatString[10];
          sprintf(sendBuffer, "Data:: AccX: ");
          for (int i = 0; i < MAX_SAMPLES; i++)
          {
             sprintf(floatString, "%.4f, ", accXSamples[i]);
             strncat(sendBuffer, floatString, BUFFER_SIZE);
          }
          strcat(sendBuffer, "AccY: ");
          for (int i = 0; i < MAX_SAMPLES; i++)
          {
             sprintf(floatString, "%.4f, ", accYSamples[i]);
             strncat(sendBuffer, floatString, BUFFER_SIZE);
          }
          strcat(sendBuffer, "AccZ: ");
          for (int i = 0; i < MAX_SAMPLES; i++)
          {
             sprintf(floatString, "%.4f, ", accZSamples[i]);
             strncat(sendBuffer, floatString, BUFFER_SIZE);
          }
          sprintf(floatString, "Temp: %.4f, ", temperature);
          strcat(sendBuffer, floatString);

          float temp(NAN), hum(NAN), pres(NAN);

          BME280::TempUnit tempUnit(BME280::TempUnit_Celsius);
          BME280::PresUnit presUnit(BME280::PresUnit_Pa);

          bme.read(pres, temp, hum, tempUnit, presUnit);

          sprintf(floatString, "Pressure: %.4f, ", pres);
          strcat(sendBuffer, floatString);

          sprintf(floatString, "Temp2: %.4f", temp);
          strcat(sendBuffer, floatString);
          
          Serial.printf("%s\n", sendBuffer);
          // send a reply, to the IP address and port that sent us the packet we received
          Udp.beginPacket("192.168.1.255", 5153);
          Udp.write(sendBuffer, strlen(sendBuffer));
          Udp.endPacket();
          sampleCount = 0;
       }
       else
       {
          // Collect accelerations
          sensors_event_t a, g, temp;
          mpu.getEvent(&a, &g, &temp);
          accXSamples[sampleCount] = a.acceleration.x;
          accYSamples[sampleCount] = a.acceleration.y;
          accZSamples[sampleCount] = a.acceleration.z;
          temperature = temp.temperature;
          sampleCount++;
       }
       
       udpTime = msTicks + 200;
   }
}
