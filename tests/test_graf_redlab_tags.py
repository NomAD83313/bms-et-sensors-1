import tempfile
import unittest
from pathlib import Path

from app.graf.graf_csv_helpers import messkluppe_csv_column_name, redlab_csv_column_name
from app.graf.graf_query_builders import messkluppe_flux, redlab_flux, redlab_flux_raw
from app.graf.graf_redlab_state import load_redlab_channels, save_redlab_channels


class GrafRedLabTagTests(unittest.TestCase):
    def test_redlab_flux_keeps_device_and_channel_tags(self):
        query = redlab_flux(
            bucket="sensors",
            measurement="redlab",
            start_expr="-5m",
            stop_expr=None,
            window="1s",
        )

        self.assertIn('"device", "channel"', query)
        self.assertNotIn("redlab_daq", query)

    def test_redlab_raw_flux_keeps_device_and_channel_tags(self):
        query = redlab_flux_raw(
            bucket="sensors",
            measurement="redlab",
            start_expr="-5m",
            stop_expr=None,
        )

        self.assertIn('"device", "channel"', query)
        self.assertNotIn("redlab_daq", query)

    def test_redlab_csv_column_name_uses_device_and_channel(self):
        name = "device=redlab_01A31CE0 | channel=ch0"
        self.assertEqual(redlab_csv_column_name(name), "redlab_01A31CE0_ch0")

    def test_messkluppe_flux_selects_force_fields(self):
        query = messkluppe_flux(
            bucket="sensors",
            measurement="messkluppe_sensor",
            start_expr="-5m",
            stop_expr=None,
            window="1s",
        )

        self.assertIn('r._measurement == "messkluppe_sensor"', query)
        self.assertIn('r._field == "force_x_raw"', query)
        self.assertIn('r._field == "force_y_raw"', query)
        self.assertIn('r._field == "force_z_raw"', query)
        self.assertIn('"clip_id", "file_id"', query)

    def test_messkluppe_csv_column_name_uses_clip_file_and_field(self):
        name = "source=messkluppe | clip_id=1 | file_id=fake | _field=force_x_raw"
        self.assertEqual(messkluppe_csv_column_name(name), "messkluppe_clip_1_file_fake_force_x_raw")

    def test_redlab_channel_state_preserves_device_channel_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "redlab_channels.json"
            saved = save_redlab_channels(
                path,
                ["ch0", "ch1"],
                {
                    "ch0": False,
                    "redlab_01A31CE0|ch0": True,
                    "redlab_0233CFAA|ch1": False,
                    "bad_device|ch9": False,
                },
            )

            self.assertEqual(saved["ch0"], False)
            self.assertEqual(saved["redlab_01A31CE0|ch0"], True)
            self.assertEqual(saved["redlab_0233CFAA|ch1"], False)
            self.assertNotIn("bad_device|ch9", saved)
            self.assertEqual(load_redlab_channels(path, ["ch0", "ch1"]), saved)


if __name__ == "__main__":
    unittest.main()
