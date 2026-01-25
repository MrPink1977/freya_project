# Driveway Sensor System - Configuration Guide

## Quick Start

This guide will help you configure and deploy your driveway sensor system with TX (transmitter) and RX (receiver) nodes.

## Prerequisites

### Software Requirements

1. **Arduino IDE** (version 1.8.19 or later) or **PlatformIO**
2. **ESP32 Board Support** installed in Arduino IDE
3. **Required Libraries**:
   - `LoRa` by Sandeep Mistry
   - `Adafruit GFX Library`
   - `Adafruit SSD1306`
   - `PubSubClient` by Nick O'Leary
   - `ArduinoJson` by Benoit Blanchon (version 6.x)

### Hardware Requirements

**TX Node (Transmitter)**:
- Heltec WiFi LoRa 32 V3 (or compatible ESP32 LoRa board)
- PIR motion sensor (HC-SR501 or similar)
- LiPo battery (2000mAh recommended)
- Jumper wires
- Weatherproof enclosure

**RX Node (Receiver)**:
- Heltec WiFi LoRa 32 V3 (or compatible ESP32 LoRa board)
- USB power supply or 5V adapter
- Enclosure (optional)

## Installation Steps

### Step 1: Install Arduino IDE and Libraries

1. Download and install Arduino IDE from [arduino.cc](https://www.arduino.cc/en/software)

2. Add ESP32 board support:
   - Open Arduino IDE
   - Go to **File → Preferences**
   - Add this URL to "Additional Board Manager URLs":
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Go to **Tools → Board → Boards Manager**
   - Search for "esp32" and install "esp32 by Espressif Systems"

3. Install required libraries:
   - Go to **Sketch → Include Library → Manage Libraries**
   - Search and install each library:
     - `LoRa` by Sandeep Mistry
     - `Adafruit GFX Library`
     - `Adafruit SSD1306`
     - `PubSubClient`
     - `ArduinoJson` (version 6.x)

### Step 2: Hardware Assembly

#### TX Node (Transmitter) Wiring

Connect the PIR sensor to the ESP32:

| PIR Sensor Pin | ESP32 Pin | Description |
|----------------|-----------|-------------|
| VCC            | 3.3V      | Power supply |
| GND            | GND       | Ground |
| OUT            | GPIO 33   | Signal output (RTC wake capable) |

**Important Notes**:
- GPIO 33 is an RTC-capable pin that can wake the ESP32 from deep sleep
- Ensure the PIR sensor can operate on 3.3V (most HC-SR501 sensors work with 3.3V-5V)
- Adjust PIR sensitivity and delay potentiometers as needed
- For battery monitoring, connect a voltage divider from battery to GPIO 1

#### RX Node (Receiver) Wiring

The RX node typically requires no external wiring if using a Heltec board with built-in LoRa and OLED. Simply connect it to power via USB.

### Step 3: Configure TX Node

1. Open `driveway_tx_transmitter.ino` in Arduino IDE

2. **Configure LoRa frequency** (line 37):
   ```cpp
   #define LORA_FREQUENCY    915E6      // 915MHz for US, 868MHz for EU
   ```
   - Use `915E6` for US/Canada/Australia
   - Use `868E6` for Europe
   - Use `433E6` for Asia (check local regulations)

3. **Adjust spreading factor** for range vs. speed (line 39):
   ```cpp
   #define LORA_SPREADING    7          // SF7 (faster) to SF9 (longer range)
   ```
   - SF7: Faster transmission, shorter range (~1-2km)
   - SF9: Slower transmission, longer range (~3-5km)
   - SF12: Maximum range (~10km) but very slow

4. **Configure display timeout** (line 59):
   ```cpp
   #define DISPLAY_TIMEOUT   4000       // Display on time (ms)
   ```
   - Shorter time = better battery life
   - Longer time = easier to see status

5. **Set node identification** (line 67):
   ```cpp
   #define NODE_ID           "driveway_tx"
   ```
   - Change if you have multiple TX nodes
   - Use descriptive names like "front_gate", "back_door", etc.

6. **Verify pin definitions** (lines 42-54):
   - Default pins are for Heltec WiFi LoRa 32 V3
   - If using a different board, update pin numbers accordingly

### Step 4: Configure RX Node

1. Open `driveway_rx_receiver.ino` in Arduino IDE

2. **Configure WiFi credentials** (lines 44-45):
   ```cpp
   #define WIFI_SSID         "YOUR_WIFI_SSID"
   #define WIFI_PASSWORD     "YOUR_WIFI_PASSWORD"
   ```
   - Replace with your actual WiFi network name and password

3. **Configure MQTT broker** (lines 49-52):
   ```cpp
   #define MQTT_SERVER       "192.168.1.100"  // Your MQTT broker IP
   #define MQTT_PORT         1883
   #define MQTT_USER         "mqtt_user"      // Leave empty if no auth
   #define MQTT_PASSWORD     "mqtt_pass"      // Leave empty if no auth
   ```
   - Set `MQTT_SERVER` to your Home Assistant IP address
   - Default MQTT port is 1883
   - If your MQTT broker doesn't require authentication, set:
     ```cpp
     #define MQTT_USER         ""
     #define MQTT_PASSWORD     ""
     ```

4. **Configure LoRa frequency** (must match TX):
   ```cpp
   #define LORA_FREQUENCY    915E6      // Must match TX frequency
   ```

5. **Configure spreading factor** (must match TX):
   ```cpp
   #define LORA_SPREADING    7          // Must match TX spreading factor
   ```

6. **Adjust motion timeout** (line 77):
   ```cpp
   #define MOTION_TIMEOUT    30         // Motion auto-off after 30s
   ```
   - This determines how long the motion state stays "ON" in Home Assistant
   - Adjust based on your automation needs

### Step 5: Upload Code

#### Upload to TX Node

1. Connect TX node to computer via USB
2. Select board: **Tools → Board → ESP32 Arduino → Heltec WiFi LoRa 32(V3)**
3. Select port: **Tools → Port → [Your COM port]**
4. Click **Upload** button
5. Wait for upload to complete
6. Open **Serial Monitor** (115200 baud) to verify operation

#### Upload to RX Node

1. Connect RX node to computer via USB
2. Select board and port (same as TX)
3. Click **Upload** button
4. Wait for upload to complete
5. Open **Serial Monitor** to verify WiFi and MQTT connections

### Step 6: Home Assistant Configuration

#### Option A: Automatic Discovery (Recommended)

The RX node automatically publishes MQTT discovery messages. Home Assistant should detect the sensor automatically if MQTT discovery is enabled.

1. In Home Assistant, go to **Settings → Devices & Services**
2. Look for "MQTT" integration
3. You should see "Driveway LoRa Sensor" appear automatically
4. Click on it to view the motion sensor entity

#### Option B: Manual Configuration

If auto-discovery doesn't work, add this to your `configuration.yaml`:

```yaml
mqtt:
  binary_sensor:
    - name: "Driveway Motion"
      state_topic: "homeassistant/binary_sensor/driveway/state"
      payload_on: "ON"
      payload_off: "OFF"
      device_class: motion
      off_delay: 30
      json_attributes_topic: "homeassistant/binary_sensor/driveway/attributes"
      availability_topic: "homeassistant/binary_sensor/driveway/availability"
      payload_available: "online"
      payload_not_available: "offline"
```

Then restart Home Assistant.

## Testing

### Test TX Node

1. Power on TX node with battery
2. Watch the OLED display - should show "Driveway TX" and "Initializing..."
3. Trigger PIR sensor by waving your hand in front of it
4. Display should show:
   - "MOTION" (large text)
   - Battery voltage
   - Boot count
   - Transmission count
5. After ~4 seconds, display should turn off (entering deep sleep)
6. Check Serial Monitor for detailed logs

### Test RX Node

1. Power on RX node
2. Display should show:
   - "Driveway RX" title
   - WiFi status: "WiFi: OK"
   - MQTT status: "MQTT: OK"
   - Motion status: "Idle"
3. When TX transmits, RX should display:
   - "MOTION!" (large text)
   - RSSI and SNR values
   - Battery voltage
   - Packet count
4. Check Serial Monitor for packet details

### Test Home Assistant Integration

1. Open Home Assistant
2. Go to **Developer Tools → States**
3. Search for `binary_sensor.driveway_motion`
4. Trigger TX node (wave at PIR)
5. Entity should change from "off" to "on"
6. After 30 seconds (or configured timeout), should return to "off"
7. Check attributes for RSSI, SNR, battery voltage

## Troubleshooting

### TX Node Issues

**Problem**: "Starting LoRa failed!" on display

**Solutions**:
- Verify LoRa module is properly connected
- Check pin definitions match your board
- Ensure correct frequency for your region
- Try different USB cable or power source
- Check for solder bridges on LoRa module

**Problem**: TX doesn't wake from sleep

**Solutions**:
- Verify PIR is connected to GPIO 33 (RTC-capable pin)
- Check PIR sensor has power (3.3V)
- Adjust PIR sensitivity potentiometer
- Test PIR separately with simple Arduino sketch
- Try different GPIO pin (must be RTC-capable: 0, 2, 4, 12-15, 25-27, 32-39)

**Problem**: Battery drains quickly

**Solutions**:
- Reduce `DISPLAY_TIMEOUT` value
- Lower `LORA_TX_POWER` if range is sufficient
- Check for current leaks (disconnect PIR and measure sleep current)
- Ensure ESP32 enters deep sleep (Serial Monitor should show "Entering deep sleep")
- Use quality LiPo battery with low self-discharge

### RX Node Issues

**Problem**: "Starting LoRa failed!"

**Solutions**:
- Same as TX node LoRa troubleshooting above

**Problem**: WiFi won't connect

**Solutions**:
- Double-check SSID and password (case-sensitive)
- Ensure WiFi is 2.4GHz (ESP32 doesn't support 5GHz)
- Move RX closer to WiFi router
- Check router settings (MAC filtering, etc.)
- Try different WiFi network

**Problem**: MQTT won't connect

**Solutions**:
- Verify MQTT broker IP address is correct
- Check MQTT port (default 1883)
- Verify MQTT username/password if authentication is enabled
- Ensure MQTT broker allows external connections
- Check Home Assistant MQTT integration is running
- Test MQTT with tool like MQTT Explorer

**Problem**: Not receiving packets from TX

**Solutions**:
- Verify both nodes use same frequency, bandwidth, spreading factor
- Check sync word matches on both nodes
- Ensure antennas are properly connected
- Test with nodes close together first (1-2 meters)
- Check Serial Monitor on both nodes for errors
- Verify TX is actually transmitting (check Serial Monitor)

### Home Assistant Issues

**Problem**: Sensor doesn't appear in Home Assistant

**Solutions**:
- Check MQTT integration is installed and configured
- Verify MQTT discovery is enabled in Home Assistant
- Check MQTT broker logs for incoming messages
- Use MQTT Explorer to verify messages are being published
- Manually add sensor to `configuration.yaml` (see Option B above)
- Restart Home Assistant

**Problem**: Sensor shows "unavailable"

**Solutions**:
- Check RX node is powered on and connected to WiFi/MQTT
- Verify availability topic is being published
- Check MQTT broker is running
- Restart RX node
- Check Home Assistant logs for errors

## Optimization Tips

### Extending Battery Life

1. **Reduce display timeout**: Lower `DISPLAY_TIMEOUT` to 2-3 seconds
2. **Optimize LoRa settings**: Use lower spreading factor (SF7) if range allows
3. **Reduce TX power**: Lower `LORA_TX_POWER` if signal is strong enough
4. **Disable display**: Comment out all display code if not needed
5. **Use larger battery**: 3000-5000mAh LiPo for longer runtime

### Improving Range

1. **Increase spreading factor**: Use SF9 or SF10 (slower but longer range)
2. **Increase TX power**: Set `LORA_TX_POWER` to 20 (maximum)
3. **Better antennas**: Use external antennas with higher gain
4. **Line of sight**: Position nodes with clear line of sight
5. **Antenna orientation**: Align antennas parallel to each other

### Reducing False Triggers

1. **Adjust PIR sensitivity**: Turn sensitivity potentiometer down
2. **Adjust PIR delay**: Set delay potentiometer to minimum
3. **Shield PIR**: Block unwanted detection areas with tape/cardboard
4. **Add software debounce**: Increase `DEBOUNCE_TIME` in TX code
5. **Position carefully**: Avoid pointing at trees, bushes, or moving objects

## Advanced Configuration

### Multiple TX Nodes

To add multiple TX sensors (e.g., front and back driveway):

1. **On each TX node**, change the `NODE_ID`:
   ```cpp
   #define NODE_ID           "front_driveway"  // or "back_driveway"
   ```

2. **On RX node**, the code already handles multiple nodes automatically

3. **In Home Assistant**, each node will appear as a separate entity

### Custom MQTT Topics

To use custom MQTT topics, modify these lines in RX code:

```cpp
#define MQTT_TOPIC_STATE       "your/custom/topic/state"
#define MQTT_TOPIC_ATTRIBUTES  "your/custom/topic/attributes"
#define MQTT_TOPIC_CONFIG      "your/custom/topic/config"
```

### Battery Voltage Monitoring

To enable accurate battery monitoring on TX node:

1. **Build voltage divider circuit**:
   - Battery+ → 100kΩ resistor → GPIO 1 → 100kΩ resistor → GND
   - This creates a 2:1 voltage divider

2. **Calibrate the divider ratio** in code:
   ```cpp
   #define BATTERY_DIVIDER   2.0        // Adjust based on actual resistor values
   ```

3. **Test and adjust**:
   - Measure actual battery voltage with multimeter
   - Compare to voltage reported in Serial Monitor
   - Adjust `BATTERY_DIVIDER` value until they match

### Low Battery Alerts

To get notifications when battery is low:

1. The TX node already checks battery and displays warning
2. The RX node publishes battery voltage to MQTT attributes
3. Create automation in Home Assistant:

```yaml
automation:
  - alias: "Driveway Sensor Low Battery Alert"
    trigger:
      - platform: numeric_state
        entity_id: binary_sensor.driveway_motion
        attribute: battery
        below: 3.3
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "Low Battery Alert"
          message: "Driveway sensor battery is low: {{ state_attr('binary_sensor.driveway_motion', 'battery') }}V"
```

## Pin Reference Tables

### Heltec WiFi LoRa 32 V3 Pinout

| Function | GPIO Pin | Notes |
|----------|----------|-------|
| LoRa SCK | 9 | SPI Clock |
| LoRa MISO | 11 | SPI MISO |
| LoRa MOSI | 10 | SPI MOSI |
| LoRa CS | 8 | Chip Select |
| LoRa RST | 12 | Reset |
| LoRa DIO0 | 14 | Interrupt |
| OLED SDA | 17 | I2C Data |
| OLED SCL | 18 | I2C Clock |
| OLED RST | 21 | Reset |
| Battery ADC | 1 | Analog input |
| PIR Signal | 33 | RTC wake capable |

### RTC-Capable GPIO Pins (for PIR wake)

Only these pins can wake ESP32 from deep sleep:

| GPIO | RTC GPIO | Notes |
|------|----------|-------|
| 0 | RTC_GPIO11 | Boot button on some boards |
| 2 | RTC_GPIO12 | Built-in LED on some boards |
| 4 | RTC_GPIO10 | Safe to use |
| 12 | RTC_GPIO15 | Used by LoRa RST |
| 13 | RTC_GPIO14 | Safe to use |
| 14 | RTC_GPIO16 | Used by LoRa DIO0 |
| 15 | RTC_GPIO13 | Safe to use |
| 25 | RTC_GPIO6 | Safe to use |
| 26 | RTC_GPIO7 | Safe to use |
| 27 | RTC_GPIO17 | Safe to use |
| 32 | RTC_GPIO9 | Safe to use |
| 33 | RTC_GPIO8 | **Recommended for PIR** |
| 34 | RTC_GPIO4 | Input only |
| 35 | RTC_GPIO5 | Input only |
| 36 | RTC_GPIO0 | Input only |
| 39 | RTC_GPIO3 | Input only |

## Support and Resources

### Documentation
- [ESP32 Deep Sleep Guide](https://randomnerdtutorials.com/esp32-deep-sleep-arduino-ide-wake-up-sources/)
- [LoRa Library Documentation](https://github.com/sandeepmistry/arduino-LoRa)
- [Home Assistant MQTT Discovery](https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery)

### Tools
- [MQTT Explorer](http://mqtt-explorer.com/) - Debug MQTT messages
- [Arduino IDE](https://www.arduino.cc/en/software) - Development environment
- [ESPTool](https://github.com/espressif/esptool) - Flash ESP32 firmware

### Community
- [Home Assistant Community](https://community.home-assistant.io/)
- [ESP32 Forum](https://www.esp32.com/)
- [Arduino Forum](https://forum.arduino.cc/)

## License

This code is provided as-is for personal and educational use. Feel free to modify and adapt for your needs.
