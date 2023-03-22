#define leftDirPin D1    //4
#define leftSpeedPin D2  //5

#define rightDirPin D6    //7
#define rightSpeedPin D8  //6

#define ENC_R D7
#define ENC_L D5

unsigned long enc_r = 0;
unsigned long enc_l = 0;

#include <WiFiManager.h>
WiFiManager wifiManager;

#include <PubSubClient.h>
void callback(const MQTT::Publish& pub) {
  String payload = pub.payload_string();
  String topic = pub.topic();

  //Serial.print(pub.topic()); // выводим в сериал порт название топика
  //Serial.print(" => ");
  //Serial.println(payload); // выводим в сериал порт значение полученных данных

  // проверяем из нужного ли нам топика пришли данные
  if (topic == "danisimo/move") {
    int mov = payload.toInt();
    int speed = 540;
    switch (mov) {
      case 1:
        digitalWrite(leftDirPin, LOW);
        analogWrite(leftSpeedPin, speed);

        digitalWrite(rightDirPin, LOW);
        analogWrite(rightSpeedPin, speed);
        break;
      case 2:
        digitalWrite(leftDirPin, HIGH);
        analogWrite(leftSpeedPin, speed);

        digitalWrite(rightDirPin, HIGH);
        analogWrite(rightSpeedPin, speed);
        break;
      case 3:
        digitalWrite(leftDirPin, LOW);
        analogWrite(leftSpeedPin, speed);

        digitalWrite(rightDirPin, LOW);
        analogWrite(rightSpeedPin, 0);
        break;
      case 4:
        digitalWrite(leftDirPin, LOW);
        analogWrite(leftSpeedPin, 0);

        digitalWrite(rightDirPin, LOW);
        analogWrite(rightSpeedPin, speed);
        break;
      case 5:
        digitalWrite(leftDirPin, HIGH);
        analogWrite(leftSpeedPin, 0);

        digitalWrite(rightDirPin, HIGH);
        analogWrite(rightSpeedPin, 0);
        break;
    }
  }
}

WiFiClient wclient;
PubSubClient client(wclient);

unsigned long send_timer;




void setup() {
  Serial.begin(115200);

  wifiManager.autoConnect("Water_Rover", "1234567890");

  pinMode(leftDirPin, OUTPUT);
  pinMode(leftSpeedPin, OUTPUT);
  pinMode(rightDirPin, OUTPUT);
  pinMode(rightSpeedPin, OUTPUT);

  attachInterrupt(ENC_R, encoder_r, RISING);
  attachInterrupt(ENC_L, encoder_l, RISING);
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!client.connected()) {
      Serial.println("Connecting to MQTT server");
      //client.set_server("mqtt.pi40.ru", 1883);
      client.set_server("mqtt.pi40.ru", 1883);
      if (client.connect(MQTT::Connect("arduinoClient").set_auth("danisimo", "1234567890"))) {
        Serial.println("Connected to MQTT server");
        client.set_callback(callback);

        client.subscribe("danisimo/move");
      } else {
        Serial.println("Could not connect to MQTT server");
      }
    }

    if (client.connected()) {
      if (millis() - send_timer > 2000) {
        client.publish("danisimo/test", "hello world");
      }
      client.loop();
    }
  }

  //forward_aling(1000, 1);
}


IRAM_ATTR void encoder_r() {
  enc_r += 1;
}

IRAM_ATTR void encoder_l() {
  enc_l += 1;
}

void stop_motor() {
  analogWrite(leftSpeedPin, 0);
  analogWrite(rightSpeedPin, 0);
}

void forward_aling(int speed, int turnover) {
  int speed_r = speed - 20;
  int speed_l = speed + 20;

  enc_r = 0;
  enc_l = 0;
  int delta = 0;
  //Serial.print(enc_l);Serial.print(" ");Serial.print(enc_r);Serial.println();

  while (enc_r < 38 * turnover) {
    delta = enc_r - enc_l;

    digitalWrite(leftDirPin, HIGH);
    analogWrite(leftSpeedPin, speed_l + delta);

    digitalWrite(rightDirPin, HIGH);
    analogWrite(rightSpeedPin, speed_r - delta);
    Serial.println(delta);
  }
}
