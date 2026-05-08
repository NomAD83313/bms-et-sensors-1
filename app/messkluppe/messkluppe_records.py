from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from .messkluppe_protocol import FileDataPacket
except ImportError:
    from messkluppe_protocol import FileDataPacket


DEFAULT_MEASUREMENT = "messkluppe_sensor"
RAW_VALUE_NAMES = (
    "sensor_ms",
    "force_x_raw",
    "force_y_raw",
    "force_z_raw",
    "accel_x_raw",
    "accel_y_raw",
    "yaw_raw",
    "imu_temperature_raw",
    "clip_temperature_raw",
    "battery_raw",
    "reserved_1",
    "reserved_2",
)


@dataclass(frozen=True)
class MesskluppeInfluxRecord:
    measurement: str
    tags: dict[str, str]
    fields: dict[str, int | float | str]
    time_ns: int | None = None


def _signed16(value: int) -> int:
    item = int(value) & 0xFFFF
    return item - 0x10000 if item & 0x8000 else item


def _packet_time_ns(packet: FileDataPacket) -> int | None:
    if packet.unix_time <= 0:
        return None
    sensor_ms = int(packet.values[0]) if packet.values else 0
    if sensor_ms < 0 or sensor_ms > 999:
        sensor_ms = 0
    return (int(packet.unix_time) * 1_000_000_000) + (sensor_ms * 1_000_000)


def file_packet_to_fields(packet: FileDataPacket) -> dict[str, int | float | str]:
    fields: dict[str, int | float | str] = {
        "line": int(packet.line_number),
        "unix_time": int(packet.unix_time),
    }

    for idx, value in enumerate(packet.values):
        fields[f"raw_{idx:02d}"] = int(value)
        if idx < len(RAW_VALUE_NAMES):
            fields[RAW_VALUE_NAMES[idx]] = _signed16(value)

    if len(packet.values) > 6:
        fields["yaw_deg"] = round(_signed16(packet.values[6]) / 10.0, 3)
    if len(packet.values) > 7:
        fields["imu_temperature_c"] = round(_signed16(packet.values[7]) / 100.0, 3)

    return fields


def file_packet_to_influx_record(
    packet: FileDataPacket,
    *,
    measurement: str = DEFAULT_MEASUREMENT,
    source: str = "messkluppe",
    file_id: str | int | None = None,
) -> MesskluppeInfluxRecord:
    tags = {
        "source": source,
        "clip_id": str(packet.clip_id),
        "packet_task": str(packet.task),
    }
    if file_id is not None:
        tags["file_id"] = str(file_id)

    return MesskluppeInfluxRecord(
        measurement=measurement,
        tags=tags,
        fields=file_packet_to_fields(packet),
        time_ns=_packet_time_ns(packet),
    )


def record_to_line_protocol(record: MesskluppeInfluxRecord) -> str:
    def esc_key(value: str) -> str:
        return str(value).replace("\\", "\\\\").replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")

    def esc_string(value: str) -> str:
        return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'

    tags = ",".join(f"{esc_key(key)}={esc_key(value)}" for key, value in sorted(record.tags.items()) if value != "")
    fields: list[str] = []
    for key, value in sorted(record.fields.items()):
        if isinstance(value, bool):
            fields.append(f"{esc_key(key)}={'true' if value else 'false'}")
        elif isinstance(value, int):
            fields.append(f"{esc_key(key)}={value}i")
        elif isinstance(value, float):
            fields.append(f"{esc_key(key)}={value}")
        else:
            fields.append(f"{esc_key(key)}={esc_string(str(value))}")
    if not fields:
        raise ValueError("record must contain at least one field")
    head = esc_key(record.measurement)
    if tags:
        head = f"{head},{tags}"
    line = f"{head} {','.join(fields)}"
    if record.time_ns is not None:
        line = f"{line} {record.time_ns}"
    return line


def point_kwargs(record: MesskluppeInfluxRecord) -> dict[str, Any]:
    return {
        "measurement": record.measurement,
        "tags": dict(record.tags),
        "fields": dict(record.fields),
        "time_ns": record.time_ns,
    }
