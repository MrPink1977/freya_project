/*
 * Driveway Sensor - RX (Receiver) Node
 * For Heltec WiFi LoRa 32 V3 (ESP32-S3 + SX1262)
 * 
 * Features:
 * - Continuous LoRa packet reception using RadioLib (SX1262 support)
 * - WiFi and MQTT connectivity
 * - Home Assistant auto-discovery
 * - OLED display with WiFi/MQTT/motion status
 * - RSSI and SNR signal quality monitoring
 * - Automatic reconnection handling
 * - Motion timeout (clears after 30 seconds)
 * 
 * Hardware:
 * - Heltec WiFi LoRa 32 V3 board
 * - LoRa Antenna MUST be connected
 * - Powered via USB (5V) - do not use battery for RX node
 * 
 * Home Assistant Integration:
 * - Binary sensor for motion detection
 * - Attributes: RSSI, SNR, battery voltage, packet count
 * - Auto-discovery via MQTT
 */

#include <heltec_unofficial.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ============================================================================
// CONFIGURATION - CHANGE THESE FOR YOUR SETUP
// ============================================================================

// WiFi Configuration
#define WIFI_SSID         "YourWiFiSSID"        // Your WiFi network name
#define WIFI_PASSWORD     "YourWiFiPassword"    // Your WiFi password

// MQTT Configuration
#define MQTT_SERVER       "192.168.0.40"        // Your MQTT broker IP
#define MQTT_PORT         1883                  // MQTT broker port
#define MQTT_USER         ""                    // MQTT username (empty if no auth)
#define MQTT_PASSWORD     ""                    // MQTT password (empty if no auth)
#define MQTT_CLIENT_ID    "driveway_rx"         // Unique MQTT client ID

// Home Assistant MQTT Discovery
#define HA_DISCOVERY_PREFIX   "homeassistant"
#define HA_DEVICE_NAME        "Driveway Motion"
#define HA_DEVICE_ID          "driveway_motion_sensor"

// LoRa Configuration (MUST MATCH TX NODE)
#define LORA_FREQUENCY    915.0     // Frequency in MHz
#define LORA_BANDWIDTH    125.0     // Bandwidth in kHz
#define LORA_SPREADING    7         // Spreading factor
#define LORA_CODING_RATE  5         // Coding rate
#define LORA_PREAMBLE     8         // Preamble length

// Motion Timeout
#define MOTION_TIMEOUT_MS   30000   // Clear motion after 30 seconds

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

// State variables
bool motionDetected = false;
unsigned long lastMotionTime = 0;
unsigned long lastDisplayUpdate = 0;
uint32_t packetsReceived = 0;
int lastRSSI = 0;
float lastSNR = 0;
uint16_t lastBatteryMv = 0;
String lastDeviceId = "";

// MQTT topics
String stateTopic;
String attributesTopic;
String availabilityTopic;
String configTopic;

// Display update interval
#define DISPLAY_UPDATE_INTERVAL 1000  // Update display every second

// ============================================================================
// SETUP
// ============================================================================

void setup() {
  // Initialize Heltec board
  heltec_setup();
  
  Serial.println("\n========================================");
  Serial.println("Driveway Sensor RX Node - Heltec V3");
  Serial.println("========================================\n");
  
  // Display initialization message
  display.clear();
  display.setFont(ArialMT_Plain_10);
  display.drawString(0, 0, "Driveway RX");
  display.drawString(0, 12, "Initializing...");
  display.display();
  
  // Initialize MQTT topics
  stateTopic = String(HA_DISCOVERY_PREFIX) + "/binary_sensor/" + HA_DEVICE_ID + "/state";
  attributesTopic = String(HA_DISCOVERY_PREFIX) + "/binary_sensor/" + HA_DEVICE_ID + "/attributes";
  availabilityTopic = String(HA_DISCOVERY_PREFIX) + "/binary_sensor/" + HA_DEVICE_ID + "/availability";
  configTopic = String(HA_DISCOVERY_PREFIX) + "/binary_sensor/" + HA_DEVICE_ID + "/config";
  
  // Connect to WiFi
  connectWiFi();
  
  // Setup MQTT
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setBufferSize(512);  // Increase buffer for discovery message
  connectMQTT();
  
  // Initialize LoRa
  Serial.println("Initializing LoRa...");
  int state = radio.begin(LORA_FREQUENCY);
  
  if (state == RADIOLIB_ERR_NONE) {
    Serial.println("LoRa initialized successfully!");
    
    // Configure LoRa parameters
    radio.setSpreadingFactor(LORA_SPREADING);
    radio.setBandwidth(LORA_BANDWIDTH);
    radio.setCodingRate(LORA_CODING_RATE);
    radio.setPreambleLength(LORA_PREAMBLE);
    
    // Start receiving
    radio.startReceive();
    
    Serial.printf("Frequency: %.1f MHz\n", LORA_FREQUENCY);
    Serial.printf("Spreading Factor: %d\n", LORA_SPREADING);
    Serial.printf("Bandwidth: %.1f kHz\n", LORA_BANDWIDTH);
    Serial.println("Listening for packets...\n");
    
  } else {
    Serial.print("LoRa initialization FAILED, code: ");
    Serial.println(state);
    
    display.clear();
    display.drawString(0, 0, "LoRa FAILED!");
    display.drawString(0, 12, "Error: " + String(state));
    display.display();
    
    while (true) {
      delay(1000);
    }
  }
  
  Serial.println("System ready!\n");
  Serial.println("========================================\n");
}

// ============================================================================
// MAIN LOOP
// ============================================================================

void loop() {
  heltec_loop();
  
  // Maintain MQTT connection
  if (!mqttClient.connected()) {
    connectMQTT();
  }
  mqttClient.loop();
  
  // Check for LoRa packets
  checkForPackets();
  
  // Check motion timeout
  if (motionDetected && (millis() - lastMotionTime > MOTION_TIMEOUT_MS)) {
    Serial.println("Motion timeout - clearing state");
    motionDetected = false;
    publishMotionState();
  }
  
  // Update display periodically
  if (millis() - lastDisplayUpdate > DISPLAY_UPDATE_INTERVAL) {
    updateDisplay();
    lastDisplayUpdate = millis();
  }
  
  delay(10);
}

// ============================================================================
// WIFI CONNECTION
// ============================================================================

void connectWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  
  display.clear();
  display.drawString(0, 0, "Connecting WiFi...");
  display.drawString(0, 12, WIFI_SSID);
  display.display();
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    Serial.print("Signal strength (RSSI): ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm\n");
  } else {
    Serial.println("\nWiFi connection FAILED!");
    display.clear();
    display.drawString(0, 0, "WiFi FAILED!");
    display.display();
    delay(5000);
    ESP.restart();
  }
}

// ============================================================================
// MQTT CONNECTION
// ============================================================================

void connectMQTT() {
  Serial.print("Connecting to MQTT broker: ");
  Serial.println(MQTT_SERVER);
  
  int attempts = 0;
  while (!mqttClient.connected() && attempts < 5) {
    Serial.print("Attempting MQTT connection...");
    
    // Attempt to connect
    bool connected;
    if (strlen(MQTT_USER) > 0) {
      connected = mqttClient.connect(MQTT_CLIENT_ID, MQTT_USER, MQTT_PASSWORD, 
                                     availabilityTopic.c_str(), 1, true, "offline");
    } else {
      connected = mqttClient.connect(MQTT_CLIENT_ID, availabilityTopic.c_str(), 
                                     1, true, "offline");
    }
    
    if (connected) {
      Serial.println("MQTT connected!");
      
      // Publish availability
      mqttClient.publish(availabilityTopic.c_str(), "online", true);
      
      // Publish Home Assistant discovery
      publishHomeAssistantDiscovery();
      
      // Publish initial state
      publishMotionState();
      
      return;
    } else {
      Serial.print("failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" - retrying in 5 seconds");
      delay(5000);
      attempts++;
    }
  }
  
  if (!mqttClient.connected()) {
    Serial.println("MQTT connection FAILED after 5 attempts!");
  }
}

// ============================================================================
// HOME ASSISTANT DISCOVERY
// ============================================================================

void publishHomeAssistantDiscovery() {
  Serial.println("Publishing Home Assistant discovery configuration...");
  
  StaticJsonDocument<512> doc;
  
  doc["name"] = HA_DEVICE_NAME;
  doc["unique_id"] = HA_DEVICE_ID;
  doc["device_class"] = "motion";
  doc["state_topic"] = stateTopic;
  doc["json_attributes_topic"] = attributesTopic;
  doc["availability_topic"] = availabilityTopic;
  doc["payload_on"] = "ON";
  doc["payload_off"] = "OFF";
  
  // Device information
  JsonObject device = doc.createNestedObject("device");
  device["identifiers"][0] = HA_DEVICE_ID;
  device["name"] = HA_DEVICE_NAME;
  device["model"] = "Heltec LoRa V3";
  device["manufacturer"] = "Custom";
  
  String output;
  serializeJson(doc, output);
  
  bool success = mqttClient.publish(configTopic.c_str(), output.c_str(), true);
  
  if (success) {
    Serial.println("Discovery configuration published successfully!");
  } else {
    Serial.println("Failed to publish discovery configuration!");
  }
}

// ============================================================================
// PUBLISH MOTION STATE
// ============================================================================

void publishMotionState() {
  const char* state = motionDetected ? "ON" : "OFF";
  
  bool success = mqttClient.publish(stateTopic.c_str(), state, true);
  
  if (success) {
    Serial.print("Published motion state: ");
    Serial.println(state);
  }
  
  // Publish attributes
  if (packetsReceived > 0) {
    StaticJsonDocument<256> doc;
    doc["rssi"] = lastRSSI;
    doc["snr"] = lastSNR;
    doc["battery_mv"] = lastBatteryMv;
    doc["battery_v"] = lastBatteryMv / 1000.0;
    doc["packets_received"] = packetsReceived;
    doc["device_id"] = lastDeviceId;
    
    String output;
    serializeJson(doc, output);
    
    mqttClient.publish(attributesTopic.c_str(), output.c_str(), true);
  }
}

// ============================================================================
// CHECK FOR LORA PACKETS
// ============================================================================

void checkForPackets() {
  // Check if packet is available
  if (radio.available()) {
    String packet;
    int state = radio.readData(packet);
    
    if (state == RADIOLIB_ERR_NONE) {
      packetsReceived++;
      
      // Get signal quality
      lastRSSI = radio.getRSSI();
      lastSNR = radio.getSNR();
      
      Serial.println("\n--- Packet Received ---");
      Serial.printf("Packet #%d\n", packetsReceived);
      Serial.println("Data: " + packet);
      Serial.printf("RSSI: %d dBm\n", lastRSSI);
      Serial.printf("SNR: %.2f dB\n", lastSNR);
      
      // Parse JSON packet
      StaticJsonDocument<256> doc;
      DeserializationError error = deserializeJson(doc, packet);
      
      if (!error) {
        lastDeviceId = doc["device"].as<String>();
        bool motion = doc["motion"] | false;
        lastBatteryMv = doc["battery"] | 0;
        
        Serial.printf("Device: %s\n", lastDeviceId.c_str());
        Serial.printf("Motion: %s\n", motion ? "YES" : "NO");
        Serial.printf("Battery: %d mV\n", lastBatteryMv);
        
        if (motion) {
          motionDetected = true;
          lastMotionTime = millis();
          publishMotionState();
        }
      } else {
        Serial.print("JSON parsing failed: ");
        Serial.println(error.c_str());
      }
      
      Serial.println("-----------------------\n");
      
    } else {
      Serial.print("Packet read failed, code: ");
      Serial.println(state);
    }
    
    // Start receiving again
    radio.startReceive();
  }
}

// ============================================================================
// UPDATE DISPLAY
// ============================================================================

void updateDisplay() {
  display.clear();
  display.setFont(ArialMT_Plain_10);
  
  // Title
  display.drawString(0, 0, "Driveway RX");
  
  // WiFi status
  String wifiStr = "WiFi: ";
  if (WiFi.status() == WL_CONNECTED) {
    wifiStr += "OK";
  } else {
    wifiStr += "DISCONNECTED";
  }
  display.drawString(0, 12, wifiStr);
  
  // MQTT status
  String mqttStr = "MQTT: ";
  if (mqttClient.connected()) {
    mqttStr += "OK";
  } else {
    mqttStr += "DISCONNECTED";
  }
  display.drawString(0, 24, mqttStr);
  
  // Motion status
  String motionStr = "Motion: ";
  if (motionDetected) {
    motionStr += "DETECTED";
  } else {
    motionStr += "Clear";
  }
  display.drawString(0, 36, motionStr);
  
  // Packet count and RSSI
  String statsStr = "RX:" + String(packetsReceived);
  if (packetsReceived > 0) {
    statsStr += " " + String(lastRSSI) + "dBm";
  }
  display.drawString(0, 48, statsStr);
  
  display.display();
}

// ============================================================================
// END OF CODE
// ============================================================================
