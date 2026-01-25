/*
 * Driveway Sensor - RX (Receiver) Node
 * 
 * Description:
 *   Mains-powered receiver that monitors LoRa packets from TX node,
 *   displays status on OLED, and publishes to Home Assistant via MQTT.
 * 
 * Hardware:
 *   - ESP32 (Heltec WiFi LoRa 32 V3 or compatible)
 *   - Built-in OLED display (128x64)
 *   - LoRa radio (915MHz US / 868MHz EU)
 *   - WiFi connection to home network
 * 
 * Features:
 *   - Continuous LoRa packet reception
 *   - WiFi and MQTT connectivity
 *   - Home Assistant auto-discovery
 *   - OLED status display with RSSI/SNR
 *   - Automatic reconnection handling
 * 
 * Author: Custom Build
 * Date: 2026-01-25
 * Version: 1.0
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <LoRa.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ArduinoJson.h>

// ===== CONFIGURATION =====

// WiFi Configuration
#define WIFI_SSID         "YOUR_WIFI_SSID"
#define WIFI_PASSWORD     "YOUR_WIFI_PASSWORD"
#define WIFI_TIMEOUT      20000      // WiFi connection timeout (ms)

// MQTT Configuration
#define MQTT_SERVER       "192.168.1.100"  // Your MQTT broker IP
#define MQTT_PORT         1883
#define MQTT_USER         "mqtt_user"      // Leave empty if no auth
#define MQTT_PASSWORD     "mqtt_pass"      // Leave empty if no auth
#define MQTT_CLIENT_ID    "driveway_rx"

// MQTT Topics
#define MQTT_TOPIC_STATE       "homeassistant/binary_sensor/driveway/state"
#define MQTT_TOPIC_ATTRIBUTES  "homeassistant/binary_sensor/driveway/attributes"
#define MQTT_TOPIC_CONFIG      "homeassistant/binary_sensor/driveway_motion/config"
#define MQTT_TOPIC_AVAILABLE   "homeassistant/binary_sensor/driveway/availability"

// LoRa Configuration
#define LORA_FREQUENCY    915E6      // 915MHz for US, 868MHz for EU
#define LORA_BANDWIDTH    125E3      // 125kHz bandwidth
#define LORA_SPREADING    7          // Must match TX spreading factor
#define LORA_SYNC_WORD    0x12       // Must match TX sync word

// Pin Definitions - Heltec WiFi LoRa 32 V3
#define LORA_SCK          9
#define LORA_MISO         11
#define LORA_MOSI         10
#define LORA_CS           8
#define LORA_RST          12
#define LORA_DIO0         14

#define OLED_SDA          17
#define OLED_SCL          18
#define OLED_RST          21

// Display Configuration
#define SCREEN_WIDTH      128
#define SCREEN_HEIGHT     64
#define OLED_ADDR         0x3C

// Timing Configuration
#define DISPLAY_TIMEOUT   30000      // Clear display after 30s
#define MOTION_TIMEOUT    30         // Motion auto-off after 30s
#define MQTT_RECONNECT    5000       // MQTT reconnect interval (ms)
#define WIFI_RECONNECT    10000      // WiFi reconnect interval (ms)

// ===== GLOBAL OBJECTS =====

WiFiClient espClient;
PubSubClient mqttClient(espClient);
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RST);

// ===== GLOBAL VARIABLES =====

unsigned long lastPacketTime = 0;
unsigned long lastDisplayUpdate = 0;
unsigned long lastMqttReconnect = 0;
unsigned long lastWifiReconnect = 0;
unsigned long motionDetectedTime = 0;

int packetCount = 0;
int lastRSSI = 0;
float lastSNR = 0;
float lastBattery = 0;
String lastNodeId = "";

bool motionActive = false;
bool displayNeedsUpdate = true;

// ===== FUNCTION DECLARATIONS =====

void initDisplay();
void initLoRa();
void initWiFi();
void initMQTT();
void connectWiFi();
void connectMQTT();
void publishDiscoveryConfig();
void handleLoRaPacket();
void publishMotionState(bool state);
void publishAttributes();
void updateDisplay();
void displayStatus(const char* status, const char* info = "");
void checkMotionTimeout();

// ===== SETUP =====

void setup() {
  // Initialize serial for debugging
  Serial.begin(115200);
  delay(100);
  
  Serial.println("\n\n=================================");
  Serial.println("Driveway RX Node - Receiver");
  Serial.println("=================================\n");
  
  // Initialize I2C for display
  Wire.begin(OLED_SDA, OLED_SCL);
  
  // Initialize display
  initDisplay();
  displayStatus("INIT", "Starting...");
  
  // Initialize WiFi
  initWiFi();
  
  // Initialize MQTT
  initMQTT();
  
  // Initialize LoRa
  initLoRa();
  
  // Publish discovery configuration
  publishDiscoveryConfig();
  
  // Initial display update
  displayStatus("READY", "Waiting...");
  
  Serial.println("\n=================================");
  Serial.println("System ready - Listening for packets");
  Serial.println("=================================\n");
}

// ===== MAIN LOOP =====

void loop() {
  // Maintain WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    if (millis() - lastWifiReconnect > WIFI_RECONNECT) {
      Serial.println("WiFi disconnected, reconnecting...");
      connectWiFi();
      lastWifiReconnect = millis();
    }
  }
  
  // Maintain MQTT connection
  if (!mqttClient.connected()) {
    if (millis() - lastMqttReconnect > MQTT_RECONNECT) {
      Serial.println("MQTT disconnected, reconnecting...");
      connectMQTT();
      lastMqttReconnect = millis();
    }
  } else {
    mqttClient.loop();
  }
  
  // Check for LoRa packets
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    handleLoRaPacket();
  }
  
  // Check motion timeout
  checkMotionTimeout();
  
  // Update display if needed
  if (displayNeedsUpdate) {
    updateDisplay();
    displayNeedsUpdate = false;
  }
  
  // Small delay to prevent watchdog issues
  delay(10);
}

// ===== DISPLAY FUNCTIONS =====

/**
 * Initialize OLED display
 */
void initDisplay() {
  Serial.println("Initializing display...");
  
  // Reset display
  pinMode(OLED_RST, OUTPUT);
  digitalWrite(OLED_RST, LOW);
  delay(20);
  digitalWrite(OLED_RST, HIGH);
  delay(20);
  
  // Initialize display
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("ERROR: Display initialization failed!");
  } else {
    Serial.println("Display initialized successfully");
  }
  
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.display();
}

/**
 * Display status message
 */
void displayStatus(const char* status, const char* info) {
  display.clearDisplay();
  display.setTextSize(2);
  display.setCursor(0, 0);
  display.println(status);
  
  display.setTextSize(1);
  display.setCursor(0, 24);
  display.println(info);
  
  display.display();
}

/**
 * Update display with current status
 */
void updateDisplay() {
  display.clearDisplay();
  
  // Title
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("Driveway RX");
  
  // WiFi status
  display.setCursor(0, 12);
  if (WiFi.status() == WL_CONNECTED) {
    display.print("WiFi: OK");
  } else {
    display.print("WiFi: --");
  }
  
  // MQTT status
  display.setCursor(70, 12);
  if (mqttClient.connected()) {
    display.print("MQTT: OK");
  } else {
    display.print("MQTT: --");
  }
  
  // Motion status
  display.setCursor(0, 24);
  display.setTextSize(2);
  if (motionActive) {
    display.println("MOTION!");
  } else {
    display.println("Idle");
  }
  
  // Last packet info
  display.setTextSize(1);
  display.setCursor(0, 44);
  display.print("RSSI:");
  display.print(lastRSSI);
  display.print(" SNR:");
  display.println(lastSNR, 1);
  
  display.setCursor(0, 54);
  display.print("Bat:");
  display.print(lastBattery, 2);
  display.print("V Cnt:");
  display.println(packetCount);
  
  display.display();
}

// ===== WIFI FUNCTIONS =====

/**
 * Initialize WiFi connection
 */
void initWiFi() {
  Serial.println("Initializing WiFi...");
  displayStatus("WIFI", "Connecting...");
  
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  
  connectWiFi();
}

/**
 * Connect to WiFi network
 */
void connectWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  unsigned long startTime = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startTime < WIFI_TIMEOUT) {
    delay(500);
    Serial.print(".");
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    Serial.print("Signal strength (RSSI): ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    Serial.println("\nWiFi connection failed!");
  }
}

// ===== MQTT FUNCTIONS =====

/**
 * Initialize MQTT client
 */
void initMQTT() {
  Serial.println("Initializing MQTT...");
  displayStatus("MQTT", "Connecting...");
  
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setKeepAlive(60);
  mqttClient.setSocketTimeout(30);
  
  connectMQTT();
}

/**
 * Connect to MQTT broker
 */
void connectMQTT() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Cannot connect to MQTT - WiFi not connected");
    return;
  }
  
  Serial.print("Connecting to MQTT broker: ");
  Serial.println(MQTT_SERVER);
  
  // Attempt connection
  bool connected = false;
  if (strlen(MQTT_USER) > 0) {
    connected = mqttClient.connect(MQTT_CLIENT_ID, MQTT_USER, MQTT_PASSWORD, 
                                   MQTT_TOPIC_AVAILABLE, 1, true, "offline");
  } else {
    connected = mqttClient.connect(MQTT_CLIENT_ID, MQTT_TOPIC_AVAILABLE, 1, true, "offline");
  }
  
  if (connected) {
    Serial.println("MQTT connected!");
    
    // Publish availability
    mqttClient.publish(MQTT_TOPIC_AVAILABLE, "online", true);
    
    // Publish initial state
    publishMotionState(false);
    
  } else {
    Serial.print("MQTT connection failed, rc=");
    Serial.println(mqttClient.state());
  }
}

/**
 * Publish Home Assistant discovery configuration
 */
void publishDiscoveryConfig() {
  if (!mqttClient.connected()) {
    Serial.println("Cannot publish discovery - MQTT not connected");
    return;
  }
  
  Serial.println("Publishing Home Assistant discovery configuration...");
  
  // Create JSON document
  StaticJsonDocument<1024> doc;
  
  doc["name"] = "Driveway Motion";
  doc["device_class"] = "motion";
  doc["state_topic"] = MQTT_TOPIC_STATE;
  doc["payload_on"] = "ON";
  doc["payload_off"] = "OFF";
  doc["off_delay"] = MOTION_TIMEOUT;
  doc["json_attributes_topic"] = MQTT_TOPIC_ATTRIBUTES;
  doc["availability_topic"] = MQTT_TOPIC_AVAILABLE;
  doc["payload_available"] = "online";
  doc["payload_not_available"] = "offline";
  doc["unique_id"] = "driveway_motion_sensor";
  doc["qos"] = 1;
  
  // Device information
  JsonObject device = doc.createNestedObject("device");
  device["identifiers"][0] = "driveway_lora_sensor";
  device["name"] = "Driveway LoRa Sensor";
  device["model"] = "ESP32 LoRa";
  device["manufacturer"] = "Custom";
  device["sw_version"] = "1.0";
  
  // Serialize JSON
  String output;
  serializeJson(doc, output);
  
  // Publish configuration
  bool success = mqttClient.publish(MQTT_TOPIC_CONFIG, output.c_str(), true);
  
  if (success) {
    Serial.println("Discovery configuration published successfully");
  } else {
    Serial.println("Failed to publish discovery configuration");
  }
}

/**
 * Publish motion state to MQTT
 */
void publishMotionState(bool state) {
  if (!mqttClient.connected()) {
    return;
  }
  
  const char* payload = state ? "ON" : "OFF";
  mqttClient.publish(MQTT_TOPIC_STATE, payload, true);
  
  Serial.print("Published motion state: ");
  Serial.println(payload);
}

/**
 * Publish sensor attributes to MQTT
 */
void publishAttributes() {
  if (!mqttClient.connected()) {
    return;
  }
  
  // Create JSON document
  StaticJsonDocument<512> doc;
  
  doc["rssi"] = lastRSSI;
  doc["snr"] = lastSNR;
  doc["battery"] = lastBattery;
  doc["packet_count"] = packetCount;
  doc["node_id"] = lastNodeId;
  
  // Add timestamp
  unsigned long uptime = millis() / 1000;
  doc["uptime"] = uptime;
  
  // Serialize JSON
  String output;
  serializeJson(doc, output);
  
  // Publish attributes
  mqttClient.publish(MQTT_TOPIC_ATTRIBUTES, output.c_str(), true);
  
  Serial.println("Published attributes: " + output);
}

// ===== LORA FUNCTIONS =====

/**
 * Initialize LoRa radio
 */
void initLoRa() {
  Serial.println("Initializing LoRa...");
  displayStatus("LORA", "Initializing...");
  
  // Set LoRa pins
  LoRa.setPins(LORA_CS, LORA_RST, LORA_DIO0);
  
  // Initialize LoRa
  if (!LoRa.begin(LORA_FREQUENCY)) {
    Serial.println("ERROR: Starting LoRa failed!");
    displayStatus("ERROR", "LoRa init failed");
    while (1) {
      delay(1000);
    }
  }
  
  // Configure LoRa parameters (must match TX)
  LoRa.setSpreadingFactor(LORA_SPREADING);
  LoRa.setSignalBandwidth(LORA_BANDWIDTH);
  LoRa.setCodingRate4(5);
  LoRa.setSyncWord(LORA_SYNC_WORD);
  LoRa.enableCrc();
  
  Serial.println("LoRa initialized successfully");
  Serial.printf("Frequency: %.1f MHz\n", LORA_FREQUENCY / 1E6);
  Serial.printf("Bandwidth: %.0f kHz\n", LORA_BANDWIDTH / 1E3);
  Serial.printf("Spreading Factor: %d\n", LORA_SPREADING);
}

/**
 * Handle incoming LoRa packet
 */
void handleLoRaPacket() {
  Serial.println("\n--- Packet Received ---");
  
  // Read packet
  String message = "";
  while (LoRa.available()) {
    message += (char)LoRa.read();
  }
  
  // Get RSSI and SNR
  lastRSSI = LoRa.packetRssi();
  lastSNR = LoRa.packetSnr();
  
  Serial.println("Message: " + message);
  Serial.printf("RSSI: %d dBm\n", lastRSSI);
  Serial.printf("SNR: %.2f dB\n", lastSNR);
  
  // Parse JSON packet
  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, message);
  
  if (error) {
    Serial.print("JSON parsing failed: ");
    Serial.println(error.c_str());
    return;
  }
  
  // Extract packet data
  const char* type = doc["type"];
  lastNodeId = doc["node"].as<String>();
  lastBattery = doc["battery"];
  
  Serial.printf("Type: %s\n", type);
  Serial.printf("Node: %s\n", lastNodeId.c_str());
  Serial.printf("Battery: %.2fV\n", lastBattery);
  
  // Increment packet counter
  packetCount++;
  lastPacketTime = millis();
  
  // Handle motion event
  if (strcmp(type, "motion") == 0) {
    motionActive = true;
    motionDetectedTime = millis();
    
    // Publish to MQTT
    publishMotionState(true);
    publishAttributes();
  }
  
  // Update display
  displayNeedsUpdate = true;
  
  Serial.println("--- End Packet ---\n");
}

/**
 * Check if motion timeout has expired
 */
void checkMotionTimeout() {
  if (motionActive && (millis() - motionDetectedTime > MOTION_TIMEOUT * 1000)) {
    motionActive = false;
    publishMotionState(false);
    displayNeedsUpdate = true;
    Serial.println("Motion timeout - state set to OFF");
  }
}

// ===== END OF CODE =====
