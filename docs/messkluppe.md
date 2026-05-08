# Messkluppe Legacy Integration

Messkluppe is a legacy nRF24L01-based clip sensor system found under `~/Documents`.

Source reference:

- Host/Raspberry Pi app: `~/Documents/!FOK/Flask_Messkluppe`
- Older host copy: `~/Documents/MesskluppeMaster-master/_Rpi`
- Node firmware: `~/Documents/MesskluppeMaster-master/*.ino`

The new stack integration should preserve the protocol but avoid importing the old Flask UI, SQLite runtime state, generated CSV files, compiled RF24 artifacts, and Python cache files.

Old SQLite should not be used as the primary database in this stack. The migration target is the existing stack InfluxDB.

## Protocol

The node sends fixed 32-byte nRF24 payloads. Most node payloads are interpreted as sixteen little-endian `uint16` words. Host commands are encoded as up to eight unsigned 32-bit words, each split to bytes in the same order used by the legacy `translate_to_radio` helper.

The first word is `clip_id * 1000 + task`.

Known task values:

- `0`: idle / ping
- `10`: deep sleep
- `20`: start logging
- `30`: send file list
- `39`: file list finished
- `40`: send file data
- `49`: file download finished
- `50`: delete one file
- `51`: delete all files
- `59`: delete finished
- `60`: live data
- `99`: host acknowledgement / return to idle

File download payloads use a special decode path because `unix_time` and `line_number` are reconstructed from pairs of 16-bit words.

## Integration Direction

The planned service is `messkluppe-collector`:

`Arduino node -> nRF24 binary payloads -> messkluppe-collector -> InfluxDB -> graf-lite/Grafana`

The first runnable version is intentionally host-side only:

- It starts as a Compose profile service, so the default stack is unchanged.
- `MESSKLUPPE_FAKE_MODE=1` generates synthetic decoded packets and writes them to InfluxDB. This validates the storage path before real nRF24 hardware is connected.
- Real nRF24/RPi GPIO support is still pending and should be added behind the same collector API.

Run:

```bash
docker compose --profile messkluppe -f docker-compose.yml -f docker-compose.override.yml up -d messkluppe-collector
```

HTTP endpoints:

- `GET /`: built-in collector status UI.
- `GET /health`: collector health and state.
- `GET /api/status`: collector state.
- `POST /api/fake-once`: generate and ingest one synthetic packet.
- `POST /api/fake/start`: start the synthetic packet loop.
- `POST /api/fake/stop`: stop the synthetic packet loop.
- `POST /api/ingest-hex`: ingest one 32-byte legacy payload as hex, useful for replay tests.

Legacy-compatible control API skeleton:

- `POST /api/clip/start-logging` with JSON `sample_rate` and `logging_time`.
- `POST /api/clip/stop-logging`.
- `POST /api/clip/reset-mode`.
- `POST /api/clip/deep-sleep/start`.
- `POST /api/clip/deep-sleep/stop`.
- `POST /api/clip/live/start` with JSON `display` (`linearForce` or `raw`).
- `POST /api/clip/live/stop`.
- `GET /api/clip/files`.
- `POST /api/clip/files/download`.
- `POST /api/clip/files/delete`.
- `POST /api/clip/files/delete-all`.

In fake mode these endpoints update collector state and return success. In real-radio mode they currently return `501` until the nRF24 transport is implemented.

When the dashboard is running, nginx exposes the UI at `/messkluppe/` and the health probe at `/probe/messkluppe`.

Relevant environment variables:

- `MESSKLUPPE_APP_PORT` default `3080`.
- `MESSKLUPPE_FAKE_MODE` default `1`.
- `MESSKLUPPE_FAKE_INTERVAL_SEC` default `5.0`.
- `MESSKLUPPE_INFLUX_MEASUREMENT` default `messkluppe_sensor`.
- `MESSKLUPPE_SOURCE_TAG` default `messkluppe`.

## Visualization

The collector writes decoded force packets to InfluxDB measurement `messkluppe_sensor`.

Graf App Lite exposes the data in two places:

- `/graf/`: the All view includes the Messkluppe Force panel.
- `/graf/messkluppe`: a dedicated Messkluppe window for `force_x_raw`, `force_y_raw`, and `force_z_raw`.

The dedicated view also provides CSV export through `/graf/api/export/messkluppe.csv`.

Grafana provisioning includes a `Messkluppe Force` panel in the main dashboard. Restart `grafana` after changing provisioning files so the mounted dashboard JSON is reloaded.

Initial code should stay hardware-independent:

- `app/messkluppe/messkluppe_protocol.py`: byte order, task ids, packet parsing, command encoding.
- `app/messkluppe/messkluppe_records.py`: decoded packet to Influx-ready records and line protocol.
- `app/messkluppe/messkluppe_app.py`: minimal Flask collector app with fake ingest and Influx writing.
- Unit tests under `tests/` using synthetic payloads.

Hardware-facing nRF24/RPi GPIO code should be added as a separate layer after the protocol tests are stable.

## Legacy Host Transfer

The current legacy host source has been copied to `app/messkluppe/legacy_host/` as a reference and migration starting point.

Tracked files include:

- Flask app, radio helpers, OLED display script, templates, static UI assets, and legacy systemd unit files.
- `db.schema.sql`, generated from the old `db.db` schema and default settings.
- `static/_csv/.gitkeep`, preserving the runtime CSV directory without committing historical measurements.

Excluded runtime files:

- `db.db`
- `static/_csv/*.csv`
- Python caches and compiled files

The legacy app still contains hardcoded Raspberry Pi paths and old dependencies. It should be treated as imported source, not as a finished Docker service.
