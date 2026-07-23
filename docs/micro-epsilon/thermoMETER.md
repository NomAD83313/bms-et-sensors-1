# Micro‑Epsilon thermoMETER CT — Technical Summary for Copilot Coding Agent

This document summarizes all essential technical information required to work with
**Micro‑Epsilon thermoMETER CT** sensors under Linux using USB/RS485, ASCII protocol,
and optional Modbus.  
Prepared for integration with automation, robotics, embedded systems, and Copilot Coding Agent workflows.

---

# 1. Device Architecture

## 1.1 thermoMETER CT sensor
- Infrared temperature sensor (pyrometer)
- Outputs a single temperature value
- Communicates via **RS485** internally
- Supports ASCII protocol (all models)
- Some models support **Modbus RTU** or **Modbus TCP**

## 1.2 USB Interface
When connected via USB, the device appears as:

Infrared Online Sensor Adapter (DR 6.7.6)

This is **not** the sensor itself — it is a **USB → RS485 adapter**.

On Linux the device appears as:

/dev/ttyMICROEPS

Baudrate: 115200 (may vary) Data bits: 8 Parity: None Stop bits: 1 Flow control: None Terminator: CR LF ("\r\n")

---

# 3. ASCII Protocol

All commands follow:

<COMMAND>\r\n

Responses are ASCII strings.

## 3.1 Identification
*IDN?        → returns model, firmware, serial number PING         → PONG

## 3.2 Measurement
MEAS?        → current temperature MEASALL?     → temperature + status MAX?         → max temperature MIN?         → min temperature MAXRST       → reset max MINRST       → reset min

## 3.3 Emissivity
EMIS?        → read emissivity EMIS <val>   → set emissivity (0.10 … 1.00)

## 3.4 Averaging / Filters
AVG?         → read averaging time (ms) AVG <ms>     → set averaging time
FILT?        → read digital filter level FILT <0-3>   → set filter level

## 3.5 Ranges
RANGE?       → read measurement range RANGE <n>    → set range (if supported)

## 3.6 Baudrate
BAUD?        → read baudrate BAUD <rate>  → set baudrate (9600–115200)

## 3.7 System
RESET        → reboot device SAVE         → save settings to EEPROM LOAD         → load settings from EEPROM

---

# 4. Modbus Support

Not all CT models support Modbus.

## 4.1 Check Modbus availability
MODBUS?

Possible responses:
- `ERR` → Modbus not supported
- `0`   → supported but disabled
- `1`   → Modbus RTU enabled
- `2`   → Modbus TCP enabled (rare)

## 4.2 Enable Modbus RTU
MODBUS 1

5.2 Python Example (set emissivity)
ser.write(b"EMIS 0.95\r\n")
print(ser.readline().decode().strip())

6. Optical Accessories (CF Lenses)
Example: CT‑CF22‑C3
• 	This is not a sensor
• 	It is a close‑focus optical lens
• 	It reduces spot size for small‑object measurement
• 	It does not appear in software or SDK lists
• 	It does not affect communication protocols

7. Notes for Developers
• 	thermoMETER CT does not appear in MEDAQLib’s “supported sensors” list
because it uses generic ASCII RS485.
• 	MEDAQLib can still be used, but only as a generic ASCII device.
• 	USB interface is always a serial port, not a native USB protocol.
• 	All configuration can be done via ASCII commands.

8. Recommended Workflow for Linux
1. 	Identify device:
ls /dev/ttyUSB*
2. 	Open serial port (115200 baud)
3. 	Test communication:
*IDN?
4. 	Read temperature:
MEAS?
5. 	Configure emissivity, filters, averaging as needed
6. 	(Optional) Enable Modbus if supported

9. Useful Commands Cheat Sheet
| Purpose               | Command        |
|-----------------------|----------------|
| Read temperature      | `MEAS?`        |
| Read emissivity       | `EMIS?`        |
| Set emissivity        | `EMIS 0.95`    |
| Read averaging        | `AVG?`         |
| Set averaging         | `AVG 20`       |
| Read filter           | `FILT?`        |
| Set filter            | `FILT 2`       |
| Read baudrate         | `BAUD?`        |
| Set baudrate          | `BAUD 115200`  |
| Check Modbus          | `MODBUS?`      |
| Enable Modbus         | `MODBUS 1`     |
| Save settings         | `SAVE`         |
| Reset device          | `RESET`        |

10. Summary
thermoMETER CT is a serial ASCII device behind a USB‑RS485 adapter.
It does not appear in MEDAQLib’s supported sensor list, but works reliably via:
• 	ASCII protocol (recommended)
• 	Modbus RTU (if supported)
All configuration (emissivity, filters, averaging, baudrate) is done via ASCII commands.
This document provides everything needed to integrate the sensor into Linux applications, embedded systems, and automation workflows.

---
