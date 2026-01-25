/*
 * Driveway Sensor - TX (Transmitter) Node
 * For Heltec WiFi LoRa 32 V3 (ESP32-S3 + SX1262)
 * 
 * Features:
 * - PIR motion sensor wake from deep sleep
 * - OLED display shows status, battery, transmission count
 * - LoRa transmission using RadioLib (SX1262 support)
 * - Ultra-low power consumption (~17µA sleeping)
 * - Battery voltage monitoring with low battery warning
 * - Automatic return to deep sleep after display timeout
 * 
 * Hardware Connections:
 * - PIR Sensor: GPIO 33 (or change PIR_PIN below)
 * - Battery: Connected to board's battery connector
 * - LoRa Antenna: MUST be connected to LoRa antenna connector
 * - Display: Built-in OLED (auto-configured)
 * 
 * Expected Battery Life: 6-12 months on 2000mAh LiPo (10 events/day)
 */

#include <heltec_unofficial.h>

// ============================================================================
// CONFIGURATION - Adjust these settings for your setup
// ============================================================================

// PIR Sensor Configuration
#define PIR_PIN           33        // GPIO pin connected to PIR sensor output
#define PIR_TRIGGER_LEVEL HIGH      // PIR output level when motion detected

// LoRa Configuration
#define LORA_FREQUENCY    915.0     // Frequency in MHz (915.0 for US, 868.0 for EU, 433.0 for Asia)
#define LORA_BANDWIDTH    125.0     // Bandwidth in kHz
#define LORA_SPREADING    7         // Spreading factor (7-12, lower = faster/shorter range)
#define LORA_CODING_RATE  5         // Coding rate (5-8)
#define LORA_TX_POWER     22        // TX power in dBm (max 22 for SX1262)
#define LORA_PREAMBLE     8         // Preamble length

// Power Management
#define DISPLAY_TIMEOUT_MS  4000    // How long to keep display on after wake (milliseconds)
#define BATTERY_ADC_PIN     1       // ADC pin for battery voltage (GPIO1 on Heltec V3)
#define BATTERY_DIVIDER     2.0     // Voltage divider ratio
#define LOW_BATTERY_MV      3300    // Low battery threshold in millivolts

// Device Identification
#define DEVICE_ID         "TX01"    // Unique identifier for this transmitter

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

RTC_DATA_ATTR uint32_t bootCount = 0;        // Persists across deep sleep
RTC_DATA_ATTR uint32_t transmissionCount = 0; // Total transmissions since first boot
unsigned long wakeTime = 0;                   // Time when device woke up

// ============================================================================
// SETUP - Runs once after wake from sleep
// ============================================================================

void setup() {
  // Initialize Heltec board (display, serial, radio)
  heltec_setup();
  
  bootCount++;
  wakeTime = millis();
  
  // Configure PIR pin
  pinMode(PIR_PIN, INPUT);
  
  Serial.println("\n========================================");
  Serial.println("Driveway Sensor TX Node - Heltec V3");
  Serial.println("========================================");
  Serial.printf("Boot #%d\n", bootCount);
  Serial.printf("Wake reason: %d\n", esp_sleep_get_wakeup_cause());
  
  // Display wake message
  display.clear();
  display.setFont(ArialMT_Plain_10);
  display.drawString(0, 0, "Driveway TX");
  display.drawString(0, 12, "Boot: " + String(bootCount));
  display.display();
  
  // Read battery voltage
  uint16_t batteryMv = readBatteryVoltage();
  Serial.printf("Battery: %d mV\n", batteryMv);
  
  // Check for low battery
  if (batteryMv < LOW_BATTERY_MV && batteryMv > 0) {
    Serial.println("WARNING: Low battery!");
    display.drawString(0, 24, "LOW BATTERY!");
    display.display();
    delay(2000);
  }
  
  // Initialize LoRa radio
  Serial.println("Initializing LoRa...");
  int state = radio.begin(LORA_FREQUENCY);
  
  if (state == RADIOLIB_ERR_NONE) {
    Serial.println("LoRa initialized successfully!");
    
    // Configure LoRa parameters
    radio.setSpreadingFactor(LORA_SPREADING);
    radio.setBandwidth(LORA_BANDWIDTH);
    radio.setCodingRate(LORA_CODING_RATE);
    radio.setOutputPower(LORA_TX_POWER);
    radio.setPreambleLength(LORA_PREAMBLE);
    
    Serial.printf("Frequency: %.1f MHz\n", LORA_FREQUENCY);
    Serial.printf("Spreading Factor: %d\n", LORA_SPREADING);
    Serial.printf("Bandwidth: %.1f kHz\n", LORA_BANDWIDTH);
    Serial.printf("TX Power: %d dBm\n", LORA_TX_POWER);
    
    // Send motion detection packet
    sendMotionPacket(batteryMv);
    
  } else {
    Serial.print("LoRa initialization failed, code: ");
    Serial.println(state);
    
    display.clear();
    display.drawString(0, 0, "LoRa FAILED!");
    display.drawString(0, 12, "Error: " + String(state));
    display.display();
    delay(2000);
  }
  
  // Display status before sleep
  displayStatus(batteryMv);
  
  // Wait for display timeout
  while (millis() - wakeTime < DISPLAY_TIMEOUT_MS) {
    heltec_loop();
    delay(10);
  }
  
  // Prepare for deep sleep
  Serial.println("Entering deep sleep...");
  Serial.println("========================================\n");
  Serial.flush();
  
  // Configure wake on PIR trigger
  esp_sleep_enable_ext0_wakeup((gpio_num_t)PIR_PIN, PIR_TRIGGER_LEVEL);
  
  // Turn off display and radio to save power
  display.clear();
  display.display();
  
  // Enter deep sleep
  esp_deep_sleep_start();
}

// ============================================================================
// LOOP - Not used (device sleeps after setup)
// ============================================================================

void loop() {
  // This will never be reached because we deep sleep at end of setup()
}

// ============================================================================
// SEND MOTION PACKET
// ============================================================================

void sendMotionPacket(uint16_t batteryMv) {
  transmissionCount++;
  
  Serial.println("\n--- Sending Motion Packet ---");
  Serial.printf("Transmission #%d\n", transmissionCount);
  
  // Create JSON packet
  String packet = "{";
  packet += "\"device\":\"" + String(DEVICE_ID) + "\",";
  packet += "\"motion\":true,";
  packet += "\"battery\":" + String(batteryMv) + ",";
  packet += "\"count\":" + String(transmissionCount) + ",";
  packet += "\"boot\":" + String(bootCount);
  packet += "}";
  
  Serial.println("Packet: " + packet);
  
  // Display transmission status
  display.clear();
  display.setFont(ArialMT_Plain_10);
  display.drawString(0, 0, "MOTION DETECTED");
  display.drawString(0, 12, "Sending...");
  display.display();
  
  // Transmit packet
  int state = radio.transmit(packet);
  
  if (state == RADIOLIB_ERR_NONE) {
    Serial.println("Transmission successful!");
    Serial.printf("Data rate: %.2f bps\n", radio.getDataRate());
    
    display.drawString(0, 24, "TX Success!");
    display.drawString(0, 36, "Count: " + String(transmissionCount));
    display.display();
    
  } else {
    Serial.print("Transmission failed, code: ");
    Serial.println(state);
    
    display.drawString(0, 24, "TX Failed!");
    display.drawString(0, 36, "Error: " + String(state));
    display.display();
  }
  
  Serial.println("-----------------------------\n");
}

// ============================================================================
// DISPLAY STATUS
// ============================================================================

void displayStatus(uint16_t batteryMv) {
  display.clear();
  display.setFont(ArialMT_Plain_10);
  
  // Title
  display.drawString(0, 0, "Driveway TX");
  
  // Battery
  String batteryStr = String(batteryMv / 1000.0, 2) + "V";
  if (batteryMv < LOW_BATTERY_MV && batteryMv > 0) {
    batteryStr += " LOW!";
  }
  display.drawString(0, 12, "Batt: " + batteryStr);
  
  // Transmission count
  display.drawString(0, 24, "TX: " + String(transmissionCount));
  
  // Boot count
  display.drawString(0, 36, "Boot: " + String(bootCount));
  
  // Sleep message
  display.drawString(0, 48, "Sleeping...");
  
  display.display();
}

// ============================================================================
// READ BATTERY VOLTAGE
// ============================================================================

uint16_t readBatteryVoltage() {
  // Configure ADC
  analogReadResolution(12);  // 12-bit resolution (0-4095)
  analogSetAttenuation(ADC_11db);  // Full scale ~3.3V
  
  // Take multiple readings and average
  uint32_t sum = 0;
  const int samples = 10;
  
  for (int i = 0; i < samples; i++) {
    sum += analogRead(BATTERY_ADC_PIN);
    delay(10);
  }
  
  uint16_t adcValue = sum / samples;
  
  // Convert ADC value to millivolts
  // ADC reading is 12-bit (0-4095) representing 0-3.3V
  // Battery voltage is divided by 2 before ADC
  uint16_t millivolts = (adcValue * 3300 * BATTERY_DIVIDER) / 4095;
  
  return millivolts;
}

// ============================================================================
// END OF CODE
// ============================================================================
