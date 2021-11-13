/***********************************************************************
* SEISMOMETER
* DESC: Simple device designed to detect and transmit any accelerations it
* detects. This device is designed to detect vibrations on the earth as
* well as earthquakes.
* 
* Author: Jonathan L Clark
* Date: 11/13/2021
***********************************************************************/

#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <SPI.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

#ifndef STASSID
#define STASSID "JLC1"
#define STAPSK  "1990clark$fam1984"
#endif

unsigned int localPort = 8888;      // local port to listen on

// buffers for receiving and sending data
//char packetBuffer[UDP_TX_PACKET_MAX_SIZE + 1]; //buffer to hold incoming packet,
char  sendBuffer[8];       // a string to send back
unsigned long msTicks = 0;
unsigned long udpTime = 0;
unsigned long motionDetectCool = 0.0;
int motionSensed = 0;
uint16_t lastAnalogRead = 0;
unsigned long ledOffTime = 0;
Adafruit_MPU6050 mpu;

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
       sendBuffer[0] = 0xCD;
       sendBuffer[1] = motionSensed;
       sendBuffer[2] = lastAnalogRead & 0x00FF;
       sendBuffer[3] = (lastAnalogRead >> 8) & 0x00FF;

       // send a reply, to the IP address and port that sent us the packet we received
       Udp.beginPacket("192.168.1.255", 3030);
       Udp.write(sendBuffer, 4);
       Udp.endPacket();

       // Collect accelerations
       sensors_event_t a, g, temp;
       mpu.getEvent(&a, &g, &temp);
       Serial.printf("Accx: %f\n", a.acceleration.x);
       Serial.printf("Accy: %f\n", a.acceleration.y);
       Serial.printf("Accz: %f\n", a.acceleration.z);
       Serial.printf("Temp: %f\n", temp.temperature);
       a.acceleration.y;
       a.acceleration.z;
       
       udpTime = msTicks + 1000;
       ledOffTime = msTicks + 500;
   }
}
