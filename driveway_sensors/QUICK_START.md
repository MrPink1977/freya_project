# Driveway Sensor System - Quick Start Guide

Get your driveway sensor up and running in 30 minutes!

## What You Need

### Hardware
- 2× Heltec WiFi LoRa 32 V3 boards (or compatible ESP32 LoRa boards)
- 1× PIR motion sensor (HC-SR501 or similar)
- 1× LiPo battery (2000mAh+ recommended)
- 3× Jumper wires (for PIR connection)
- 2× LoRa antennas (usually included with boards)
- 1× USB cable (for programming)
- 1× USB power supply (for RX node)

### Software
- Arduino IDE installed on your computer
- USB cable to connect boards to computer

## Step 1: Install Arduino IDE (5 minutes)

1. Download Arduino IDE from [arduino.cc](https://www.arduino.cc/en/software)
2. Install and open Arduino IDE
3. Go to **File → Preferences**
4. Add this URL to "Additional Board Manager URLs":
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
5. Click OK

## Step 2: Install ESP32 Support (3 minutes)

1. Go to **Tools → Board → Boards Manager**
2. Search for "esp32"
3. Install "esp32 by Espressif Systems"
4. Wait for installation to complete

## Step 3: Install Libraries (5 minutes)

Go to **Sketch → Include Library → Manage Libraries** and install these:

1. Search "LoRa" → Install "LoRa by Sandeep Mistry"
2. Search "Adafruit GFX" → Install "Adafruit GFX Library"
3. Search "Adafruit SSD1306" → Install "Adafruit SSD1306"
4. Search "PubSubClient" → Install "PubSubClient by Nick O'Leary"
5. Search "ArduinoJson" → Install "ArduinoJson by Benoit Blanchon" (version 6.x)

## Step 4: Wire PIR Sensor to TX Node (2 minutes)

Connect 3 wires from PIR sensor to ESP32:

| PIR Pin | ESP32 Pin |
|---------|-----------|
| VCC     | 3.3V      |
| GND     | GND       |
| OUT     | GPIO 33   |

**Important**: Make sure connections are secure!

## Step 5: Configure and Upload TX Code (5 minutes)

1. Open `driveway_tx_transmitter.ino` in Arduino IDE

2. **Change LoRa frequency** (line 37) for your region:
   ```cpp
   #define LORA_FREQUENCY    915E6      // US: 915E6, EU: 868E6
   ```

3. **Select board**: Tools → Board → ESP32 Arduino → Heltec WiFi LoRa 32(V3)

4. **Select port**: Tools → Port → [Your COM port]

5. **Upload**: Click the Upload button (→)

6. **Verify**: Open Serial Monitor (115200 baud) - should see boot messages

## Step 6: Configure and Upload RX Code (5 minutes)

1. Open `driveway_rx_receiver.ino` in Arduino IDE

2. **Enter WiFi credentials** (lines 44-45):
   ```cpp
   #define WIFI_SSID         "YourWiFiName"
   #define WIFI_PASSWORD     "YourWiFiPassword"
   ```

3. **Enter MQTT broker IP** (line 49):
   ```cpp
   #define MQTT_SERVER       "192.168.1.100"  // Your Home Assistant IP
   ```

4. **Match LoRa frequency to TX** (line 59):
   ```cpp
   #define LORA_FREQUENCY    915E6      // Must match TX!
   ```

5. **Upload**: Same process as TX node

6. **Verify**: Serial Monitor should show WiFi and MQTT connection

## Step 7: Test the System (5 minutes)

### Test TX Node:
1. Connect battery to TX node
2. Wave hand in front of PIR sensor
3. Display should show "MOTION DETECTED"
4. After 4 seconds, display turns off (sleeping)

### Test RX Node:
1. Power RX node via USB
2. Display should show "WiFi: OK" and "MQTT: OK"
3. When TX transmits, RX should show "MOTION!"
4. Check RSSI and SNR values on display

### Test Home Assistant:
1. Open Home Assistant
2. Go to Settings → Devices & Services → MQTT
3. Look for "Driveway LoRa Sensor"
4. Trigger TX node - sensor should change to "on"

## Troubleshooting

### TX shows "Starting LoRa failed!"
- Check antenna is connected
- Verify LoRa frequency is correct for your region
- Try different USB cable or power source

### RX won't connect to WiFi
- Double-check SSID and password (case-sensitive)
- Ensure WiFi is 2.4GHz (not 5GHz)
- Move RX closer to router

### RX won't connect to MQTT
- Verify MQTT broker IP address
- Check Home Assistant MQTT integration is running
- Try empty username/password if no authentication:
  ```cpp
  #define MQTT_USER         ""
  #define MQTT_PASSWORD     ""
  ```

### RX not receiving packets
- Verify both nodes use same frequency
- Check both antennas are connected
- Start with nodes close together (1-2 meters)

### Sensor doesn't appear in Home Assistant
- Check MQTT integration is installed
- Verify RX is connected to MQTT (Serial Monitor)
- Restart Home Assistant

## What's Next?

### Optimize Battery Life
- Reduce display timeout in TX code (line 59)
- Use larger battery (3000-5000mAh)
- Lower TX power if range is sufficient

### Improve Range
- Increase spreading factor to 9 or 12
- Use external antennas
- Position nodes with line of sight

### Add Automations
Create automations in Home Assistant:

```yaml
automation:
  - alias: "Driveway Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.driveway_motion
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          message: "Motion in driveway!"
```

### Add More Sensors
- Change `NODE_ID` in TX code for each sensor
- Each will appear as separate entity in Home Assistant
- Examples: front gate, back door, garage

## Configuration Files

Your configuration at a glance:

**TX Node**:
- Frequency: 915MHz (US) or 868MHz (EU)
- Spreading Factor: 7 (default)
- PIR Pin: GPIO 33
- Display Timeout: 4 seconds

**RX Node**:
- WiFi SSID: [Your network]
- MQTT Server: [Your Home Assistant IP]
- Frequency: Must match TX
- Motion Timeout: 30 seconds

## Need More Help?

- **Detailed setup**: See CONFIGURATION.md
- **System design**: See ARCHITECTURE.md
- **Wiring help**: See WIRING.md
- **Problems**: See TROUBLESHOOTING_CHECKLIST.md

## Success Checklist

Your system is working when:

- [ ] TX wakes on PIR motion
- [ ] TX displays status and transmits
- [ ] TX enters deep sleep after 4 seconds
- [ ] RX receives packet and displays info
- [ ] RX publishes to MQTT
- [ ] Home Assistant sensor changes to "on"
- [ ] Battery lasts multiple days

## Important Settings Summary

### Must Match on Both Nodes:
- LoRa Frequency (915MHz or 868MHz)
- Spreading Factor (default: 7)
- Bandwidth (default: 125kHz)
- Sync Word (default: 0x12)

### Must Configure on RX:
- WiFi SSID
- WiFi Password
- MQTT Server IP
- MQTT Username/Password (if required)

### Optional Adjustments:
- Display timeout (TX)
- Motion timeout (RX)
- TX power (both)
- Node ID (TX)

## Common Mistakes to Avoid

1. **Wrong frequency**: US uses 915MHz, EU uses 868MHz
2. **No antenna**: Always connect antenna before powering on
3. **Wrong WiFi band**: ESP32 only supports 2.4GHz (not 5GHz)
4. **Mismatched LoRa settings**: TX and RX must use same frequency/SF
5. **Wrong GPIO**: PIR must connect to GPIO 33 (RTC-capable)

## Tips for Best Results

1. **Start close**: Test with nodes 1-2 meters apart first
2. **Check Serial Monitor**: Always monitor for errors and status
3. **Adjust PIR**: Turn sensitivity and delay potentiometers
4. **Secure wiring**: Solder connections for permanent installation
5. **Weatherproof TX**: Use IP65+ enclosure for outdoor use

## Expected Performance

**Battery Life** (2000mAh LiPo, 10 events/day):
- Theoretical: 3+ years
- Practical: 6-12 months

**Range** (SF7, open field):
- Good signal: 1-2 km
- Urban environment: 200-500 m

**Latency**:
- PIR trigger to HA update: <2 seconds
- Wake/transmit/sleep cycle: 4 seconds

## You're Done!

Congratulations! Your driveway sensor system is now operational. The TX node will sleep until motion is detected, then wake, display status, transmit via LoRa, and return to sleep. The RX node continuously monitors for packets and publishes to Home Assistant.

Enjoy your new motion detection system!

---

**Questions?** Check the other documentation files for detailed information.

**Problems?** See TROUBLESHOOTING_CHECKLIST.md for systematic debugging.

**Want to learn more?** See ARCHITECTURE.md for system design details.
