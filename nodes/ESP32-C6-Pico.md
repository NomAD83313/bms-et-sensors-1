# ESP32-C6-Pico

Matter over Thread firmware for the BMS DOA `ESP32-C6-Pico` node.

## Hardware

- Target: `ESP32-C6`, `4 MB` flash
- Transport: Matter over Thread
- Commissioning: BLE
- Native USB: `USB JTAG/serial`
- RGB LED: onboard `WS2812` on `GPIO 8`
- Button: `BOOT` on `GPIO 9`
- Additional board logic: `TCA9554PWR` GPIO expander

## Important Board Constraint

This board reserves:

- `GPIO22` as `I2C SDA`
- `GPIO23` as `I2C SCL`

These pins are for the onboard `TCA9554PWR` GPIO expander and should not be
reused for unrelated functions.

Practical meaning:

- native `ESP32-C6` GPIO and ADC are still available
- `EXIO` via `TCA9554` is additional digital I/O, not a replacement for native GPIO
- the current firmware initializes the onboard `TCA9554PWR` and keeps all `EXIO` lines in safe input mode by default

## Device Model

- Endpoint `1`: `Temperature Sensor` using the ESP32-C6 internal temperature sensor
- Endpoint `2`: `Contact Sensor` using the `BOOT` button

## Matter Identity

- VendorID: `0xFFF1`
- VendorName: `BMS DOA`
- ProductID: `0x8003`
- ProductName: `ESP32-C6-Pico`
- SoftwareVersion: current git commit
- QR code: `MT:2980142C00Q90648G00`
- Manual pairing code: `33331712336`
- Setup passcode: `20202021`
- Discriminator: `3584 (0xE00)`
- Serial: runtime `BMS-C6P-<MAC6>` from base MAC

Current lab node:

- Serial: `BMS-C6P-53AC5C`
- Matter node id after 2026-05-05 UI commissioning: `6`
- Commissioned with Matter.js server via the external Realtek USB BLE adapter
  (`0bda:8771`)

## Thread Mode

This project starts as a powered `Minimal End Device` profile.

Why:

- it gives us an efficient end-device baseline
- it lets the board join Thread without assuming router duty
- it keeps room for a later `EXIO`-focused sensor/actuator profile

Important commissioning note:

- Use only the external standalone Realtek USB BLE adapter for Matter
  commissioning.
- Do not use the Raspberry Pi internal Cypress/Broadcom BLE adapter.
- Do not use the MediaTek `0e8d:7961` Wi-Fi/AP combo BLE adapter.
- Start Matter services through `./scripts/restart-matter-server.sh` so the
  Realtek HCI index is auto-detected and passed to Matter.js.

2026-05-05 verification:

- Built and flashed from `esp-matter-release-v1.5`.
- Runtime Thread mode: `MINIMAL END DEVICE`.
- Light sleep: disabled for commissioning stability.
- UI commissioning succeeded through Matter.js.
- Commissioned endpoints:
  - endpoint `1`: `TemperatureSensor`
  - endpoint `2`: `ContactSensor`

## Planned Expansion

Current baseline:

- `BOOT` button on `GPIO9`
- onboard RGB LED on `GPIO8`
- `GPIO22/23` reserved for the onboard `TCA9554PWR`
- `WS_TCA9554PWR` helper initialized during boot
- all `EXIO` lines start as inputs until we assign them a role

Follow-up work for this board:

- map selected `EXIO` lines into extra Matter inputs / outputs
- document which signals should stay on native GPIO and which belong on `EXIO`

## Pairing Persistence

Normal `flash` updates preserve NVS and do not require re-pairing. `erase-flash`,
factory reset, or NVS wipe require fresh commissioning.

## OTA Prototype

This board now uses the same OTA baseline as the other `4 MB` ESP32-C6 targets.

Current OTA layout:

| Partition | Offset | Size | Purpose |
| --- | --- | --- | --- |
| `nvs` | `0x9000` | `0x6000` | Matter pairing and runtime state |
| `otadata` | `0xf000` | `0x2000` | ESP-IDF OTA slot metadata |
| `phy_init` | `0x11000` | `0x1000` | RF calibration data |
| `ota_0` | `0x20000` | `0x1F0000` | First app slot |
| `ota_1` | `0x210000` | `0x1F0000` | Second app slot |

Build the OTA image with a clean build-local sdkconfig:

```bash
cd esp32c6Pico/matter-node
source /home/ets/.espressif/tools/activate_idf_v5.4.1.sh
/home/ets/.espressif/tools/python/v5.4.1/venv/bin/python \
  /home/ets/.espressif/v5.4.1/esp-idf/tools/idf.py \
  -B build-ota \
  -DSDKCONFIG=$PWD/build-ota/sdkconfig \
  build
```

For a real OTA transfer test, build a second image with a higher
`SoftwareVersion` than the firmware already running on the device:

```bash
/home/ets/.espressif/tools/python/v5.4.1/venv/bin/python \
  /home/ets/.espressif/v5.4.1/esp-idf/tools/idf.py \
  -B build-ota-next \
  -DSDKCONFIG=$PWD/build-ota-next/sdkconfig \
  -DMATTER_NODE_SOFTWARE_VERSION_U32=<NEXT_HEX_VERSION> \
  -DMATTER_NODE_FIRMWARE_VERSION=<NEXT_VERSION_STRING> \
  build
```

Expected outputs:

- `build-ota/esp32c6_pico_matter_node.bin`
- `build-ota/esp32c6_pico_matter_node-ota.bin`
- `build-ota-next/*.local-update.json` for local Matter Server OTA tests

Serial-flash the first OTA-layout image without erasing flash:

```bash
/home/ets/.espressif/tools/python/v5.4.1/venv/bin/python \
  /home/ets/.espressif/v5.4.1/esp-idf/tools/idf.py \
  -B build-ota -p /dev/ttyACM0 flash
```

Do not use `erase-flash` for migration testing. NVS remains at the same offset,
so this migration is intended to preserve existing pairing data.

## Important Files

- `esp32c6Pico/matter-node/main/main.cpp`
- `esp32c6Pico/matter-node/sdkconfig.defaults`
- `esp32c6Pico/matter-node/CMakeLists.txt`
- `esp32c6Pico/matter-node/tools/generate_onboarding_card.py`
- `esp32c6Pico/matter-node/matter-node-card.png`
