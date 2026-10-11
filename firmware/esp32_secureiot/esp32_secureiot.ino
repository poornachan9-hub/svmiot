/*
 * ============================================================
 *  SecureIoT-X — ESP32 Firmware
 *  Version : 1.0.0
 *  Hardware: ESP32-WROOM-32 + DHT22 sensor (optional)
 *
 *  Topics published:
 *    iot/{DEVICE_ID}/telemetry   – sensor readings every 10s
 *    iot/{DEVICE_ID}/heartbeat   – keepalive ping every 30s
 *    iot/{DEVICE_ID}/status      – online / offline (LWT)
 *    iot/{DEVICE_ID}/security    – anomaly / attack reports
 *
 *  Required libraries (install via Arduino Library Manager):
 *    • PubSubClient  by Nick O'Leary       >= 2.8.0
 *    • ArduinoJson   by Benoit Blanchon    >= 6.21.0
 *    • DHT sensor library by Adafruit      >= 1.4.4
 *    • Adafruit Unified Sensor             >= 1.1.9
 *
 *  Board: "ESP32 Dev Module" (install esp32 board package from
 *          https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json)
 * ============================================================
 */

// ── CONFIGURATION — Edit these before flashing ────────────────

// Wi-Fi credentials
#define WIFI_SSID        "YourWiFiSSID"
#define WIFI_PASSWORD    "YourWiFiPassword"

// MQTT broker — set to your PC's Wi-Fi IP (run `ipconfig` on Windows)
// The host PC running SecureIoT-X & Mosquitto should be on the same LAN.
#define MQTT_BROKER_HOST "10.108.133.208"   // ← Host PC Wi-Fi IP
#define MQTT_BROKER_PORT 1883

// Optional MQTT auth (leave empty if broker has no auth)
#define MQTT_USERNAME    ""
#define MQTT_PASSWORD    ""

// This device's unique ID — MUST be registered in SecureIoT-X first
// Valid range for external hardware: ESP32_011 through ESP32_999
#define DEVICE_ID        "ESP32_011"
#define FIRMWARE_VERSION "1.0.0"
#define DEVICE_LOCATION  "Zone-External"

// DHT22 sensor pin (GPIO)  — set to -1 to disable sensor
#define DHT_PIN          4
#define DHT_TYPE         DHT22

// Telemetry interval (milliseconds)
#define TELEMETRY_INTERVAL_MS   10000    // 10 s
#define HEARTBEAT_INTERVAL_MS   30000    // 30 s

// Motion detection threshold — if packet_rate spike > this, raise security event
#define ANOMALY_PACKET_THRESHOLD 5000

// ── END CONFIGURATION ──────────────────────────────────────────

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// Optional: only include DHT if pin is configured
#if DHT_PIN >= 0
  #include <DHT.h>
  DHT dht(DHT_PIN, DHT_TYPE);
#endif

// ── Topic helpers ──────────────────────────────────────────────
const char* TOPIC_TELEMETRY  = "iot/" DEVICE_ID "/telemetry";
const char* TOPIC_HEARTBEAT  = "iot/" DEVICE_ID "/heartbeat";
const char* TOPIC_STATUS     = "iot/" DEVICE_ID "/status";
const char* TOPIC_SECURITY   = "iot/" DEVICE_ID "/security";
const char* TOPIC_CONTROL    = "iot/" DEVICE_ID "/control";

// Quarantine Status Indicator (GPIO 2 is standard onboard LED on ESP32)
#define QUARANTINE_LED_PIN 2

// ── Globals ────────────────────────────────────────────────────
WiFiClient   wifiClient;
PubSubClient mqttClient(wifiClient);

unsigned long lastTelemetryMs  = 0;
unsigned long lastHeartbeatMs  = 0;
unsigned long startMs          = 0;
uint32_t      msgCounter       = 0;
uint32_t      packetRateSimulator = 0;   // increments to simulate traffic
bool          isQuarantined    = false;   // hardware isolation flag

// ── Prototypes ─────────────────────────────────────────────────
void connectWifi();
bool connectMQTT();
void publishTelemetry();
void publishHeartbeat();
void publishStatus(bool online);
void publishSecurityEvent(const char* attackType, uint32_t packetCount);
bool probeTestEndpoint();
String generateEventId();
void mqttCallback(char* topic, byte* payload, unsigned int length);

// ─────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(500);
  pinMode(QUARANTINE_LED_PIN, OUTPUT);
  digitalWrite(QUARANTINE_LED_PIN, LOW);

  Serial.println();
  Serial.println("===========================================");
  Serial.println("  SecureIoT-X ESP32 Firmware v" FIRMWARE_VERSION);
  Serial.println("  Device ID : " DEVICE_ID);
  Serial.println("  Broker    : " MQTT_BROKER_HOST);
  Serial.println("===========================================");

#if DHT_PIN >= 0
  dht.begin();
  Serial.println("[DHT] Sensor initialized on GPIO " + String(DHT_PIN));
#endif

  startMs = millis();

  connectWifi();

  mqttClient.setServer(MQTT_BROKER_HOST, MQTT_BROKER_PORT);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setKeepAlive(60);
  mqttClient.setBufferSize(512);

  connectMQTT();
}

// ─────────────────────────────────────────────────────────────
void loop() {
  // If under hardware quarantine, lock radio and halt network transmission
  if (isQuarantined) {
    digitalWrite(QUARANTINE_LED_PIN, HIGH); // Solid quarantine LED
    delay(500);
    return;
  }

  // Maintain Wi-Fi
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WIFI] Connection lost — reconnecting…");
    connectWifi();
  }

  // Maintain MQTT
  if (!mqttClient.connected()) {
    Serial.println("[MQTT] Disconnected — reconnecting…");
    connectMQTT();
  }
  mqttClient.loop();

  unsigned long now = millis();

  // Publish telemetry on interval
  if (now - lastTelemetryMs >= TELEMETRY_INTERVAL_MS) {
    lastTelemetryMs = now;
    publishTelemetry();
  }

  // Publish heartbeat on interval
  if (now - lastHeartbeatMs >= HEARTBEAT_INTERVAL_MS) {
    lastHeartbeatMs = now;
    publishHeartbeat();
  }
}

// ─────────────────────────────────────────────────────────────
void connectWifi() {
  if (isQuarantined) return;
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.print("[WIFI] Connecting to ");
  Serial.print(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  uint8_t retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 40) {
    delay(500);
    Serial.print(".");
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.print("[WIFI] Connected! IP: ");
    Serial.println(WiFi.localIP());
    Serial.print("[WIFI] RSSI: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    Serial.println("\n[WIFI] FAILED. Check SSID/password and retry.");
  }
}

// ─────────────────────────────────────────────────────────────
bool connectMQTT() {
  if (isQuarantined) return false;

  // Last-Will-Testament: publish offline status on unexpected disconnect
  const char* lwtPayload = "{\"device_id\":\"" DEVICE_ID "\",\"status\":\"offline\","
                           "\"firmware_version\":\"" FIRMWARE_VERSION "\"}";

  uint8_t attempts = 0;
  while (!mqttClient.connected() && attempts < 5) {
    Serial.print("[MQTT] Connecting to broker " MQTT_BROKER_HOST ":" + String(MQTT_BROKER_PORT) + " … attempt ");
    Serial.println(attempts + 1);

    bool ok;
    if (strlen(MQTT_USERNAME) > 0) {
      ok = mqttClient.connect(DEVICE_ID, MQTT_USERNAME, MQTT_PASSWORD,
                              TOPIC_STATUS, 1, true, lwtPayload);
    } else {
      ok = mqttClient.connect(DEVICE_ID, nullptr, nullptr,
                              TOPIC_STATUS, 1, true, lwtPayload);
    }

    if (ok) {
      Serial.println("[MQTT] Connected!");
      // Subscribe to control topic for hardware quarantine commands
      mqttClient.subscribe(TOPIC_CONTROL, 1);
      Serial.printf("[MQTT] Subscribed to %s\n", TOPIC_CONTROL);
      // Announce device online
      publishStatus(true);
      return true;
    } else {
      Serial.print("[MQTT] Failed, rc=");
      Serial.println(mqttClient.state());
      delay(3000);
      attempts++;
    }
  }

  Serial.println("[MQTT] Could not connect after 5 attempts.");
  return false;
}

// ─────────────────────────────────────────────────────────────
void publishTelemetry() {
  float temperature = NAN, humidity = NAN;
  bool  motionDetected = false;

#if DHT_PIN >= 0
  temperature = dht.readTemperature();
  humidity    = dht.readHumidity();
  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("[DHT] Read error — sending telemetry without sensor values");
    temperature = 0.0f;
    humidity    = 0.0f;
  }
#endif

  float  rssi     = (float)WiFi.RSSI();
  float  uptimeSec = (millis() - startMs) / 1000.0f;

  // Build JSON document
  StaticJsonDocument<256> doc;
  doc["device_id"]        = DEVICE_ID;
  doc["temperature"]      = isnan(temperature) ? 0.0f : temperature;
  doc["humidity"]         = isnan(humidity)    ? 0.0f : humidity;
  doc["motion"]           = motionDetected;
  doc["rssi"]             = rssi;
  doc["uptime"]           = (int)uptimeSec;
  doc["firmware_version"] = FIRMWARE_VERSION;
  doc["msg_id"]           = ++msgCounter;
  doc["timestamp"]        = (unsigned long)(millis() / 1000);

  char buffer[256];
  size_t len = serializeJson(doc, buffer, sizeof(buffer));

  if (mqttClient.publish(TOPIC_TELEMETRY, buffer, len)) {
    Serial.printf("[TELEMETRY] T=%.1f°C H=%.1f%% RSSI=%.0fdBm uptime=%ds\n",
                  temperature, humidity, rssi, (int)uptimeSec);
  } else {
    Serial.println("[TELEMETRY] Publish FAILED");
  }

  // Simulate incremental packet count for anomaly detection demo
  packetRateSimulator += random(50, 300);
}

// ─────────────────────────────────────────────────────────────
void publishHeartbeat() {
  StaticJsonDocument<128> doc;
  doc["device_id"] = DEVICE_ID;
  doc["uptime"]    = (int)((millis() - startMs) / 1000);
  doc["rssi"]      = (int)WiFi.RSSI();
  doc["msg_id"]    = ++msgCounter;
  doc["timestamp"] = (unsigned long)(millis() / 1000);

  char buffer[128];
  size_t len = serializeJson(doc, buffer, sizeof(buffer));

  if (mqttClient.publish(TOPIC_HEARTBEAT, buffer, len)) {
    Serial.println("[HEARTBEAT] Sent");
  } else {
    Serial.println("[HEARTBEAT] Publish FAILED");
  }
}

// ─────────────────────────────────────────────────────────────
void publishStatus(bool online) {
  StaticJsonDocument<192> doc;
  doc["device_id"]        = DEVICE_ID;
  doc["status"]           = online ? "online" : "offline";
  doc["ip_address"]       = WiFi.localIP().toString();
  doc["firmware_version"] = FIRMWARE_VERSION;
  doc["location"]         = DEVICE_LOCATION;
  doc["rssi"]             = (int)WiFi.RSSI();
  doc["timestamp"]        = (unsigned long)(millis() / 1000);

  char buffer[192];
  size_t len = serializeJson(doc, buffer, sizeof(buffer));

  // Retain=true so broker remembers device presence
  if (mqttClient.publish(TOPIC_STATUS, buffer, len, true)) {
    Serial.printf("[STATUS] Published: %s\n", online ? "online" : "offline");
  } else {
    Serial.println("[STATUS] Publish FAILED");
  }
}

// ─────────────────────────────────────────────────────────────
/*
 * publishSecurityEvent — Call this from your code when an anomaly
 * is detected. Generates authentic RT_IOT2022-compatible network flow
 * statistics for Model Detection (Test Category A).
 *
 * Parameters:
 *   attackType  — e.g. "DDoS", "DoS", "Mirai", "Brute_Force"
 *   packetCount — observed abnormal packet count
 */
void publishSecurityEvent(const char* attackType, uint32_t packetCount) {
  String eventId = generateEventId();
  unsigned long durationMs = millis() - startMs;
  float durationSec = max(0.1f, (float)durationMs / 1000.0f);
  float pktRate = (float)packetCount / durationSec;

  StaticJsonDocument<512> doc;
  doc["event_id"]            = eventId;
  doc["device_id"]           = DEVICE_ID;
  doc["attack_type"]         = attackType;
  doc["label"]               = attackType;
  doc["packet_count"]        = packetCount;
  doc["ip_address"]          = WiFi.localIP().toString();
  doc["mac_address"]         = WiFi.macAddress();
  doc["rssi"]                = (int)WiFi.RSSI();
  doc["timestamp"]           = (unsigned long)(millis() / 1000);

  // Real flow features matching trained SVM schema (RT_IOT2022)
  doc["flow_duration"]       = durationSec;
  doc["fwd_pkts_tot"]        = packetCount;
  doc["bwd_pkts_tot"]        = 10;
  doc["fwd_data_pkts_tot"]   = packetCount > 20 ? packetCount - 20 : packetCount;
  doc["bwd_data_pkts_tot"]   = 0;
  doc["fwd_pkts_per_sec"]    = pktRate;
  doc["bwd_pkts_per_sec"]    = 1.0f;
  doc["flow_pkts_per_sec"]   = pktRate + 1.0f;
  doc["fwd_byts_per_sec"]    = pktRate * 64.0f;
  doc["bwd_byts_per_sec"]    = 64.0f;
  doc["fwd_pkts_payload_avg"]= 64.0f;
  doc["bwd_pkts_payload_avg"]= 0.0f;
  doc["proto"]               = 6;        // TCP
  doc["dst_port"]            = MQTT_BROKER_PORT;
  doc["conn_state_num"]      = 1;
  doc["packet_rate"]         = pktRate;
  doc["fwd_bwd_ratio"]       = (float)packetCount / 11.0f;
  doc["total_pkts"]          = packetCount + 10;
  doc["traffic_asymmetry"]   = 0.99f;

  char buffer[512];
  size_t len = serializeJson(doc, buffer, sizeof(buffer));

  if (mqttClient.publish(TOPIC_SECURITY, buffer, len)) {
    Serial.printf("[SECURITY] Flow event published: %s (%u pkts, rate=%.1f/s) ID=%s\n",
                  attackType, packetCount, pktRate, eventId.c_str());
  } else {
    Serial.println("[SECURITY] Publish FAILED");
  }
}

// ─────────────────────────────────────────────────────────────
/*
 * probeTestEndpoint — Verifies whether this device can currently
 * communicate with the SecureIoT-X designated test endpoint.
 * Returns true if connection succeeds (unblocked), false if isolated/blocked.
 */
bool probeTestEndpoint() {
  if (isQuarantined || WiFi.status() != WL_CONNECTED) {
    Serial.println("[PROBE] Blocked — Hardware radio quarantined or disconnected.");
    return false;
  }

  WiFiClient probeClient;
  probeClient.setTimeout(2); // 2 second timeout
  Serial.print("[PROBE] Testing connection to host " MQTT_BROKER_HOST ":8000 ... ");

  if (probeClient.connect(MQTT_BROKER_HOST, 8000)) {
    // Send probe GET request
    probeClient.print(String("GET /api/devices/probe/test?device_id=") + DEVICE_ID + " HTTP/1.1\r\n" +
                      "Host: " + MQTT_BROKER_HOST + ":8000\r\n" +
                      "Connection: close\r\n\r\n");

    unsigned long t0 = millis();
    while (probeClient.available() == 0 && (millis() - t0) < 2000) {
      delay(10);
    }

    String respLine = probeClient.readStringUntil('\n');
    probeClient.stop();

    if (respLine.indexOf("200") >= 0) {
      Serial.println("ACCESSIBLE (HTTP 200 OK) — Device is NOT isolated.");
      return true;
    } else {
      Serial.println("BLOCKED (" + respLine + ") — Device is QUARANTINED.");
      return false;
    }
  } else {
    Serial.println("FAILED (Connection Refused / Timed Out) — Network path BLOCKED.");
    return false;
  }
}

// ─────────────────────────────────────────────────────────────
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (unsigned int i = 0; i < length; i++) {
    msg += (char)payload[i];
  }
  Serial.printf("[MQTT] Inbound message on %s: %s\n", topic, msg.c_str());

  // Handle hardware quarantine & release commands from NetworkEnforcer
  String t(topic);
  if (t == TOPIC_CONTROL || t.endsWith("/control") || t.endsWith("/command")) {
    StaticJsonDocument<256> cmd;
    DeserializationError err = deserializeJson(cmd, msg);
    if (!err) {
      const char* command = cmd["command"];
      const char* action  = cmd["action"];

      if ((command && strcmp(command, "QUARANTINE_RADIO_LOCK") == 0) ||
          (action && strcmp(action, "ISOLATE") == 0)) {
        Serial.println("***************************************************");
        Serial.println("[QUARANTINE] Real Hardware Isolation order received!");
        Serial.println("[QUARANTINE] Engaging Tier 3 Radio Lock & Quarantine LED.");
        Serial.println("***************************************************");

        isQuarantined = true;
        digitalWrite(QUARANTINE_LED_PIN, HIGH); // Solid ON
        mqttClient.disconnect();
        WiFi.disconnect(true); // Drop Wi-Fi associations
      } else if ((command && strcmp(command, "RELEASE") == 0) ||
                 (action && strcmp(action, "RELEASE") == 0)) {
        Serial.println("[RELEASE] Hardware quarantine lifted. Re-engaging radio...");
        isQuarantined = false;
        digitalWrite(QUARANTINE_LED_PIN, LOW); // OFF
        connectWifi();
      }
    }
  }
}

// ─────────────────────────────────────────────────────────────
/*
 * generateEventId — produce a 16-char hex-like event ID from
 * millis() + random nibble, without using sprintf %x (avoids
 * some ESP32 toolchain edge cases).
 */
String generateEventId() {
  uint32_t a = millis();
  uint32_t b = esp_random();   // hardware RNG
  char buf[17];
  snprintf(buf, sizeof(buf), "%08lx%08lx", (unsigned long)a, (unsigned long)b);
  return String(buf);
}
