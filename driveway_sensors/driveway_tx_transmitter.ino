/*
 * Driveway Sensor - TX (Transmitter) Node
 * 
 * Description:
 *   Battery-powered PIR motion sensor that wakes from deep sleep,
 *   displays status on OLED, transmits via LoRa, then returns to sleep.
 * 
 * Hardware:
 *   - ESP32 (Heltec WiFi LoRa 32 V3 or compatible)
 *   - PIR motion sensor on GPIO 33 (RTC wake capable)
 *   - Built-in OLED display (128x64)
 *   - LoRa radio (915MHz US / 868MHz EU)
 *   - Battery voltage monitoring on GPIO 1
 * 
 * Power Consumption:
 *   - Deep sleep: ~10-20µA
 *   - Active (transmit): ~120mA for 3-5 seconds
 *   - Expected battery life: 6-12 months (2000mAh LiPo, 10 events/day)
 * 
 * Author: Custom Build
 * Date: 2026-01-25
 * Version: 1.0
 */

#include <Arduino.h>
#include <LoRa.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ===== CONFIGURATION =====

// LoRa Configuration
#define LORA_FREQUENCY    915E6      // 915MHz for US, 868MHz for EU
#define LORA_BANDWIDTH    125E3      // 125kHz bandwidth
#define LORA_SPREADING    7          // SF7 (faster) to SF9 (longer range)
#define LORA_TX_POWER     20         // 20dBm maximum
#define LORA_SYNC_WORD    0x12       // Private network sync word

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

#define PIR_PIN           33         // RTC_GPIO4 - wake capable
#define BATTERY_PIN       1          // ADC pin for battery voltage

// Display Configuration
#define SCREEN_WIDTH      128
#define SCREEN_HEIGHT     64
#define OLED_ADDR         0x3C

// Timing Configuration
#define DISPLAY_TIMEOUT   4000       // Display on time (ms)
#define DEBOUNCE_TIME     100        // PIR debounce (ms)

// Battery Configuration
#define BATTERY_DIVIDER   2.0        // Voltage divider ratio
#define LOW_BATTERY_V     3.3        // Low battery threshold (V)

// Node Identification
#define NODE_ID           "driveway_tx"

// ===== GLOBAL OBJECTS =====

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RST);

// ===== RTC MEMORY (Preserved during deep sleep) =====
RTC_DATA_ATTR int bootCount = 0;
RTC_DATA_ATTR unsigned long totalTransmissions = 0;

// ===== FUNCTION DECLARATIONS =====

void initDisplay();
void initLoRa();
void displayMessage(const char* line1, const char* line2 = "", const char* line3 = "", const char* line4 = "");
void displayStatus(const char* status, float battery, int rssi = 0);
float readBatteryVoltage();
void transmitMotionEvent();
void enterDeepSleep();
void print_wakeup_reason();

// ===== SETUP =====

void setup() {
  // Initialize serial for debugging
  Serial.begin(115200);
  delay(100);
  
  // Increment boot count
  bootCount++;
  
  Serial.println("\n\n=================================");
  Serial.println("Driveway TX Node - Motion Sensor");
  Serial.println("=================================");
  Serial.printf("Boot count: %d\n", bootCount);
  Serial.printf("Total transmissions: %lu\n", totalTransmissions);
  
  // Print wakeup reason
  print_wakeup_reason();
  
  // Initialize I2C for display
  Wire.begin(OLED_SDA, OLED_SCL);
  
  // Initialize display
  initDisplay();
  
  // Read battery voltage
  float batteryVoltage = readBatteryVoltage();
  Serial.printf("Battery voltage: %.2fV\n", batteryVoltage);
  
  // Check for low battery
  if (batteryVoltage < LOW_BATTERY_V) {
    displayMessage("LOW BATTERY!", 
                   String(batteryVoltage, 2).c_str(), 
                   "Replace battery", 
                   "Sleeping...");
    delay(5000);
    enterDeepSleep();
    return;
  }
  
  // Initialize LoRa
  initLoRa();
  
  // Display motion detected
  displayStatus("MOTION", batteryVoltage);
  delay(1000);
  
  // Transmit motion event
  transmitMotionEvent();
  
  // Display transmission complete
  displayMessage("TRANSMITTED", 
                 String("Battery: " + String(batteryVoltage, 2) + "V").c_str(),
                 String("Count: " + String(totalTransmissions)).c_str(),
                 "Sleeping...");
  
  // Keep display on for timeout period
  delay(DISPLAY_TIMEOUT);
  
  // Enter deep sleep
  enterDeepSleep();
}

// ===== LOOP (Never reached - device sleeps after setup) =====

void loop() {
  // This should never be reached
  delay(1000);
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
    // Continue anyway - not critical
  } else {
    Serial.println("Display initialized successfully");
  }
  
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("Driveway TX");
  display.println("Initializing...");
  display.display();
}

/**
 * Display multi-line message
 */
void displayMessage(const char* line1, const char* line2, const char* line3, const char* line4) {
  display.clearDisplay();
  display.setTextSize(2);
  display.setCursor(0, 0);
  display.println(line1);
  
  display.setTextSize(1);
  display.setCursor(0, 20);
  display.println(line2);
  display.setCursor(0, 32);
  display.println(line3);
  display.setCursor(0, 44);
  display.println(line4);
  
  display.display();
}

/**
 * Display status with battery and signal info
 */
void displayStatus(const char* status, float battery, int rssi) {
  display.clearDisplay();
  
  // Large status text
  display.setTextSize(2);
  display.setCursor(0, 0);
  display.println(status);
  
  // Battery voltage
  display.setTextSize(1);
  display.setCursor(0, 24);
  display.print("Battery: ");
  display.print(battery, 2);
  display.println("V");
  
  // Boot count
  display.setCursor(0, 36);
  display.print("Boot: ");
  display.println(bootCount);
  
  // Transmission count
  display.setCursor(0, 48);
  display.print("TX: ");
  display.println(totalTransmissions);
  
  display.display();
}

// ===== LORA FUNCTIONS =====

/**
 * Initialize LoRa radio
 */
void initLoRa() {
  Serial.println("Initializing LoRa...");
  
  // Set LoRa pins
  LoRa.setPins(LORA_CS, LORA_RST, LORA_DIO0);
  
  // Initialize LoRa
  if (!LoRa.begin(LORA_FREQUENCY)) {
    Serial.println("ERROR: Starting LoRa failed!");
    displayMessage("LORA ERROR", "Init failed", "Check wiring", "Sleeping...");
    delay(5000);
    enterDeepSleep();
    return;
  }
  
  // Configure LoRa parameters
  LoRa.setSpreadingFactor(LORA_SPREADING);
  LoRa.setSignalBandwidth(LORA_BANDWIDTH);
  LoRa.setCodingRate4(5);  // 4/5 coding rate
  LoRa.setSyncWord(LORA_SYNC_WORD);
  LoRa.setTxPower(LORA_TX_POWER);
  LoRa.enableCrc();
  
  Serial.println("LoRa initialized successfully");
  Serial.printf("Frequency: %.1f MHz\n", LORA_FREQUENCY / 1E6);
  Serial.printf("Bandwidth: %.0f kHz\n", LORA_BANDWIDTH / 1E3);
  Serial.printf("Spreading Factor: %d\n", LORA_SPREADING);
  Serial.printf("TX Power: %d dBm\n", LORA_TX_POWER);
}

/**
 * Transmit motion detection event via LoRa
 */
void transmitMotionEvent() {
  Serial.println("Transmitting motion event...");
  
  // Read battery voltage
  float batteryVoltage = readBatteryVoltage();
  
  // Build JSON packet
  String packet = "{";
  packet += "\"type\":\"motion\",";
  packet += "\"node\":\"" + String(NODE_ID) + "\",";
  packet += "\"boot\":" + String(bootCount) + ",";
  packet += "\"count\":" + String(totalTransmissions) + ",";
  packet += "\"battery\":" + String(batteryVoltage, 2) + ",";
  packet += "\"millis\":" + String(millis());
  packet += "}";
  
  Serial.println("Packet: " + packet);
  
  // Send packet
  LoRa.beginPacket();
  LoRa.print(packet);
  LoRa.endPacket();
  
  // Increment transmission counter
  totalTransmissions++;
  
  Serial.println("Transmission complete");
  Serial.printf("Total transmissions: %lu\n", totalTransmissions);
}

// ===== BATTERY FUNCTIONS =====

/**
 * Read battery voltage from ADC
 */
float readBatteryVoltage() {
  // Read ADC value (0-4095 for 12-bit ADC)
  int adcValue = analogRead(BATTERY_PIN);
  
  // Convert to voltage (ESP32 ADC reference is 3.3V)
  // Apply voltage divider correction
  float voltage = (adcValue / 4095.0) * 3.3 * BATTERY_DIVIDER;
  
  Serial.printf("Battery ADC: %d, Voltage: %.2fV\n", adcValue, voltage);
  
  return voltage;
}

// ===== SLEEP FUNCTIONS =====

/**
 * Print wakeup reason for debugging
 */
void print_wakeup_reason() {
  esp_sleep_wakeup_cause_t wakeup_reason;
  wakeup_reason = esp_sleep_get_wakeup_cause();
  
  switch(wakeup_reason) {
    case ESP_SLEEP_WAKEUP_EXT0:
      Serial.println("Wakeup caused by external signal (RTC_IO)");
      break;
    case ESP_SLEEP_WAKEUP_EXT1:
      Serial.println("Wakeup caused by external signal (RTC_CNTL)");
      break;
    case ESP_SLEEP_WAKEUP_TIMER:
      Serial.println("Wakeup caused by timer");
      break;
    case ESP_SLEEP_WAKEUP_TOUCHPAD:
      Serial.println("Wakeup caused by touchpad");
      break;
    case ESP_SLEEP_WAKEUP_ULP:
      Serial.println("Wakeup caused by ULP program");
      break;
    default:
      Serial.printf("Wakeup was not caused by deep sleep: %d\n", wakeup_reason);
      break;
  }
}

/**
 * Configure and enter deep sleep mode
 */
void enterDeepSleep() {
  Serial.println("\n=================================");
  Serial.println("Entering deep sleep mode...");
  Serial.println("Waiting for PIR trigger on GPIO 33");
  Serial.println("=================================\n");
  
  // Clear display
  display.clearDisplay();
  display.display();
  
  // Deinitialize LoRa to save power
  LoRa.end();
  
  // Configure PIR pin as wakeup source
  // ESP_EXT0 wakeup: single GPIO, HIGH or LOW level
  esp_sleep_enable_ext0_wakeup(GPIO_NUM_33, HIGH);
  
  // Optional: Enable wakeup on LOW as well (depends on PIR behavior)
  // Some PIRs stay HIGH while motion is detected
  // Adjust based on your PIR sensor characteristics
  
  // Flush serial before sleeping
  Serial.flush();
  delay(100);
  
  // Enter deep sleep
  esp_deep_sleep_start();
  
  // Code never reaches here
}

// ===== END OF CODE =====
