# Driveway Sensor System - Wiring Guide

## Overview

This guide provides detailed wiring instructions for connecting the PIR motion sensor to the TX node and optional battery monitoring circuit.

## TX Node (Transmitter) Wiring

### Basic PIR Sensor Connection

The PIR motion sensor requires only 3 wires to connect to the ESP32:

| PIR Sensor Pin | ESP32 Pin | Wire Color (typical) | Description |
|----------------|-----------|---------------------|-------------|
| VCC            | 3.3V      | Red                 | Power supply (3.3V) |
| GND            | GND       | Black               | Ground |
| OUT            | GPIO 33   | Yellow/White        | Signal output |

### Wiring Diagram (Text)

```
PIR Motion Sensor                    ESP32 (Heltec WiFi LoRa 32 V3)
┌─────────────┐                      ┌──────────────────────┐
│             │                      │                      │
│     VCC ────┼──────────────────────┼─→ 3.3V              │
│             │     (Red wire)       │                      │
│     GND ────┼──────────────────────┼─→ GND               │
│             │     (Black wire)     │                      │
│     OUT ────┼──────────────────────┼─→ GPIO 33 (RTC)     │
│             │     (Yellow wire)    │                      │
└─────────────┘                      │                      │
                                     │   ┌──────┐           │
                                     │   │ OLED │ (built-in)│
                                     │   └──────┘           │
                                     │                      │
                                     │   ┌──────┐           │
                                     │   │ LoRa │ (built-in)│
                                     │   └──────┘           │
                                     │                      │
                                     │   Battery Connector  │
                                     │   (JST 2-pin)        │
                                     └──────────────────────┘
```

### PIR Sensor Pinout

Most PIR sensors (HC-SR501, HC-SR505, AM312) have the same basic pinout:

**HC-SR501 (Large PIR)**:
```
    ┌─────────────────┐
    │  ┌───┐   ┌───┐  │
    │  │Adj│   │Adj│  │  Adj = Adjustment potentiometers
    │  └───┘   └───┘  │  Left: Sensitivity
    │                 │  Right: Delay time
    │   ┌─────────┐   │
    │   │  Dome   │   │
    │   └─────────┘   │
    │                 │
    │  VCC GND OUT    │  ← Pins (bottom)
    └─────────────────┘
```

**HC-SR505 / AM312 (Mini PIR)**:
```
    ┌───────────┐
    │  ┌─────┐  │
    │  │Dome │  │
    │  └─────┘  │
    │           │
    │ VCC       │
    │ OUT       │  ← Pins (side or bottom)
    │ GND       │
    └───────────┘
```

### PIR Sensor Settings

**HC-SR501 Potentiometer Adjustments**:

**Sensitivity (left potentiometer)**:
- Clockwise: More sensitive (detects farther)
- Counter-clockwise: Less sensitive (detects closer)
- Recommended: Start at middle position, adjust as needed

**Delay Time (right potentiometer)**:
- Clockwise: Longer output pulse (up to 300 seconds)
- Counter-clockwise: Shorter output pulse (down to 3 seconds)
- **Recommended: Fully counter-clockwise (minimum delay)**
- This ensures quick wake/transmit/sleep cycle

**Jumper Settings** (if present):
- **H (Repeatable Trigger)**: Output stays HIGH while motion detected
- **L (Single Trigger)**: Output goes HIGH once, then LOW after delay
- **Recommended: L (Single Trigger)** for battery efficiency

### Battery Connection

The Heltec WiFi LoRa 32 V3 has a built-in JST 2-pin connector for LiPo batteries:

```
LiPo Battery (3.7V)                  ESP32
┌─────────────┐                      ┌──────────────────┐
│             │                      │                  │
│    Red (+)──┼──────────────────────┼─→ BAT+ (JST)    │
│             │                      │                  │
│  Black (-)──┼──────────────────────┼─→ BAT- (JST)    │
│             │                      │                  │
└─────────────┘                      └──────────────────┘
```

**Important Battery Notes**:
- Use 3.7V LiPo battery (single cell)
- Recommended capacity: 2000-5000mAh
- Ensure battery has protection circuit (PCB)
- Connect with correct polarity (red to +, black to -)
- Charge battery before first use

### Optional: Battery Voltage Monitoring Circuit

To accurately monitor battery voltage, add a voltage divider circuit:

```
Battery +                                         ESP32
    │
    ├─────────────────────────────────────────→ BAT+ (JST)
    │
    ├───[ 100kΩ ]───┬───[ 100kΩ ]───┐
                    │                │
                    │                │
                    └────────────────┼─────→ GPIO 1 (ADC)
                                     │
                                     └─────→ GND
```

**Component List**:
- 2× 100kΩ resistors (1/4W, 1% tolerance recommended)
- Jumper wires
- Small breadboard or perfboard (optional)

**Why Voltage Divider?**:
- LiPo battery voltage ranges from 3.0V (empty) to 4.2V (full)
- ESP32 ADC maximum input is 3.3V
- Voltage divider reduces battery voltage by half (÷2)
- 4.2V battery → 2.1V at ADC (safe)

**Calibration**:
1. Measure actual battery voltage with multimeter
2. Compare to voltage reported in Serial Monitor
3. Adjust `BATTERY_DIVIDER` constant in code if needed

## RX Node (Receiver) Wiring

The RX node typically requires **no external wiring** if using a Heltec WiFi LoRa 32 V3:

- **LoRa module**: Built-in, no wiring needed
- **OLED display**: Built-in, no wiring needed
- **Power**: USB-C connector for 5V power supply

### Power Supply Options

**Option 1: USB Power Supply** (Recommended):
```
Wall Outlet → USB Power Adapter (5V 1A) → USB-C Cable → ESP32
```

**Option 2: USB Power Bank**:
```
Power Bank (5V) → USB-C Cable → ESP32
```

**Option 3: 5V Power Supply + Voltage Regulator**:
```
12V DC Supply → Buck Converter (12V→5V) → 5V/GND → ESP32 5V/GND pins
```

## Pin Usage Summary

### TX Node Pin Assignments

| Pin | Function | Used By | Notes |
|-----|----------|---------|-------|
| GPIO 1 | ADC | Battery Monitor | Optional voltage divider |
| GPIO 8 | SPI CS | LoRa | Built-in connection |
| GPIO 9 | SPI SCK | LoRa | Built-in connection |
| GPIO 10 | SPI MOSI | LoRa | Built-in connection |
| GPIO 11 | SPI MISO | LoRa | Built-in connection |
| GPIO 12 | Output | LoRa RST | Built-in connection |
| GPIO 14 | Input | LoRa DIO0 | Built-in connection |
| GPIO 17 | I2C SDA | OLED | Built-in connection |
| GPIO 18 | I2C SCL | OLED | Built-in connection |
| GPIO 21 | Output | OLED RST | Built-in connection |
| GPIO 33 | Input | PIR Sensor | **External connection required** |
| 3.3V | Power | PIR Sensor | Power supply |
| GND | Ground | PIR Sensor | Ground reference |

### RX Node Pin Assignments

| Pin | Function | Used By | Notes |
|-----|----------|---------|-------|
| GPIO 8 | SPI CS | LoRa | Built-in connection |
| GPIO 9 | SPI SCK | LoRa | Built-in connection |
| GPIO 10 | SPI MOSI | LoRa | Built-in connection |
| GPIO 11 | SPI MISO | LoRa | Built-in connection |
| GPIO 12 | Output | LoRa RST | Built-in connection |
| GPIO 14 | Input | LoRa DIO0 | Built-in connection |
| GPIO 17 | I2C SDA | OLED | Built-in connection |
| GPIO 18 | I2C SCL | OLED | Built-in connection |
| GPIO 21 | Output | OLED RST | Built-in connection |
| USB-C | Power | Board | 5V power input |

## Available GPIO Pins

If you want to add additional sensors or features, these GPIO pins are available:

### TX Node Available Pins

| GPIO | Type | Notes |
|------|------|-------|
| 2 | I/O | Built-in LED on some boards |
| 4 | I/O | RTC-capable (can wake from sleep) |
| 13 | I/O | RTC-capable |
| 15 | I/O | RTC-capable |
| 25 | I/O, DAC | RTC-capable, analog output |
| 26 | I/O, DAC | RTC-capable, analog output |
| 27 | I/O | RTC-capable |
| 32 | I/O, ADC | RTC-capable, analog input |
| 34 | Input, ADC | RTC-capable, input only |
| 35 | Input, ADC | RTC-capable, input only |
| 36 | Input, ADC | RTC-capable, input only |
| 39 | Input, ADC | RTC-capable, input only |

### RX Node Available Pins

Same as TX node, plus GPIO 33 (since no PIR sensor needed).

## Wiring Best Practices

### General Guidelines

1. **Use appropriate wire gauge**:
   - Power wires (VCC/GND): 22-24 AWG
   - Signal wires (OUT): 24-26 AWG

2. **Keep wires short**:
   - Minimize wire length to reduce noise
   - Maximum recommended length: 30cm (12 inches)

3. **Secure connections**:
   - Solder connections for permanent installation
   - Use heat shrink tubing to insulate
   - Use dupont connectors for temporary/testing

4. **Proper polarity**:
   - Double-check VCC and GND before powering on
   - Red wire = positive (+)
   - Black wire = negative (-)

5. **Strain relief**:
   - Secure wires to prevent pulling on connections
   - Use cable ties or hot glue
   - Leave small service loop

### Soldering Tips

If soldering connections:

1. **Prepare wires**:
   - Strip 3-5mm of insulation
   - Twist stranded wires tightly
   - Pre-tin wire ends with solder

2. **Soldering technique**:
   - Heat pad and wire together
   - Apply solder to joint (not iron tip)
   - Remove iron after solder flows
   - Let cool without moving

3. **Inspection**:
   - Solder joint should be shiny and smooth
   - No cold solder joints (dull, grainy appearance)
   - No solder bridges between adjacent pins

4. **Insulation**:
   - Cover exposed solder joints with heat shrink
   - Use electrical tape as backup
   - Ensure no shorts between connections

## Enclosure Considerations

### TX Node (Outdoor Installation)

**Weatherproofing Requirements**:
- IP65 or higher rated enclosure
- Gasket-sealed lid
- Cable glands for wire entry
- Ventilation (with filter) to prevent condensation

**PIR Sensor Mounting**:
- PIR dome must be exposed (not behind plastic)
- Use enclosure with PIR sensor window
- Or mount PIR on outside of enclosure
- Angle PIR downward 5-10° for driveway coverage

**Battery Placement**:
- Secure battery inside enclosure
- Use foam padding to prevent movement
- Keep battery away from hot components
- Ensure JST connector is accessible for charging

**Antenna Placement**:
- Mount antenna outside enclosure (best signal)
- Or use enclosure with RF-transparent window
- Keep antenna vertical for best range
- Use antenna extension cable if needed

### RX Node (Indoor Installation)

**Enclosure Options**:
- Simple plastic project box
- 3D printed custom enclosure
- Wall-mounted case
- Or no enclosure (if indoors)

**Ventilation**:
- Provide ventilation holes for cooling
- ESP32 generates some heat during operation
- Prevent overheating in enclosed spaces

**Display Visibility**:
- Position display window for easy viewing
- Use clear acrylic for display cover
- Angle enclosure for optimal viewing

## Testing Wiring

### Continuity Testing (Before Power-On)

Use multimeter in continuity mode:

1. **VCC to GND**: Should be open (no continuity)
2. **PIR VCC to ESP32 3.3V**: Should have continuity
3. **PIR GND to ESP32 GND**: Should have continuity
4. **PIR OUT to GPIO 33**: Should have continuity

### Voltage Testing (After Power-On)

Use multimeter in voltage mode:

1. **ESP32 3.3V to GND**: Should read 3.2-3.4V
2. **PIR VCC to GND**: Should read 3.2-3.4V
3. **PIR OUT to GND**: Should read 0V (idle) or 3.3V (motion)
4. **Battery voltage**: Should read 3.0-4.2V (LiPo)

### Functional Testing

1. **PIR Sensor**:
   - Wave hand in front of PIR
   - LED on PIR should blink (if present)
   - Measure OUT pin: should go HIGH (3.3V)

2. **ESP32 Wake**:
   - Trigger PIR sensor
   - ESP32 should wake from sleep
   - Display should turn on
   - Serial Monitor should show boot message

3. **LoRa Transmission**:
   - Trigger TX node
   - Check Serial Monitor for "Transmission complete"
   - RX node should receive packet
   - RX Serial Monitor should show packet details

## Common Wiring Mistakes

### Mistake 1: Wrong GPIO Pin

**Problem**: PIR connected to non-RTC GPIO pin

**Symptom**: ESP32 won't wake from deep sleep

**Solution**: Use GPIO 33 (or other RTC-capable pin)

### Mistake 2: Reversed Polarity

**Problem**: VCC and GND swapped

**Symptom**: PIR doesn't work, may damage sensor

**Solution**: Double-check red=VCC, black=GND

### Mistake 3: Loose Connection

**Problem**: Wire not fully inserted or soldered

**Symptom**: Intermittent operation, random resets

**Solution**: Secure all connections, use solder for permanent install

### Mistake 4: No Antenna

**Problem**: LoRa antenna not connected

**Symptom**: "Starting LoRa failed!" or very short range

**Solution**: Always connect antenna before powering on

### Mistake 5: Wrong Voltage

**Problem**: 5V applied to 3.3V pin

**Symptom**: Damaged ESP32 or PIR sensor

**Solution**: Verify voltage levels before connecting

## Troubleshooting Wiring Issues

### No Power to PIR Sensor

**Check**:
- Measure voltage between PIR VCC and GND
- Should read 3.2-3.4V
- If 0V, check wiring and ESP32 power

### PIR Output Always HIGH or LOW

**Check**:
- Measure PIR OUT voltage
- Should toggle between 0V and 3.3V
- If stuck, PIR may be damaged or misconfigured

### ESP32 Won't Wake from Sleep

**Check**:
- Verify PIR OUT connected to GPIO 33
- Measure PIR OUT voltage when triggered
- Check code has correct wake configuration

### Intermittent Operation

**Check**:
- Inspect all solder joints
- Wiggle wires to find loose connections
- Re-solder or re-seat connectors

## Wiring Checklist

Before powering on your system, verify:

- [ ] PIR VCC connected to ESP32 3.3V
- [ ] PIR GND connected to ESP32 GND
- [ ] PIR OUT connected to ESP32 GPIO 33
- [ ] Battery connected with correct polarity (if used)
- [ ] LoRa antenna connected to both nodes
- [ ] No short circuits between VCC and GND
- [ ] All connections are secure (soldered or firmly seated)
- [ ] Wires are properly insulated (no exposed conductors)
- [ ] Voltage divider circuit correct (if using battery monitoring)
- [ ] Enclosure provides adequate protection (if outdoor)

Once all items are checked, you're ready to power on and test!

## Additional Resources

### Datasheets
- [HC-SR501 PIR Sensor Datasheet](https://www.mpja.com/download/31227sc.pdf)
- [ESP32 Datasheet](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf)
- [Heltec WiFi LoRa 32 V3 Pinout](https://resource.heltec.cn/download/WiFi_LoRa32_V3/HTIT-WB32LA(F)_V3.png)

### Video Tutorials
- Search YouTube for "ESP32 PIR sensor wiring"
- Search YouTube for "HC-SR501 adjustment tutorial"
- Search YouTube for "ESP32 deep sleep PIR wake"

### Tools Needed
- Soldering iron (if permanent installation)
- Multimeter (for testing)
- Wire strippers
- Small screwdriver (for PIR adjustment)
- Heat shrink tubing or electrical tape
