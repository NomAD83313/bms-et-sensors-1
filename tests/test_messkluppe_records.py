import unittest

from app.messkluppe.messkluppe_protocol import TASK_FILE_DOWNLOAD, decode_file_data_packet, make_id_task, words16_to_legacy_payload
from app.messkluppe.messkluppe_records import file_packet_to_fields, file_packet_to_influx_record, record_to_line_protocol


class MesskluppeRecordTests(unittest.TestCase):
    def _packet(self):
        payload = words16_to_legacy_payload([
            make_id_task(1, TASK_FILE_DOWNLOAD),
            0x5E2D,
            0x1234,
            0x0000,
            0x0009,
            123,
            0xFFFE,
            102,
            103,
            104,
            105,
            1234,
            2500,
            2600,
            3700,
            0,
        ])
        return decode_file_data_packet(payload)

    def test_file_packet_to_fields_keeps_raw_and_named_values(self):
        fields = file_packet_to_fields(self._packet())

        self.assertEqual(fields["line"], 9)
        self.assertEqual(fields["sensor_ms"], 123)
        self.assertEqual(fields["force_x_raw"], -2)
        self.assertEqual(fields["yaw_raw"], 1234)
        self.assertEqual(fields["yaw_deg"], 123.4)
        self.assertEqual(fields["raw_01"], 0xFFFE)

    def test_file_packet_to_influx_record_sets_tags_and_time(self):
        record = file_packet_to_influx_record(self._packet(), file_id=1580000000)

        self.assertEqual(record.measurement, "messkluppe_sensor")
        self.assertEqual(record.tags["source"], "messkluppe")
        self.assertEqual(record.tags["clip_id"], "1")
        self.assertEqual(record.tags["file_id"], "1580000000")
        self.assertEqual(record.time_ns, 0x5E2D1234 * 1_000_000_000 + 123_000_000)

    def test_record_to_line_protocol(self):
        record = file_packet_to_influx_record(self._packet(), file_id=1580000000)
        line = record_to_line_protocol(record)

        self.assertIn("messkluppe_sensor,clip_id=1,file_id=1580000000,packet_task=40,source=messkluppe", line)
        self.assertIn("force_x_raw=-2i", line)
        self.assertIn("yaw_deg=123.4", line)
        self.assertTrue(line.endswith(str(record.time_ns)))


if __name__ == "__main__":
    unittest.main()
