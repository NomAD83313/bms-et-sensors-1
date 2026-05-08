import json
from pathlib import Path
from typing import Any


def default_redlab_channels(channel_keys: list[str]) -> dict[str, bool]:
    return {key: True for key in channel_keys}


def _is_redlab_selection_key(key: str, channel_keys: list[str]) -> bool:
    if key in channel_keys:
        return True
    if "|" not in key:
        return False
    device, channel = key.split("|", 1)
    return bool(device.strip()) and channel in channel_keys


def load_redlab_channels(state_path: Path, channel_keys: list[str]) -> dict[str, bool]:
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return default_redlab_channels(channel_keys)
        out = default_redlab_channels(channel_keys)
        for key in raw:
            if _is_redlab_selection_key(key, channel_keys):
                out[key] = bool(raw[key])
        return out
    except Exception:
        return default_redlab_channels(channel_keys)


def save_redlab_channels(
    state_path: Path,
    channel_keys: list[str],
    payload: dict[str, Any],
) -> dict[str, bool]:
    out = default_redlab_channels(channel_keys)
    for key in payload:
        if _is_redlab_selection_key(key, channel_keys):
            out[key] = bool(payload[key])
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    return out
