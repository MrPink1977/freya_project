# Driveway Sensor System - Troubleshooting Checklist

Use this checklist to systematically diagnose and fix issues with your driveway sensor system.

## Pre-Flight Checklist

Before troubleshooting, verify these basics:

- [ ] Both nodes have power (battery for TX, USB/mains for RX)
- [ ] Arduino IDE has ESP32 board support installed
- [ ] All required libraries are installed (see libraries.txt)
- [ ] Correct board selected: Heltec WiFi LoRa 32(V3)
- [ ] Correct COM port selected
- [ ] Serial Monitor set to 115200 baud
- [ ] Antennas are connected to both nodes

## TX Node (Transmitter) Troubleshooting

### Issue: Code won't compile

- [ ] Check all required libraries are installed
- [ ] Verify ESP32 board support is installed (version 2.0.0+)
- [ ] Close and reopen Arduino IDE
- [ ] Check for typos in configuration section
- [ ] Verify ArduinoJson is version 6.x (not 7.x)

### Issue: Code won't upload

- [ ] Correct board selected: Heltec WiFi LoRa 32(V3)
- [ ] Correct COM port selected
- [ ] Try different USB cable (data cable, not charge-only)
- [ ] Press and hold "PRG" button during upload if available
- [ ] Reduce upload speed to 115200
- [ ] Try different USB port on computer
- [ ] Disconnect battery during upload

### Issue: "Starting LoRa failed!" on display

**Hardware Checks**:
- [ ] LoRa module is properly seated on board
- [ ] Antenna is connected to LoRa module
- [ ] No loose connections or solder bridges
- [ ] Board is genuine Heltec (not clone with different pins)

**Software Checks**:
- [ ] Pin definitions match your board (lines 42-54)
- [ ] Frequency is correct for your region (915MHz US, 868MHz EU)
- [ ] LoRa library is installed correctly
- [ ] Try different spreading factor (7, 9, or 12)

**Testing**:
- [ ] Upload basic LoRa example sketch to verify hardware
- [ ] Check Serial Monitor for detailed error messages
- [ ] Measure voltage on LoRa module pins (should be 3.3V)

### Issue: TX won't wake from deep sleep

**PIR Sensor Checks**:
- [ ] PIR sensor has power (3.3V between VCC and GND)
- [ ] PIR output is connected to GPIO 33
- [ ] PIR sensitivity is adjusted (turn potentiometer)
- [ ] PIR delay is set to minimum (turn other potentiometer)
- [ ] PIR sensor LED blinks when motion detected

**GPIO Checks**:
- [ ] GPIO 33 is RTC-capable (it is - this is correct)
- [ ] No other peripherals using GPIO 33
- [ ] Wire connection is solid (not loose)

**Code Checks**:
- [ ] `esp_sleep_enable_ext0_wakeup(GPIO_NUM_33, HIGH)` is called
- [ ] PIR_PIN is defined as 33
- [ ] Code reaches deep sleep (Serial Monitor shows "Entering deep sleep")

**Testing**:
- [ ] Test PIR separately with simple Arduino sketch
- [ ] Manually connect GPIO 33 to 3.3V to trigger wake
- [ ] Try different RTC-capable GPIO pin
- [ ] Check Serial Monitor for wake reason on boot

### Issue: Display doesn't work

**Hardware Checks**:
- [ ] Display is properly connected to board
- [ ] No loose I2C connections
- [ ] Display has power

**Software Checks**:
- [ ] I2C address is correct (0x3C is standard)
- [ ] SDA/SCL pins match your board (17/18 for Heltec V3)
- [ ] Adafruit SSD1306 library is installed
- [ ] Adafruit GFX library is installed

**Testing**:
- [ ] Upload Adafruit SSD1306 example sketch
- [ ] Use I2C scanner sketch to find display address
- [ ] Check Serial Monitor for display init messages

### Issue: Battery drains too quickly

**Expected vs Actual**:
- [ ] Measure actual sleep current with multimeter
- [ ] Should be 10-20µA in deep sleep
- [ ] If higher, check for current leaks

**Optimization**:
- [ ] Reduce DISPLAY_TIMEOUT to 2-3 seconds
- [ ] Lower LORA_TX_POWER if range is sufficient
- [ ] Verify ESP32 enters deep sleep (Serial Monitor)
- [ ] Disconnect PIR and measure sleep current
- [ ] Check battery capacity (should be 2000mAh+)
- [ ] Verify battery is not damaged/old

**Testing**:
- [ ] Measure current with multimeter in series with battery
- [ ] Check voltage drop during transmission
- [ ] Monitor battery voltage over 24 hours

### Issue: Low battery warning appears immediately

**Calibration**:
- [ ] Measure actual battery voltage with multimeter
- [ ] Compare to voltage shown in Serial Monitor
- [ ] Adjust BATTERY_DIVIDER constant if needed
- [ ] Verify voltage divider circuit is correct (if used)

**Battery**:
- [ ] Check battery is fully charged (4.2V for LiPo)
- [ ] Verify battery is not damaged
- [ ] Check battery connector is secure

## RX Node (Receiver) Troubleshooting

### Issue: WiFi won't connect

**Network Checks**:
- [ ] SSID is correct (case-sensitive)
- [ ] Password is correct (case-sensitive)
- [ ] WiFi is 2.4GHz (ESP32 doesn't support 5GHz)
- [ ] Router is powered on and working
- [ ] Other devices can connect to same network

**Signal Checks**:
- [ ] RX node is within range of router
- [ ] No thick walls/metal between node and router
- [ ] Router is not on DFS channel (use channel 1, 6, or 11)

**Router Settings**:
- [ ] MAC filtering is disabled (or add ESP32 MAC)
- [ ] DHCP is enabled
- [ ] Maximum clients limit not reached
- [ ] No special characters in SSID/password

**Code Checks**:
- [ ] WIFI_SSID and WIFI_PASSWORD are correct
- [ ] No extra spaces in credentials
- [ ] WiFi credentials are in quotes

**Testing**:
- [ ] Try different WiFi network (mobile hotspot)
- [ ] Check Serial Monitor for connection attempts
- [ ] Upload basic WiFi example sketch to test
- [ ] Increase WIFI_TIMEOUT if network is slow

### Issue: MQTT won't connect

**Broker Checks**:
- [ ] MQTT broker is running (check Home Assistant)
- [ ] MQTT broker IP address is correct
- [ ] MQTT port is correct (default 1883)
- [ ] Broker allows external connections

**Authentication**:
- [ ] MQTT username is correct (or empty if no auth)
- [ ] MQTT password is correct (or empty if no auth)
- [ ] Broker requires authentication (check settings)

**Network**:
- [ ] RX node is connected to WiFi first
- [ ] RX node can ping MQTT broker IP
- [ ] No firewall blocking port 1883
- [ ] Broker and RX node on same network/VLAN

**Code Checks**:
- [ ] MQTT_SERVER IP is correct
- [ ] MQTT_PORT is correct (1883 standard)
- [ ] MQTT_USER and MQTT_PASSWORD match broker

**Testing**:
- [ ] Use MQTT Explorer to test broker connection
- [ ] Check Home Assistant MQTT integration status
- [ ] Try connecting from computer with MQTT client
- [ ] Check Serial Monitor for MQTT error codes

### Issue: "Starting LoRa failed!" on RX

- [ ] See TX node "Starting LoRa failed!" section above
- [ ] All checks apply to RX node as well

### Issue: Not receiving packets from TX

**LoRa Configuration**:
- [ ] Both nodes use same frequency (915MHz or 868MHz)
- [ ] Both nodes use same spreading factor
- [ ] Both nodes use same bandwidth (125kHz)
- [ ] Both nodes use same sync word (0x12)

**Hardware**:
- [ ] Antennas are connected to both nodes
- [ ] Antennas are not damaged
- [ ] LoRa modules are working (check with examples)

**Range**:
- [ ] Nodes are within range (start with 1-2 meters)
- [ ] No thick walls/metal between nodes
- [ ] Antennas are oriented similarly

**TX Node**:
- [ ] TX is actually transmitting (check Serial Monitor)
- [ ] TX completes transmission before sleeping
- [ ] TX LoRa init succeeds (no "Starting LoRa failed!")

**Testing**:
- [ ] Place nodes 1 meter apart for testing
- [ ] Check Serial Monitor on both nodes
- [ ] Verify TX shows "Transmission complete"
- [ ] Verify RX shows "Packet Received"
- [ ] Check RSSI and SNR values (should be high when close)

### Issue: Display shows wrong information

**Status Checks**:
- [ ] WiFi status matches actual connection
- [ ] MQTT status matches actual connection
- [ ] Motion state changes when packet received

**Packet Data**:
- [ ] RSSI value is reasonable (-30 to -120 dBm)
- [ ] SNR value is reasonable (-20 to +10 dB)
- [ ] Battery voltage is reasonable (3.0-4.2V)
- [ ] Packet count increments with each packet

**Code**:
- [ ] Display update function is called
- [ ] No display timeout clearing screen prematurely
- [ ] Variables are updated when packet received

## Home Assistant Integration Troubleshooting

### Issue: Sensor doesn't appear in Home Assistant

**MQTT Integration**:
- [ ] MQTT integration is installed in Home Assistant
- [ ] MQTT integration is configured correctly
- [ ] MQTT discovery is enabled (default)
- [ ] Broker is running and accessible

**RX Node**:
- [ ] RX node is connected to MQTT
- [ ] Discovery message is published (check Serial Monitor)
- [ ] Topics match Home Assistant expectations

**Testing**:
- [ ] Check Developer Tools → MQTT in Home Assistant
- [ ] Subscribe to `homeassistant/#` to see all messages
- [ ] Verify discovery message is published
- [ ] Check Home Assistant logs for errors

### Issue: Sensor shows "unavailable"

**Availability**:
- [ ] RX node is powered on
- [ ] RX node is connected to WiFi
- [ ] RX node is connected to MQTT
- [ ] Availability topic is published

**MQTT**:
- [ ] Broker is running
- [ ] No network issues between RX and broker
- [ ] Retained messages are enabled on broker

**Testing**:
- [ ] Check MQTT Explorer for availability topic
- [ ] Restart RX node
- [ ] Check Home Assistant MQTT integration status
- [ ] Verify availability topic payload is "online"

### Issue: Sensor state doesn't change

**Packet Reception**:
- [ ] RX node is receiving packets (check Serial Monitor)
- [ ] Packets are parsed correctly (check Serial Monitor)
- [ ] Motion state is published to MQTT

**MQTT Topics**:
- [ ] State topic matches Home Assistant configuration
- [ ] Payload is "ON" or "OFF" (case-sensitive)
- [ ] Messages are being published (check MQTT Explorer)

**Home Assistant**:
- [ ] Entity is not disabled in Home Assistant
- [ ] No automation overriding state
- [ ] State topic is correct in entity configuration

**Testing**:
- [ ] Trigger TX node and watch Serial Monitor on RX
- [ ] Check MQTT Explorer for state topic messages
- [ ] Check Home Assistant Developer Tools → States
- [ ] Manually publish "ON" to state topic to test

### Issue: Attributes not showing

**MQTT Configuration**:
- [ ] Attributes topic is configured in discovery
- [ ] Attributes are published when packet received
- [ ] JSON format is correct

**Home Assistant**:
- [ ] Entity has json_attributes_topic configured
- [ ] Attributes appear in Developer Tools → States
- [ ] Attributes are not filtered by recorder

**Testing**:
- [ ] Check MQTT Explorer for attributes topic
- [ ] Verify JSON payload is valid
- [ ] Check Home Assistant logs for parsing errors

## General Debugging Tips

### Serial Monitor Best Practices

- [ ] Set baud rate to 115200
- [ ] Enable timestamps (if available)
- [ ] Enable autoscroll
- [ ] Clear output before each test
- [ ] Save output to file for analysis

### Systematic Testing Approach

1. **Test TX node alone**:
   - [ ] Verify LoRa init succeeds
   - [ ] Verify display works
   - [ ] Verify PIR triggers wake
   - [ ] Verify transmission completes
   - [ ] Verify deep sleep is entered

2. **Test RX node alone**:
   - [ ] Verify WiFi connects
   - [ ] Verify MQTT connects
   - [ ] Verify LoRa init succeeds
   - [ ] Verify display works

3. **Test LoRa communication**:
   - [ ] Place nodes 1 meter apart
   - [ ] Trigger TX and verify RX receives
   - [ ] Check RSSI/SNR values
   - [ ] Increase distance gradually

4. **Test Home Assistant integration**:
   - [ ] Verify MQTT messages are published
   - [ ] Verify sensor appears in Home Assistant
   - [ ] Verify state changes when motion detected
   - [ ] Verify attributes are populated

### Common Error Codes

**MQTT Error Codes** (from Serial Monitor):
- `-4`: Connection timeout
- `-3`: Connection lost
- `-2`: Connect failed
- `-1`: Disconnected
- `0`: Connected
- `1`: Bad protocol
- `2`: Bad client ID
- `3`: Unavailable
- `4`: Bad credentials
- `5`: Unauthorized

**ESP32 Sleep Wake Reasons**:
- `ESP_SLEEP_WAKEUP_EXT0`: External GPIO (PIR sensor) - **Expected**
- `ESP_SLEEP_WAKEUP_TIMER`: Timer wakeup
- `ESP_SLEEP_WAKEUP_TOUCHPAD`: Touchpad wakeup
- `Default`: First boot or reset - **Expected on first boot**

### Measurement Tools

**Multimeter Checks**:
- [ ] Battery voltage: 3.0-4.2V (LiPo)
- [ ] 3.3V rail: 3.2-3.4V
- [ ] PIR output: 0V idle, 3.3V motion
- [ ] Sleep current: 10-20µA (requires µA range)

**Software Tools**:
- [ ] MQTT Explorer: Monitor all MQTT messages
- [ ] WiFi Analyzer: Check WiFi signal strength
- [ ] I2C Scanner: Find display address
- [ ] LoRa example sketches: Test LoRa hardware

## Getting Help

If you've worked through this checklist and still have issues:

1. **Gather information**:
   - [ ] Serial Monitor output from both nodes
   - [ ] Photos of wiring
   - [ ] MQTT Explorer screenshots
   - [ ] Home Assistant logs
   - [ ] Exact error messages

2. **Check documentation**:
   - [ ] README.md for overview
   - [ ] CONFIGURATION.md for detailed setup
   - [ ] ARCHITECTURE.md for system design

3. **Community resources**:
   - Home Assistant Community Forum
   - ESP32 Forum
   - Arduino Forum
   - Reddit: r/homeassistant, r/esp32

4. **Double-check basics**:
   - [ ] All connections are secure
   - [ ] All configuration values are correct
   - [ ] All libraries are installed
   - [ ] Code uploaded successfully to both nodes

## Quick Reference: Common Fixes

| Problem | Quick Fix |
|---------|-----------|
| LoRa init fails | Check antenna, verify pins, try different frequency |
| WiFi won't connect | Check SSID/password, ensure 2.4GHz, try mobile hotspot |
| MQTT won't connect | Verify broker IP, check credentials, test with MQTT Explorer |
| TX won't wake | Check PIR power, verify GPIO 33, test PIR separately |
| Battery drains fast | Reduce display timeout, verify deep sleep, check current |
| No packets received | Match LoRa settings, start close together, check Serial Monitor |
| HA sensor missing | Enable MQTT discovery, check topics, restart HA |
| Display blank | Check I2C address, verify pins, upload display example |

## Success Criteria

Your system is working correctly when:

- [ ] TX node wakes on PIR motion
- [ ] TX node displays status for 3-4 seconds
- [ ] TX node transmits LoRa packet
- [ ] TX node enters deep sleep
- [ ] RX node receives packet
- [ ] RX node displays packet info (RSSI, SNR, battery)
- [ ] RX node publishes to MQTT
- [ ] Home Assistant sensor changes to "on"
- [ ] Home Assistant sensor returns to "off" after timeout
- [ ] Attributes show RSSI, SNR, battery voltage
- [ ] Battery lasts multiple days/weeks

Once all criteria are met, your driveway sensor system is fully operational!
