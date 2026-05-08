# CLAUDE.md — BMS ET Sensors Stack
User wants answers in Russian. All code and comments must be in English.
## Project overview

Docker-based sensor data acquisition and visualization stack for environmental monitoring. Runs on Linux (Raspberry Pi primary target). Manages multiple hardware integrations via containerized Python services backed by InfluxDB and Grafana.

**Custom app services (Python/Flask, locally built):**
- `mscl-collector` — MicroStrain MSCL wireless node data acquisition + web API (Flask)
- `redlab-collector` — MCC RedLab thermocouple collector (Flask)
- `almemo-collector` — ALMEMO serial device integration (Flask)
- `pyrometer-collector` — thermoMETER CT and Optris serial integration (Flask)
- `graf-lite` — lightweight Python dashboard for low-resource hosts
- `ap-control` — Raspberry Pi access point operator UI for AP state and connected clients
- `service-controller` — internal service control + recovery API (MSCL serial guard, RedLab USB presence, ALMEMO USB presence)

**Third-party services (pulled from Docker Hub):**
- `influxdb` — time-series storage backend
- `grafana` — dashboards
- `dashboard` — nginx + simple-dash start page

**Optional profile-gated services (Thread / Matter):**
- `openthread-border-router` — OpenThread Border Router; profile `thread`; OpenThread RCP via USB serial or network socket
- `matter-server` — Home Assistant python-matter-server; profile `matter`; host networking
- `matter-collector` — Matter collector; profile `matter`; websocket consumer that writes normalized sensor events to InfluxDB

## Key commands

```bash
# Full local rebuild + restart (all custom app services)
./scripts/restart-local.sh

# Build and restart individual services
./scripts/build-local-mscl.sh
./scripts/build-local-redlab.sh
./scripts/build-local-graf-app.sh
./scripts/build-local-ap-ui.sh
./scripts/build-local-almemo.sh
./scripts/build-local-svcctl.sh
./scripts/build-local-matter-app.sh
./scripts/build-local-all.sh

# Fast MSCL restart (code-only change, no rebuild needed)
./scripts/restart-mscl-dev.sh

# Logs
./scripts/logs.sh              # all services
./scripts/logs.sh mscl-collector     # single service

# Tests
python -m unittest discover -s tests -q

# arm64 Docker Hub push (run on native arm64 host)
./scripts/build-push-arm64.sh

# Native x64 local build (no cross-compilation)
./scripts/build-local-x64-all.sh

# RPi setup
./scripts/rpi-setup.sh         # full build on RPi

# Cleanup
./scripts/clean-docker.sh                    # project-scoped stack cleanup
DRY_RUN=1 ./scripts/cleanup-dockerhub-tags.sh  # Docker Hub tag pruning
```

## Development workflow

### MSCL fast iteration
`mscl-collector` bind-mounts `./app/mscl:/app` via `docker-compose.override.yml`. Flask reloader is intentionally disabled. For code/template changes (`*.py`, `*.js`, `*.html`), use `restart-mscl-dev.sh` — no rebuild required. Rebuild (`build-local-mscl.sh`) only when `Dockerfile.mscl`, `requirements.txt`, or base image changes.

### Compose invocation
Always use both files:
```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d
```
Scripts handle this internally.

### Environment
Bootstrap from `.env.example`:
```bash
cp .env.example .env
```
Edit secrets and hardware paths (`MSCL_PORT`, `INFLUX_TOKEN`, etc.).

## Architecture notes

### Service control & recovery (`service-controller`)
- Monitors MSCL serial port stability; starts `mscl-collector` only after the port is present and stable.
- Detects MCC USB-TC by USB vendor/product ID; starts `redlab-collector` only after USB presence is confirmed.
- Detects ALMEMO USB adapter by vendor/product ID; starts `almemo-collector` only after USB presence is confirmed.

### ALMEMO integration status
- Since `v4.1.0`, the `Sensor Info` button uses a fast overview path based on `f2 P00` plus `P32`, instead of polling peaks and timestamps every time.
- Since `v4.0.4`, multi-step ALMEMO UI actions are batched on the server through `/api/command-sequence` instead of issuing many independent `/api/command` calls.
- The serial layer now explicitly sends `XON` after input-buffer resets and after re-arming the command channel when leaving streaming mode.
- Field checks on 2026-04-19 did not reproduce ALMEMO cable/device dropouts during common UI flows, but latency under active live streaming still needs follow-up optimization.
- After rebuilding `almemo-collector`, hard-refresh the browser to avoid testing with stale cached JavaScript.

### InfluxDB source tags
Shared tags used by both `mscl-collector` and `graf-lite`:
- `mscl_sensors`
- `mscl_config_stream`
- `mscl_node_export`

### Matter over Thread (OpenThread Border Router + Matter Server)

Optional overlay for commercial Matter-over-Thread sensor collection. Both services use `network_mode: host` and Compose profiles — the default stack works without Thread hardware.

**Data path:**
```
Matter/Thread sensors → Thread mesh → OpenThread RCP → openthread-border-router
  → matter-server → matter-collector → InfluxDB → Grafana
```

**Key env vars** (set in `.env`, defaults in `.env.example`):
- `OTBR_RCP_DEVICE` — RCP serial device path; use `/dev/serial/by-id/…` for USB or `/dev/ttyOTBR` with `OTBR_RCP_TCP_ENDPOINT` for SMLIGHT serial-over-IP
- `OTBR_RCP_TCP_ENDPOINT` — optional network RCP endpoint, for example `10.42.0.2:6638`; `restart-openthread.sh` bridges it to `OTBR_RCP_DEVICE` with host-side `socat`
- `OTBR_RCP_BAUD` — must match RCP firmware; tested value: `460800`
- `OTBR_INFRA_IF` / `MATTER_PRIMARY_IF` — use `wlan1` when RPi AP is the Matter/Thread infra link
- `MATTER_SERVER_IMAGE` — default `ghcr.io/matter-js/python-matter-server@sha256:6827e352011e2d8c2bde771e446fcf72acc49150ef66bad978816bac1762aad3` (pinned digest)
- `MATTER_BLE_USB_VID` / `MATTER_BLE_USB_PID` — external BLE adapter IDs used by `scripts/restart-matter-server.sh` auto-detection (default `0bda:8771`)
- Matter commissioning policy: use the external Realtek `0bda:8771` dongle only; Raspberry Pi internal Cypress BLE is disabled at boot and MediaTek `0e8d:7961` is unsuitable for commissioning.

**Runtime state** (never commit):
- `runtime/openthread/` — OTBR network state
- `runtime/matter-server/` — fabric/controller state and device credentials

**Host preparation:**
```bash
./scripts/openthread-host-setup.sh --check   # read-only prereq check
./scripts/openthread-host-setup.sh --apply   # enable IPv6 forwarding, create runtime dir
```
Apply writes `/etc/sysctl.d/99-bms-openthread.conf` for persistence across reboots.
RPi AP must have `ipv6.method link-local` — set by `scripts/rpi-nm-ap.sh`.

**Start services:**
```bash
./scripts/restart-openthread.sh     # runs --check, then starts openthread-border-router
./scripts/restart-matter-server.sh  # starts matter-server + matter-collector
```

**First-time Thread dataset init** (fresh `runtime/openthread/` only):
```bash
docker exec openthread-border-router ot-ctl dataset init new
docker exec openthread-border-router ot-ctl dataset networkname BMS-Thread
docker exec openthread-border-router ot-ctl dataset channel 20
docker exec openthread-border-router ot-ctl dataset commit active
docker exec openthread-border-router ot-ctl ifconfig up
docker exec openthread-border-router ot-ctl thread start
```
Thread channel 20 avoids overlap with the RPi AP on Wi-Fi channel 4.
**Never log or commit** `ot-ctl dataset active -x` output — it contains Thread network credentials.

`matter-collector` collector runs under the same `matter` profile and subscribes to Matter Server websocket events.

### Image builds
Docker Hub publishing is `arm64`-only and must run on a native `arm64` host. Local `x64` builds are native-only via `build-local-x64-all.sh`, without cross-compilation. MSCL package downloads remain architecture-specific and SHA256-verified in `Dockerfile.mscl`.

## File and config conventions

### Install-time vs. runtime files
- **Tracked in Git:** install-time templates only (`.env.example`)
- **Local only, never committed:** runtime state generated by containers (`.env`, `runtime/`)

Checklist for any new service or config path:
1. Decide install-time vs. runtime at the moment of adding the mount in `docker-compose.yml`.
2. Add the runtime path to `.gitignore` immediately.
3. If install-time: provide a `.example` template and create from it in setup/restart scripts.

### Legacy env variables
Several env vars are now hard-coded inside the stack. **Do not re-add** them to `.env` unless the source code changes. See `README.md` § "Removed legacy env variables" for the full list.

## Testing

Tests are `unittest`-based, located in `tests/`. Run with:
```bash
python -m unittest discover -s tests -q
```

For local host-side test runs, prefer the repo virtualenv:
```bash
./scripts/setup-local-python.sh
./scripts/test-local.sh
```
Test artifacts go to `tests/runs/` (git-ignored). Validation snapshot from 2026-02-13 is in `tests/runs/20260213-193644/`.

## Directory layout

```
app/
  mscl/        Flask MSCL acquisition app (bind-mounted in dev)
  redlab/      RedLab thermocouple collector
  almemo/      ALMEMO serial integration
  graf/        Graf App Lite dashboard
  ap/          Raspberry Pi AP operator UI
  matter/      Matter collector + Thread topology UI/API
  svcctl/      Service control & recovery API
dashboard/     nginx + simple-dash start page
grafana/       Grafana provisioning (datasources, dashboards)
scripts/       All build, deploy, setup, and diagnostic scripts
  lib/         Shared shell functions (compose-common.sh, setup-common.sh)
tests/         Python unit tests
docs/          Hardware manuals and integration notes
```
