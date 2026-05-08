import unittest

from app.graf.graf_views import VIEW_CONFIGS


class GrafViewsTests(unittest.TestCase):
    def test_pyrometers_view_uses_friendly_titles(self):
        cfg = VIEW_CONFIGS["pyrometers"]

        self.assertEqual(cfg["title"], "Graf App Lite · Pyrometers")
        self.assertEqual(cfg["device"]["panel_title"], "Pyrometers")

    def test_matter_view_uses_generic_matter_temperature_title(self):
        cfg = VIEW_CONFIGS["matter"]

        self.assertEqual(cfg["title"], "Graf App Lite · Matter")
        self.assertEqual(cfg["device"]["panel_title"], "Matter Temperature")

    def test_all_view_includes_messkluppe_panel(self):
        cfg = VIEW_CONFIGS["all"]

        self.assertTrue(cfg["show_messkluppe"])

    def test_messkluppe_view_uses_force_window(self):
        cfg = VIEW_CONFIGS["messkluppe"]

        self.assertEqual(cfg["title"], "Graf App Lite · Messkluppe")
        self.assertEqual(cfg["device"]["panel_title"], "Messkluppe Force")
        self.assertEqual(cfg["device"]["chart_id"], "c6")


if __name__ == "__main__":
    unittest.main()
