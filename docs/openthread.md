# OpenThread Border Router Notes

This document describes the OTBR side of the optional Matter/Thread stack used in this repository.

## Matter Server commissioning note

`matter-server` commissioning is only stable in this project environment with a dedicated external USB BLE adapter.

- Use the tested Realtek USB BLE dongle (`0bda:8771`, Bluetooth address `8C:88:2B:24:32:8F`) for commissioning.
- Do not use the Raspberry Pi internal Cypress BLE adapter or the MediaTek Wi-Fi/AP combo BLE adapter for commissioning.
- The MediaTek `0e8d:7961` adapter is the Wi-Fi/AP combo device and is explicitly unsuitable for Matter commissioning here.
- The Raspberry Pi internal Cypress/Broadcom Bluetooth is disabled at boot on project hosts; keep commissioning on the external Realtek dongle.
- Start or restart `matter-server` with `./scripts/restart-matter-server.sh`; raw `docker restart` preserves stale `BLUETOOTH_ADAPTER` values after HCI renumbering.

For a fresh or factory-reset Wi-Fi/Thread device, commission through BLE with the QR payload and do not pass `network_only`.
The `network_only` flag disables BLE discovery in `matter-server`; use it only when the device is already reachable on the IP network.

Correct BLE commissioning WebSocket command:

```json
{
  "message_id": "commission-qr-ble",
  "command": "commission_with_code",
  "args": {
    "code": "MT:..."
  }
}
```

Do not use this for a fresh Thread device:

```json
{
  "message_id": "commission-thread-wrong",
  "command": "commission_with_code",
  "args": {
    "code": "MT:...",
    "network_only": true
  }
}
```

## Scope

The OTBR service is optional and runs only under the Compose `thread` profile.

Data path:

```text
Thread node -> OpenThread RCP -> openthread-border-router -> matter-server -> matter-collector -> InfluxDB
```

Related docs:

- `docs/matter-thread-topology.md`
- `nodes/README.md`

## Runtime model

- Service name: `openthread-border-router`
- Compose profile: `thread`
- Network mode: `host`
- Required hardware: OpenThread RCP with Matter-over-Thread firmware, for example Sonoff USB RCP or SMLIGHT SLZB network RCP
- Runtime state: `runtime/openthread/` and `runtime/openthread/thread/`

Never commit OTBR runtime state.

## Environment variables

Defined in `.env.example`:

- `OTBR_IMAGE`
- `OTBR_RCP_DEVICE`
- `OTBR_RCP_TCP_ENDPOINT`
- `OTBR_RCP_BAUD`
- `OTBR_INFRA_IF`
- `OTBR_THREAD_IF`
- `OTBR_LOG_LEVEL`

Recommended defaults for the Raspberry Pi AP setup:

- `OTBR_INFRA_IF=<ap-interface>`
- `MATTER_PRIMARY_IF=<ap-interface>`
- Thread channel `20`

RCP endpoint examples:

```dotenv
# USB RCP
OTBR_RCP_DEVICE=/dev/serial/by-id/usb-ITEAD_SONOFF_Zigbee_3.0_USB_Dongle_Plus_V2_...-if00
OTBR_RCP_BAUD=460800

# SMLIGHT SLZB Wi-Fi/LAN RCP socket
OTBR_RCP_DEVICE=/dev/ttyOTBR
OTBR_RCP_TCP_ENDPOINT=10.42.0.2:6638
OTBR_RCP_BAUD=460800
```

For network RCPs, `scripts/restart-openthread.sh` starts a host-side `socat` bridge from
`OTBR_RCP_TCP_ENDPOINT` to `OTBR_RCP_DEVICE`. The OTBR container then sees the bridged
pseudo-tty through its `/dev` bind mount.

When `scripts/openthread-host-setup.sh --apply` is used with `OTBR_RCP_TCP_ENDPOINT`,
it also installs `bms-otbr-rcp-bridge.service`. The service waits for the RCP TCP
endpoint before exposing `/dev/ttyOTBR`, which prevents OTBR from starting on an
unconnected pseudo-tty after host reboot.

## Host preparation

Before starting OTBR, run the host prerequisite helper:

```bash
./scripts/openthread-host-setup.sh --check
```

To apply the required host changes:

```bash
./scripts/openthread-host-setup.sh --apply
```

This helper is intended to be idempotent.

Important Raspberry Pi requirement:

- the AP profile on the AP interface must use `ipv6.method link-local`

That is handled by `scripts/rpi-nm-ap.sh` in the normal RPi setup flow.

## Start and restart

Start OTBR:

```bash
./scripts/restart-openthread.sh
```

This script:

1. runs the host prerequisite check
2. starts `openthread-border-router`
3. verifies `otbr-agent`
4. retries agent restart or one container recreate if readiness is delayed

Start the Matter-side services afterwards:

```bash
./scripts/restart-matter-server.sh
```

BLE commissioning policy:

- Use the hardcoded Realtek USB BLE adapter only (`0bda:8771`, Bluetooth address `8C:88:2B:24:32:8F`).
- Internal BLE fallback is disabled in `restart-matter-server.sh`.
- MediaTek `0e8d:7961` is blocked by `restart-matter-server.sh` because commissioning failed repeatedly with this combo adapter.
- If Linux renumbers HCI devices, rerun `./scripts/restart-matter-server.sh`; the script resolves the current `hciN` from the hardcoded Realtek identity and recreates `matter-server`.

## First-time dataset initialization

Only for a fresh `runtime/openthread/` state:

```bash
docker exec openthread-border-router ot-ctl dataset init new
docker exec openthread-border-router ot-ctl dataset networkname BMS-Thread
docker exec openthread-border-router ot-ctl dataset channel 20
docker exec openthread-border-router ot-ctl dataset commit active
docker exec openthread-border-router ot-ctl ifconfig up
docker exec openthread-border-router ot-ctl thread start
```

Security note:

- never log, paste, or commit `ot-ctl dataset active -x`

It contains Thread network credentials.

## Useful checks

Container and service state:

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile thread ps
docker logs -f openthread-border-router
```

OTBR agent state:

```bash
docker exec openthread-border-router ot-ctl state
docker exec openthread-border-router service otbr-agent status
```

## Topology expectations

OTBR is one side of the topology model, but it is not the only source of truth.

The canonical `/thread-topology` snapshot is built by merging:

- Matter inventory from `python-matter-server`
- OTBR router/neighbor/meshdiag diagnostics
- ordered backend association rules

If OTBR reports only `rloc-only` children, the backend may still produce a fully associated topology tree when Matter-side parent evidence is unique. See `docs/matter-thread-topology.md`.

## Common pitfalls

- OTBR starts but `otbr-agent` does not answer yet.
  Use `./scripts/restart-openthread.sh` instead of a raw `docker compose up`.
- `matter-server` is up but Thread commissioning/discovery is broken.
  Check that the RPi AP still has `ipv6.method link-local`.
- A node is visible in OTBR diagnostics but missing from the console tree.
  Inspect `/matter/thread-topology` and compare warnings with Matter inventory.
- Dataset/state was wiped.
  Reinitialize the dataset and recommission nodes if needed.
