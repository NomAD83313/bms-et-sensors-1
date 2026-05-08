import unittest
from unittest.mock import patch

from app.messkluppe import messkluppe_app


class MesskluppeAppControlTests(unittest.TestCase):
    def setUp(self):
        self.client = messkluppe_app.app.test_client()

    def test_start_logging_updates_state_in_fake_mode(self):
        response = self.client.post("/api/clip/start-logging", json={"sample_rate": 500, "logging_time": 12})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"]["clip_mode"], "logging")
        self.assertEqual(payload["status"]["clip_task"], 20)
        self.assertTrue(payload["status"]["logging"])
        self.assertEqual(payload["status"]["sample_rate"], 500)
        self.assertEqual(payload["status"]["logging_time"], 12)

    def test_reset_mode_returns_to_idle(self):
        self.client.post("/api/clip/start-logging", json={"sample_rate": 500, "logging_time": 12})

        response = self.client.post("/api/clip/reset-mode")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"]["clip_mode"], "idle")
        self.assertEqual(payload["status"]["clip_task"], 0)
        self.assertFalse(payload["status"]["logging"])

    def test_live_start_accepts_known_display_modes(self):
        response = self.client.post("/api/clip/live/start", json={"display": "raw"})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"]["clip_mode"], "live")
        self.assertEqual(payload["status"]["clip_task"], 60)
        self.assertTrue(payload["status"]["live_mode"])
        self.assertEqual(payload["status"]["live_display"], "raw")

    def test_deep_sleep_controls_state(self):
        start = self.client.post("/api/clip/deep-sleep/start")
        stop = self.client.post("/api/clip/deep-sleep/stop")

        self.assertEqual(start.status_code, 200)
        self.assertTrue(start.get_json()["status"]["deep_sleep"])
        self.assertEqual(stop.status_code, 200)
        self.assertFalse(stop.get_json()["status"]["deep_sleep"])

    def test_files_endpoint_returns_contract_shape(self):
        response = self.client.get("/api/clip/files")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertIn("files", payload)
        self.assertIn("status", payload)

    def test_index_exposes_legacy_control_surface(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Start Logging", html)
        self.assertIn("Online Files", html)
        self.assertIn("startLoggingBtn", html)
        self.assertIn("Mock once", html)
        self.assertIn("api/mock-node/start", html)
        self.assertIn("api/clip/start-logging", html)
        self.assertIn("api/clip/files/delete-all", html)
        self.assertIn("Radio Diagnostics", html)
        self.assertIn("api/radio/diagnose", html)

    def test_radio_diagnostics_endpoint_updates_state(self):
        diag = {
            "ok": True,
            "configured": {"spi_bus": 0, "spi_device": 0, "ce_gpio": 25},
            "checks": {"spi_open": {"ok": True}},
            "registers": {"rf_ch": 111},
            "details": {"connected_hint": True},
            "duration_ms": 1.0,
            "error": "",
        }

        with patch.object(messkluppe_app, "run_radio_diagnostics", return_value=diag):
            response = self.client.post("/api/radio/diagnose")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["radio"], diag)
        self.assertEqual(payload["status"]["radio_last_diag"], diag)

    @patch.object(messkluppe_app, "_write_record", return_value=True)
    def test_mock_node_once_ingests_decoded_payload(self, _write_record):
        response = self.client.post("/api/mock-node/once")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["sample"]["file_id"], "mock-node")
        self.assertEqual(payload["status"]["last_record"]["tags"]["file_id"], "mock-node")
        self.assertGreaterEqual(payload["status"]["packets_received"], 1)


if __name__ == "__main__":
    unittest.main()
