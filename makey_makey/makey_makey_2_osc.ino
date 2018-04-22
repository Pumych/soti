#include <OSCMessage.h>
#include <ESP8266WiFi.h>
#include <WiFiUdp.h>

char ssid[] = "<WIFI SSID>";          // WiFi SSID
char pass[] = "<WIFI PASS>";      // WiFi Password

const IPAddress destIp(192,0,138,100);  // Remote IP of the target device running SonicPi (OSC server)
const unsigned int destPort = 4559;     // Remote port of the target device running SonicPi (OSC server)
const unsigned int localPort = 46804;   // Any free UDP port number
const int makey1 = D5;                  // A pin that receives digital signals from MakeyMakey
const int makey2 = D7;                  // Another pin that receives digital signals from MakeyMakey
WiFiUDP Udp;                            // A UDP instance to let us send and receive packets over UDP

void sendOscKey(const char * key) {
  OSCMessage msgOut(key);
  Udp.beginPacket(destIp, destPort);
  msgOut.send(Udp);
  Udp.endPacket();
  msgOut.empty();
}

void sendOsc1() {
  sendOscKey("/1/buttonListener");
}

void sendOsc2() {
  sendOscKey("/2/buttonListener");
}


void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
    
  WiFi.begin(ssid, pass);
  
  while (WiFi.status() != WL_CONNECTED) {
      delay(500);
      Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());  

  Serial.println("Starting UDP");
  Udp.begin(localPort);
  Serial.print("Local port: ");
  Serial.println(Udp.localPort());

  pinMode(makey1, INPUT);
  pinMode(makey2, INPUT);
}


void loop() {
  attachInterrupt(makey1, sendOsc1, RISING);
  attachInterrupt(makey2, sendOsc2, RISING);
}

