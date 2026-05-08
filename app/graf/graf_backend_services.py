from datetime import timezone
from typing import Any

from influxdb_client import InfluxDBClient

from graf_csv_helpers import build_csv_content, make_csv_filename, make_csv_response
from graf_query_builders import (
    almemo_flux,
    matter_flux,
    messkluppe_flux,
    mscl_flux,
    redlab_flux,
    redlab_flux_raw,
    split_env_list,
    tail_flux,
    pyrometers_flux,
)
from graf_series_helpers import (
    duration_to_ns,
    normalize_mscl_display_series,
    resample_series,
    series_median_interval_ms,
)


def build_backend_services(
    *,
    influx_url: str,
    influx_token: str,
    influx_org: str,
    influx_bucket: str,
    mscl_measurement: str,
    mscl_source: str,
    mscl_source_extra: str,
    mscl_channel: str,
    redlab_measurement: str,
    almemo_measurement: str,
    pyrometers_measurement: str,
    messkluppe_measurement: str,
    matter_measurement: str,
    parse_iso_ts_fn,
):
    mscl_sources = split_env_list(",".join([mscl_source, mscl_source_extra]))

    def to_iso_z(dt_obj) -> str:
        try:
            return dt_obj.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except Exception:
            try:
                return dt_obj.isoformat().replace("+00:00", "Z")
            except Exception:
                return ""

    def new_client() -> InfluxDBClient:
        return InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)

    def query_series(flux_query: str, key_fields: list[str]) -> list[dict[str, Any]]:
        if not all([influx_token, influx_org, influx_bucket]):
            return []

        out: dict[str, dict[str, Any]] = {}
        try:
            with new_client() as client:
                tables = client.query_api().query(flux_query, org=influx_org)
                for table in tables:
                    for rec in table.records:
                        values = rec.values or {}
                        label_parts = []
                        for field in key_fields:
                            val = values.get(field)
                            if val is not None and str(val) != "":
                                label_parts.append(f"{field}={val}")
                        if not label_parts:
                            label_parts.append(f"field={rec.get_field()}")
                        key = " | ".join(label_parts)

                        series = out.setdefault(
                            key,
                            {
                                "name": key,
                                "points": [],
                            },
                        )
                        time_obj = rec.get_time()
                        sort_ns = None
                        try:
                            sort_ns = int(time_obj.timestamp() * 1_000_000_000)
                        except Exception:
                            sort_ns = None
                        series["points"].append(
                            {
                                "_sort_ns": sort_ns,
                                "t": to_iso_z(time_obj),
                                "v": rec.get_value(),
                            }
                        )
        except Exception:
            return []

        for series in out.values():
            points = list(series.get("points") or [])
            points.sort(
                key=lambda point: (
                    point.get("_sort_ns") is None,
                    point.get("_sort_ns") if point.get("_sort_ns") is not None else 0,
                    point.get("t", ""),
                )
            )
            for point in points:
                point.pop("_sort_ns", None)
            series["points"] = points
        return list(out.values())

    def mscl_query(start_expr: str, stop_expr: str | None) -> str:
        return mscl_flux(
            bucket=influx_bucket,
            measurement=mscl_measurement,
            channel=mscl_channel,
            source_values=mscl_sources,
            start_expr=start_expr,
            stop_expr=stop_expr,
        )

    def redlab_query(start_expr: str, stop_expr: str | None, window: str) -> str:
        if window == "__raw__":
            return redlab_flux_raw(
                bucket=influx_bucket,
                measurement=redlab_measurement,
                start_expr=start_expr,
                stop_expr=stop_expr,
            )
        return redlab_flux(
            bucket=influx_bucket,
            measurement=redlab_measurement,
            start_expr=start_expr,
            stop_expr=stop_expr,
            window=window,
        )

    def almemo_query(start_expr: str, stop_expr: str | None, window: str) -> str:
        return almemo_flux(
            bucket=influx_bucket,
            measurement=almemo_measurement,
            start_expr=start_expr,
            stop_expr=stop_expr,
            window=window,
        )

    def pyrometers_query(start_expr: str, stop_expr: str | None, window: str) -> str:
        return pyrometers_flux(
            bucket=influx_bucket,
            measurement=pyrometers_measurement,
            start_expr=start_expr,
            stop_expr=stop_expr,
            window=window,
        )

    def messkluppe_query(start_expr: str, stop_expr: str | None, window: str) -> str:
        return messkluppe_flux(
            bucket=influx_bucket,
            measurement=messkluppe_measurement,
            start_expr=start_expr,
            stop_expr=stop_expr,
            window=window,
        )

    def matter_query(start_expr: str, stop_expr: str | None, window: str) -> str:
        return matter_flux(
            bucket=influx_bucket,
            measurement=matter_measurement,
            start_expr=start_expr,
            stop_expr=stop_expr,
            window=window,
        )

    def sampled_mscl_series(start_expr: str, stop_expr: str | None, window: str, raw_mode: bool = False) -> list[dict[str, Any]]:
        raw = query_series(mscl_query(start_expr, stop_expr), ["_measurement", "device", "source", "node_id", "channel"])
        normalized = normalize_mscl_display_series(raw, parse_iso_ts_fn)
        if raw_mode:
            return normalized
        window_ns = duration_to_ns(window) or 1_000_000_000
        return resample_series(normalized, window_ns, parse_iso_ts_fn)

    def load_mscl_series(start_expr: str, stop_expr: str | None, window: str, raw_mode: bool) -> list[dict[str, Any]]:
        return sampled_mscl_series(start_expr, stop_expr, window, raw_mode=raw_mode)

    def load_redlab_series(start_expr: str, stop_expr: str | None, window: str, raw_mode: bool) -> list[dict[str, Any]]:
        query = redlab_query(start_expr, stop_expr, "__raw__" if raw_mode else window)
        return query_series(query, ["device", "channel", "field"])

    def load_almemo_series(start_expr: str, stop_expr: str | None, window: str, raw_mode: bool) -> list[dict[str, Any]]:
        del raw_mode
        return query_series(almemo_query(start_expr, stop_expr, window), ["device", "mode", "channel", "unit", "sensor"])

    def load_pyrometers_series(start_expr: str, stop_expr: str | None, window: str, raw_mode: bool) -> list[dict[str, Any]]:
        del raw_mode
        return query_series(pyrometers_query(start_expr, stop_expr, window), ["source", "device", "_field"])

    def load_messkluppe_series(start_expr: str, stop_expr: str | None, window: str, raw_mode: bool) -> list[dict[str, Any]]:
        query_window = "__raw__" if raw_mode else window
        return query_series(messkluppe_query(start_expr, stop_expr, query_window), ["source", "clip_id", "file_id", "_field"])

    def load_matter_series(start_expr: str, stop_expr: str | None, window: str, raw_mode: bool) -> list[dict[str, Any]]:
        del raw_mode
        return query_series(matter_query(start_expr, stop_expr, window), ["source", "node_id", "endpoint_id", "cluster_id"])

    def panel_raw_cadence_ms(panel_key: str, start_expr: str, stop_expr: str | None) -> float | None:
        tail_n = 12
        if panel_key == "mscl_temperature":
            series = query_series(tail_flux(mscl_query(start_expr, stop_expr), tail_n), ["_measurement", "device", "source", "node_id", "channel"])
            series = normalize_mscl_display_series(series, parse_iso_ts_fn)
            return series_median_interval_ms(series, parse_iso_ts_fn)
        if panel_key == "redlab_temperature":
            series = query_series(tail_flux(redlab_query(start_expr, stop_expr, "__raw__"), tail_n), ["device", "channel", "field"])
            return series_median_interval_ms(series, parse_iso_ts_fn)
        if panel_key == "almemo_live":
            series = query_series(tail_flux(almemo_query(start_expr, stop_expr, "__raw__"), tail_n), ["device", "mode", "channel", "unit", "sensor"])
            return series_median_interval_ms(series, parse_iso_ts_fn)
        if panel_key == "pyrometers_temperature":
            series = query_series(tail_flux(pyrometers_query(start_expr, stop_expr, "__raw__"), tail_n), ["source", "device", "_field"])
            return series_median_interval_ms(series, parse_iso_ts_fn)
        if panel_key == "messkluppe_force":
            series = query_series(tail_flux(messkluppe_query(start_expr, stop_expr, "__raw__"), tail_n), ["source", "clip_id", "file_id", "_field"])
            return series_median_interval_ms(series, parse_iso_ts_fn)
        if panel_key == "matter_temperature":
            series = query_series(tail_flux(matter_query(start_expr, stop_expr, "__raw__"), tail_n), ["source", "node_id", "endpoint_id", "cluster_id"])
            return series_median_interval_ms(series, parse_iso_ts_fn)
        return None

    def csv_export_response(
        *,
        by_ts: dict[str, dict[str, Any]],
        cols: set[str],
        precision: int,
        filename_prefix: str,
        sample_key: str,
        range_key: str,
        column_prefix: str = "",
        delimiter: str = ",",
        decimal_separator: str = ".",
    ):
        ordered_cols = [f"{column_prefix}{col}" for col in sorted(cols)]
        csv_content = build_csv_content(
            by_ts,
            ordered_cols,
            parse_iso_ts_fn=parse_iso_ts_fn,
            precision=precision,
            column_prefix=column_prefix,
            delimiter=delimiter,
            decimal_separator=decimal_separator,
        )
        filename = make_csv_filename(filename_prefix, sample_key, range_key)
        return make_csv_response(csv_content, filename)

    return {
        "to_iso_z_fn": to_iso_z,
        "load_mscl_series_fn": load_mscl_series,
        "load_redlab_series_fn": load_redlab_series,
        "load_almemo_series_fn": load_almemo_series,
        "load_pyrometers_series_fn": load_pyrometers_series,
        "load_messkluppe_series_fn": load_messkluppe_series,
        "load_matter_series_fn": load_matter_series,
        "panel_raw_cadence_ms_fn": panel_raw_cadence_ms,
        "csv_export_response_fn": csv_export_response,
    }
