# Driveway Sensor System Architecture

## Overview

This system consists of two ESP32-based nodes communicating via LoRa radio:
- **TX Node (Transmitter)**: Battery-powered PIR motion sensor at driveway
- **RX Node (Receiver)**: Mains-powered receiver connected to WiFi/MQTT/Home Assistant

## Hardware Requirements

### TX Node (Transmitter)
- ESP32 board (Heltec WiFi LoRa 32 V3 or similar)
- PIR motion sensor (HC-SR501 or similar)
- OLED display (typically built-in on Heltec boards)
- Battery power supply (LiPo recommended)
- LoRa module (915MHz for US, 868MHz for EU)

### RX Node (Receiver)
- ESP32 board (Heltec WiFi LoRa 32 V3 or similar)
- OLED display (typically built-in)
- LoRa module (matching TX frequency)
- Mains power supply

## System Architecture

### TX Node Operation Flow

1. **Deep Sleep State** (default, ultra-low power)
   - ESP32 in deep sleep mode
   - PIR sensor connected to RTC GPIO for wake-up
   - Current draw: ~10-20µA

2. **Wake on Motion**
   - PIR sensor triggers interrupt
   - ESP32 wakes from deep sleep
   - Display turns on showing status

3. **Transmit Sequence**
   - Initialize LoRa radio
   - Display "Motion Detected" message
   - Send motion detection packet via LoRa
   - Display "Packet Sent" confirmation
   - Wait for brief display timeout (3-5 seconds)

4. **Return to Sleep**
   - Turn off display
   - Deinitialize LoRa radio
   - Enter deep sleep with PIR wake enabled

### RX Node Operation Flow

1. **Continuous Operation**
   - Always powered on (mains powered)
   - WiFi connected to home network
   - MQTT client connected to Home Assistant
   - LoRa radio in receive mode

2. **Receive Sequence**
   - Monitor for incoming LoRa packets
   - Parse packet data (RSSI, SNR, message)
   - Display packet info on OLED screen
   - Publish to MQTT topic for Home Assistant

3. **MQTT Integration**
   - Topic: `homeassistant/binary_sensor/driveway/state`
   - Payload: `ON` (motion detected) or `OFF` (timeout)
   - Auto-discovery configuration for Home Assistant
   - Includes RSSI and SNR as attributes

4. **Display Updates**
   - Show last packet received time
   - Display RSSI and SNR values
   - Show WiFi and MQTT connection status
   - Auto-clear after timeout

## LoRa Configuration

### Radio Parameters
- **Frequency**: 915MHz (US) or 868MHz (EU)
- **Bandwidth**: 125kHz (good range/speed balance)
- **Spreading Factor**: 7-9 (SF7 for speed, SF9 for range)
- **Coding Rate**: 4/5
- **Sync Word**: 0x12 (private network)
- **TX Power**: 20dBm (maximum)

### Packet Format
```
{
  "type": "motion",
  "node": "driveway_tx",
  "timestamp": <millis>,
  "battery": <voltage>
}
```

## Power Management Strategy

### TX Node Battery Optimization

1. **Deep Sleep**: Primary power saving method
   - ESP32 deep sleep: ~10µA
   - Wake on external interrupt (PIR)
   - RTC memory preserves critical data

2. **Quick Wake/Transmit/Sleep Cycle**
   - Total wake time: 3-5 seconds
   - LoRa init: ~100ms
   - Transmit: ~50-200ms (depends on SF)
   - Display timeout: 3 seconds
   - Sleep entry: ~10ms

3. **Display Management**
   - Turn on only during transmission
   - Auto-off after 3-5 seconds
   - Reduces power consumption significantly

4. **Battery Monitoring**
   - Read battery voltage via ADC
   - Include in transmitted packet
   - Low battery warning on display
   - Home Assistant notification via MQTT

### Expected Battery Life

With a 2000mAh LiPo battery:
- Sleep current: 20µA
- Active current: 120mA (average during 4s wake)
- 10 motion events per day

**Calculation**:
- Sleep time per day: 86400s - (10 × 4s) = 86360s
- Sleep consumption: (86360/3600) × 0.02mA = 0.48mAh
- Active consumption: (40/3600) × 120mA = 1.33mAh
- Total per day: ~1.81mAh
- **Battery life: ~1100 days (3 years)**

In practice, expect 6-12 months due to battery self-discharge and temperature effects.

## Home Assistant Integration

### MQTT Auto-Discovery

The RX node publishes discovery messages to enable automatic device creation:

**Binary Sensor Configuration**:
```yaml
Topic: homeassistant/binary_sensor/driveway_motion/config
Payload:
{
  "name": "Driveway Motion",
  "device_class": "motion",
  "state_topic": "homeassistant/binary_sensor/driveway/state",
  "payload_on": "ON",
  "payload_off": "OFF",
  "off_delay": 30,
  "json_attributes_topic": "homeassistant/binary_sensor/driveway/attributes",
  "unique_id": "driveway_motion_sensor",
  "device": {
    "identifiers": ["driveway_lora_sensor"],
    "name": "Driveway LoRa Sensor",
    "model": "ESP32 LoRa",
    "manufacturer": "Custom"
  }
}
```

**Sensor Attributes**:
```json
{
  "rssi": -45,
  "snr": 9.5,
  "battery": 3.87,
  "last_seen": "2026-01-25T10:30:45"
}
```

### Automation Examples

**Driveway Alert**:
```yaml
automation:
  - alias: "Driveway Motion Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.driveway_motion
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          message: "Motion detected in driveway"
          title: "Driveway Alert"
```

**Low Battery Warning**:
```yaml
automation:
  - alias: "Driveway Sensor Low Battery"
    trigger:
      - platform: numeric_state
        entity_id: sensor.driveway_motion
        attribute: battery
        below: 3.3
    action:
      - service: notify.mobile_app
        data:
          message: "Driveway sensor battery low: {{ state_attr('sensor.driveway_motion', 'battery') }}V"
```

## Troubleshooting

### Common Issues

1. **"Starting LoRa failed!"**
   - Check SPI pin definitions match your board
   - Verify LoRa module is properly connected
   - Ensure correct frequency for your region
   - Check for pin conflicts with other peripherals

2. **TX not waking from sleep**
   - Verify PIR is connected to RTC-capable GPIO
   - Check PIR sensor power supply
   - Ensure PIR sensitivity is properly adjusted
   - Test with manual GPIO trigger

3. **RX not receiving packets**
   - Verify both nodes use same frequency/bandwidth/SF
   - Check sync word matches
   - Verify antenna connections
   - Test range (start close, then increase distance)

4. **MQTT not connecting**
   - Check WiFi credentials
   - Verify MQTT broker IP and port
   - Check MQTT username/password
   - Ensure broker allows external connections

5. **Display not working**
   - Verify I2C address (usually 0x3C)
   - Check SDA/SCL pin definitions
   - Ensure display library is installed
   - Test with simple display example first

## Pin Definitions

### Heltec WiFi LoRa 32 V3

**LoRa Module**:
- SCK: GPIO 9
- MISO: GPIO 11
- MOSI: GPIO 10
- CS: GPIO 8
- RST: GPIO 12
- DIO0: GPIO 14

**OLED Display**:
- SDA: GPIO 17
- SCL: GPIO 18
- RST: GPIO 21

**PIR Sensor (TX)**:
- Signal: GPIO 33 (RTC_GPIO4 - wake capable)

**Battery Monitoring**:
- ADC: GPIO 1 (with voltage divider)

## Future Enhancements

1. **Bidirectional Communication**
   - RX sends acknowledgment back to TX
   - TX displays ACK status before sleeping
   - Retry logic if no ACK received

2. **Multiple TX Nodes**
   - Each TX has unique ID
   - RX handles multiple sensors
   - Home Assistant creates separate entities

3. **Enhanced Data**
   - Temperature sensor on TX
   - Light level sensor
   - Packet counter for reliability tracking

4. **OTA Updates**
   - TX wakes periodically to check for updates
   - RX always available for OTA
   - Version tracking in MQTT attributes

5. **Mesh Network**
   - Multiple RX nodes for extended range
   - Packet forwarding between nodes
   - Automatic route selection
