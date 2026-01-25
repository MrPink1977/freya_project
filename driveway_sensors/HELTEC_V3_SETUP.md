# Heltec WiFi LoRa 32 V3 Setup Guide

## Your Board

You have the **Heltec WiFi LoRa 32 V3** board with:
- **ESP32-S3** microcontroller
- **SX1262** LoRa chip (NOT SX1276/SX1278)
- Built-in OLED display
- USB-C connector

**IMPORTANT**: This board requires a **different library** than regular ESP32 LoRa boards!

## Why the Original Code Didn't Work

The code I originally provided used the "LoRa by Sandeep Mistry" library, which only works with **SX1276/SX1278** chips. Your board has an **SX1262** chip, which requires the **RadioLib** library.

## Installation Steps

### Step 1: Install Required Library

1. Open Arduino IDE
2. Go to **Sketch → Include Library → Manage Libraries...**
3. Search for: **"Heltec ESP32 LoRa v3"**
4. Install **"Heltec ESP32 LoRa v3 Unofficial"** by ropg
5. This will automatically install RadioLib as a dependency

### Step 2: Add ESP32 Board Support (if not already done)

1. Go to **File → Preferences**
2. In "Additional Board Manager URLs", add:
   ```
   https://espressif.github.io/arduino-esp32/package_esp32_index.json
   ```
3. Click OK
4. Go to **Tools → Board → Boards Manager**
5. Search for "esp32"
6. Install **"esp32 by Espressif Systems"** (version 2.0.16 or later)

### Step 3: Select the Correct Board

1. Go to **Tools → Board → ESP32 Arduino**
2. Select **"Heltec WiFi LoRa 32(V3) / Wireless shell(V3)"**
3. **DO NOT** select any other Heltec board!

### Step 4: Configure Upload Settings

1. **Tools → Upload Speed**: 921600
2. **Tools → CPU Frequency**: 240MHz
3. **Tools → Flash Frequency**: 80MHz
4. **Tools → Flash Mode**: QIO
5. **Tools → Flash Size**: 8MB
6. **Tools → Partition Scheme**: Default 4MB with spiffs
7. **Tools → Port**: Select your COM port

### Step 5: Install Other Required Libraries

For the **RX node** only, you also need:

1. **PubSubClient** by Nick O'Leary
2. **ArduinoJson** by Benoit Blanchon (version 6.x, NOT 7.x)

Install these from the Library Manager.

## New Code Files

I've created new code files specifically for your Heltec V3 board:

1. **driveway_tx_heltec_v3.ino** - Transmitter code (battery-powered, PIR wake)
2. **driveway_rx_heltec_v3.ino** - Receiver code (WiFi/MQTT/Home Assistant)

## Configuration

### TX Node (Transmitter)

Edit `driveway_tx_heltec_v3.ino`:

```cpp
// Line 28: PIR sensor pin
#define PIR_PIN           33        // Change if using different GPIO

// Line 32: LoRa frequency
#define LORA_FREQUENCY    915.0     // 915.0 for US, 868.0 for EU, 433.0 for Asia

// Line 46: Device ID
#define DEVICE_ID         "TX01"    // Unique name for this sensor
```

### RX Node (Receiver)

Edit `driveway_rx_heltec_v3.ino`:

```cpp
// Lines 37-38: WiFi credentials
#define WIFI_SSID         "WarRoom1"           // Your WiFi name
#define WIFI_PASSWORD     "YourWiFiPassword"   // Your WiFi password

// Lines 41-44: MQTT settings
#define MQTT_SERVER       "192.168.0.40"       // Your computer's IP
#define MQTT_PORT         1883
#define MQTT_USER         ""                   // Empty if no authentication
#define MQTT_PASSWORD     ""                   // Empty if no authentication

// Line 50: LoRa frequency (MUST MATCH TX)
#define LORA_FREQUENCY    915.0
```

## Upload Process

### For TX Node:
1. Open `driveway_tx_heltec_v3.ino`
2. Configure settings (PIR pin, frequency, device ID)
3. Connect board via USB
4. Select correct board and port
5. Click Upload (→)
6. Open Serial Monitor (115200 baud) to verify

### For RX Node:
1. Open `driveway_rx_heltec_v3.ino`
2. Configure WiFi, MQTT, and LoRa settings
3. Connect board via USB
4. Select correct board and port
5. Click Upload (→)
6. Open Serial Monitor (115200 baud) to verify

## Expected Serial Output

### TX Node (Success):
```
========================================
Driveway Sensor TX Node - Heltec V3
========================================
Boot #1
Wake reason: 0
Battery: 4200 mV
Initializing LoRa...
LoRa initialized successfully!
Frequency: 915.0 MHz
Spreading Factor: 7
Bandwidth: 125.0 kHz
TX Power: 22 dBm

--- Sending Motion Packet ---
Transmission #1
Packet: {"device":"TX01","motion":true,"battery":4200,"count":1,"boot":1}
Transmission successful!
Data rate: 5468.75 bps
-----------------------------

Entering deep sleep...
========================================
```

### RX Node (Success):
```
========================================
Driveway Sensor RX Node - Heltec V3
========================================

Connecting to WiFi: WarRoom1
WiFi connected!
IP address: 192.168.0.53
Signal strength (RSSI): -44 dBm

Connecting to MQTT broker: 192.168.0.40
Attempting MQTT connection...MQTT connected!
Publishing Home Assistant discovery configuration...
Discovery configuration published successfully!
Published motion state: OFF
Initializing LoRa...
LoRa initialized successfully!
Frequency: 915.0 MHz
Spreading Factor: 7
Bandwidth: 125.0 kHz
Listening for packets...

System ready!
========================================
```

## Troubleshooting

### "LoRa initialization failed"
- **Check antenna is connected** (REQUIRED!)
- Verify correct board selected
- Try power cycling the board
- Check frequency setting (915 for US, 868 for EU)

### "WiFi connection FAILED"
- Double-check SSID and password
- Ensure WiFi is 2.4GHz (ESP32 doesn't support 5GHz)
- Check WiFi signal strength

### "MQTT connection FAILED"
- Verify MQTT broker IP address
- Check broker is running (Docker container)
- Ensure port 1883 is accessible
- Try empty username/password if no authentication

### Compilation Errors
- Make sure you installed "Heltec ESP32 LoRa v3 Unofficial" library
- Verify RadioLib was auto-installed
- Check ArduinoJson is version 6.x (not 7.x)
- Ensure correct board is selected

## Key Differences from Original Code

1. **Library**: Uses `#include <heltec_unofficial.h>` instead of separate LoRa library
2. **Radio Object**: `radio` object is automatically created by the library
3. **Initialization**: Uses `heltec_setup()` and `heltec_loop()`
4. **LoRa Functions**: Uses RadioLib API (e.g., `radio.begin()`, `radio.transmit()`)
5. **Pin Definitions**: Handled automatically by the library

## Testing

1. **Upload TX code** to one board
2. **Upload RX code** to another board
3. **Power on RX** first (via USB)
4. **Power on TX** (via USB or battery)
5. **Trigger PIR** sensor on TX
6. **Watch Serial Monitor** on both boards
7. **Check Home Assistant** for new motion sensor

## Battery Operation (TX Node)

For battery-powered TX node:
1. Connect 3.7V LiPo battery to JST connector
2. Board will charge battery when USB connected
3. Disconnect USB for battery operation
4. Expected battery life: 6-12 months (2000mAh, 10 events/day)

## Support

If you still have issues:
1. Check Serial Monitor output on both boards
2. Verify antenna is connected (CRITICAL!)
3. Ensure both boards use same frequency
4. Test with boards close together first
5. Check MQTT broker is accessible

## References

- [Heltec V3 Unofficial Library](https://github.com/ropg/heltec_esp32_lora_v3)
- [RadioLib Documentation](https://jgromes.github.io/RadioLib/)
- [Heltec Official Docs](https://heltec.org/project/wifi-lora-32-v3/)
