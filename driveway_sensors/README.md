# Driveway Sensor System

A battery-efficient LoRa-based motion detection system with Home Assistant integration.

## Overview

This project implements a wireless driveway motion sensor using two ESP32 LoRa nodes:

- **TX Node (Transmitter)**: Battery-powered PIR motion sensor that sleeps until motion is detected, then wakes, displays status, transmits via LoRa, and returns to deep sleep for maximum battery life.

- **RX Node (Receiver)**: Mains-powered receiver that continuously monitors for LoRa packets, displays status on OLED screen, and publishes motion events to Home Assistant via MQTT.

## Key Features

### TX Node (Transmitter)
- ✅ **Ultra-low power consumption**: ~10-20µA in deep sleep
- ✅ **PIR wake-on-motion**: Wakes from deep sleep when motion detected
- ✅ **OLED status display**: Shows motion status, battery voltage, transmission count
- ✅ **Battery monitoring**: Tracks voltage and warns when low
- ✅ **Long battery life**: 6-12 months on 2000mAh LiPo (typical usage)
- ✅ **Automatic sleep**: Returns to deep sleep after transmission

### RX Node (Receiver)
- ✅ **Continuous operation**: Always listening for LoRa packets
- ✅ **WiFi connectivity**: Connects to home network
- ✅ **MQTT integration**: Publishes to Home Assistant
- ✅ **Auto-discovery**: Automatically creates Home Assistant entities
- ✅ **OLED display**: Shows WiFi/MQTT status, RSSI, SNR, battery info
- ✅ **Signal quality monitoring**: Displays RSSI and SNR for each packet

### Home Assistant Integration
- ✅ **Binary motion sensor**: Appears as motion detector in Home Assistant
- ✅ **Automatic discovery**: No manual configuration needed
- ✅ **Rich attributes**: RSSI, SNR, battery voltage, packet count
- ✅ **Availability tracking**: Shows online/offline status
- ✅ **Automation ready**: Use in automations, alerts, notifications

## Hardware Requirements

### TX Node (Transmitter)
- Heltec WiFi LoRa 32 V3 (or compatible ESP32 LoRa board)
- PIR motion sensor (HC-SR501 or similar)
- LiPo battery (2000mAh recommended)
- Jumper wires
- Weatherproof enclosure

### RX Node (Receiver)
- Heltec WiFi LoRa 32 V3 (or compatible ESP32 LoRa board)
- USB power supply or 5V adapter
- Enclosure (optional)

## Software Requirements

- Arduino IDE (1.8.19 or later) or PlatformIO
- ESP32 board support
- Required libraries:
  - LoRa by Sandeep Mistry
  - Adafruit GFX Library
  - Adafruit SSD1306
  - PubSubClient by Nick O'Leary
  - ArduinoJson by Benoit Blanchon (v6.x)

## Quick Start

1. **Install Arduino IDE and libraries** (see CONFIGURATION.md)
2. **Wire PIR sensor** to TX node GPIO 33
3. **Configure TX code**:
   - Set LoRa frequency for your region
   - Adjust display timeout if needed
4. **Configure RX code**:
   - Set WiFi SSID and password
   - Set MQTT broker IP address
   - Match LoRa frequency to TX
5. **Upload code** to both nodes
6. **Test system**:
   - Power on RX node (should connect to WiFi/MQTT)
   - Power on TX node with battery
   - Trigger PIR sensor
   - Check Home Assistant for motion entity

## File Structure

```
driveway_sensors/
├── README.md                      # This file - project overview
├── ARCHITECTURE.md                # System architecture and design
├── CONFIGURATION.md               # Detailed configuration guide
├── driveway_tx_transmitter.ino    # TX node code (transmitter)
└── driveway_rx_receiver.ino       # RX node code (receiver)
```

## Documentation

- **README.md** (this file): Project overview and quick start
- **ARCHITECTURE.md**: Detailed system architecture, power management, packet format, Home Assistant integration
- **CONFIGURATION.md**: Step-by-step configuration, troubleshooting, optimization tips

## Expected Battery Life

With a 2000mAh LiPo battery and typical usage (10 motion events per day):

- **Sleep current**: ~20µA
- **Active current**: ~120mA (during 4-second wake cycle)
- **Calculated battery life**: ~3 years (theoretical)
- **Practical battery life**: 6-12 months (accounting for self-discharge and temperature)

Battery life can be extended by:
- Reducing display timeout
- Using larger battery (3000-5000mAh)
- Lowering LoRa TX power if range allows
- Disabling display entirely (code modification)

## Range

Typical range depends on spreading factor and environment:

| Spreading Factor | Speed | Range (open field) | Range (urban) |
|------------------|-------|-------------------|---------------|
| SF7 | Fast | 1-2 km | 200-500 m |
| SF9 | Medium | 3-5 km | 500-1000 m |
| SF12 | Slow | 10+ km | 1-3 km |

Range can be improved by:
- Increasing spreading factor (slower but longer range)
- Using external antennas with higher gain
- Ensuring line of sight between nodes
- Positioning nodes higher up

## Home Assistant Example

Once configured, the sensor appears in Home Assistant as:

**Entity**: `binary_sensor.driveway_motion`

**Attributes**:
```yaml
rssi: -45
snr: 9.5
battery: 3.87
packet_count: 142
node_id: "driveway_tx"
uptime: 86400
```

**Example Automation**:
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

## Troubleshooting

### Common Issues

**TX Node**:
- "Starting LoRa failed!" → Check wiring and pin definitions
- Won't wake from sleep → Verify PIR connected to GPIO 33
- Battery drains quickly → Reduce display timeout, check sleep current

**RX Node**:
- WiFi won't connect → Check SSID/password, ensure 2.4GHz network
- MQTT won't connect → Verify broker IP, check authentication
- Not receiving packets → Verify LoRa settings match TX node

**Home Assistant**:
- Sensor doesn't appear → Check MQTT discovery is enabled
- Shows "unavailable" → Verify RX node is connected to MQTT

See **CONFIGURATION.md** for detailed troubleshooting steps.

## Advanced Features

### Multiple TX Nodes

The system supports multiple TX nodes (e.g., front driveway, back gate):

1. Change `NODE_ID` in each TX node code
2. RX node automatically handles multiple transmitters
3. Each appears as separate entity in Home Assistant

### Battery Voltage Monitoring

Build a simple voltage divider circuit to monitor battery voltage:

- Battery+ → 100kΩ → GPIO 1 → 100kΩ → GND
- Calibrate `BATTERY_DIVIDER` constant in code
- Voltage appears in Home Assistant attributes
- Create automation for low battery alerts

### Custom MQTT Topics

Modify MQTT topic definitions in RX code to use custom topics for integration with other systems.

## Technical Specifications

### LoRa Configuration
- **Frequency**: 915MHz (US) / 868MHz (EU) / 433MHz (Asia)
- **Bandwidth**: 125kHz
- **Spreading Factor**: 7-12 (configurable)
- **Coding Rate**: 4/5
- **TX Power**: Up to 20dBm
- **Sync Word**: 0x12 (private network)

### Power Consumption
- **TX Deep Sleep**: 10-20µA
- **TX Active**: 120mA (peak during transmission)
- **RX Idle**: 80-100mA
- **RX Receiving**: 120-150mA

### Packet Format
```json
{
  "type": "motion",
  "node": "driveway_tx",
  "boot": 5,
  "count": 142,
  "battery": 3.87,
  "millis": 3456
}
```

## Future Enhancements

Potential improvements for future versions:

1. **Bidirectional communication**: TX waits for ACK from RX
2. **OTA updates**: Remote firmware updates via WiFi
3. **Additional sensors**: Temperature, light level, humidity
4. **Mesh networking**: Multiple RX nodes for extended range
5. **Solar charging**: Solar panel + charge controller for unlimited runtime
6. **Camera trigger**: Integrate with IP camera for motion-triggered recording

## Credits

This project uses the following open-source libraries:
- [LoRa](https://github.com/sandeepmistry/arduino-LoRa) by Sandeep Mistry
- [Adafruit GFX](https://github.com/adafruit/Adafruit-GFX-Library) by Adafruit
- [Adafruit SSD1306](https://github.com/adafruit/Adafruit_SSD1306) by Adafruit
- [PubSubClient](https://github.com/knolleary/pubsubclient) by Nick O'Leary
- [ArduinoJson](https://github.com/bblanchon/ArduinoJson) by Benoit Blanchon

## License

This project is provided as-is for personal and educational use. Feel free to modify and adapt for your needs.

## Support

For detailed configuration instructions, see **CONFIGURATION.md**.

For system architecture and design details, see **ARCHITECTURE.md**.

For issues and questions:
- Check the troubleshooting section in CONFIGURATION.md
- Review Home Assistant MQTT integration documentation
- Consult ESP32 and LoRa library documentation

## Version History

- **v1.0** (2026-01-25): Initial release
  - TX node with PIR wake and deep sleep
  - RX node with WiFi/MQTT/Home Assistant integration
  - OLED display on both nodes
  - Battery monitoring
  - Auto-discovery for Home Assistant
