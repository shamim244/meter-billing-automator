import unittest
from unittest.mock import MagicMock
from smart_engine.ui_cache import UniversalUICache, fast_get_current_activity

class TestUniversalUICache(unittest.TestCase):
    def setUp(self):
        self.cache = UniversalUICache(cache_file=None)
        self.cache.invalidate()

    def test_get_resolution_default_and_custom(self):
        mock_d = MagicMock()
        mock_d.window_size.return_value = (1080, 2400)
        self.assertEqual(self.cache.get_resolution(mock_d), (1080, 2400))
        self.assertEqual(self.cache.get_resolution_key(mock_d), "1080x2400")

        # Test landscape swap to portrait (min, max)
        mock_d.window_size.return_value = (2400, 1080)
        self.assertEqual(self.cache.get_resolution(mock_d), (1080, 2400))

    def test_cache_and_retrieve_exact_resolution(self):
        mock_d = MagicMock()
        mock_d.window_size.return_value = (1080, 2400)

        bounds = {"left": 400, "top": 1000, "right": 600, "bottom": 1200}
        coords = self.cache.cache_element_bounds("btn_test", mock_d, bounds)
        self.assertEqual(coords, (500, 1100))

        retrieved = self.cache.get_coordinates("btn_test", mock_d)
        self.assertEqual(retrieved, (500, 1100))

    def test_cross_device_ratio_scaling(self):
        # Calibrate on 1080x2400
        mock_d1 = MagicMock()
        mock_d1.window_size.return_value = (1080, 2400)
        # Center at x=540 (0.5), y=1200 (0.5)
        bounds = {"left": 440, "top": 1100, "right": 640, "bottom": 1300}
        self.cache.cache_element_bounds("btn_center", mock_d1, bounds)

        # Retrieve on 720x1600 (different phone display)
        mock_d2 = MagicMock()
        mock_d2.window_size.return_value = (720, 1600)
        scaled_coords = self.cache.get_coordinates("btn_center", mock_d2)
        # 0.5 * 720 = 360, 0.5 * 1600 = 800
        self.assertEqual(scaled_coords, (360, 800))

    def test_tap_hierarchy(self):
        mock_d = MagicMock()
        mock_d.window_size.return_value = (1080, 2400)

        # Tier 1: Cached tap
        self.cache.cache_element_bounds("btn_tap", mock_d, {"left": 100, "top": 200, "right": 300, "bottom": 400})
        ok = self.cache.tap("btn_tap", mock_d)
        self.assertTrue(ok)
        mock_d.click.assert_called_with(200, 300)

        # Tier 2: Selector tap and auto-cache
        mock_selector = MagicMock()
        mock_selector.info = {"bounds": {"left": 500, "top": 600, "right": 700, "bottom": 800}}
        ok = self.cache.tap("btn_new", mock_d, selector_obj=mock_selector)
        self.assertTrue(ok)
        mock_d.click.assert_called_with(600, 700)
        self.assertEqual(self.cache.get_coordinates("btn_new", mock_d), (600, 700))

    def test_invalidation(self):
        mock_d = MagicMock()
        mock_d.window_size.return_value = (1080, 2400)
        self.cache.cache_element_bounds("btn_del", mock_d, {"left": 10, "top": 10, "right": 30, "bottom": 30})
        self.assertIsNotNone(self.cache.get_coordinates("btn_del", mock_d))

        self.cache.invalidate("btn_del", mock_d)
        self.assertIsNone(self.cache.get_coordinates("btn_del", mock_d))

    def test_fast_get_current_activity(self):
        mock_d = MagicMock()
        mock_shell_out = MagicMock()
        mock_shell_out.output = "mCurrentFocus=Window{123 u0 in.phoenix.bpdcl/in.phoenix.bpdcl.BillingManualActivity}"
        mock_d.shell.return_value = mock_shell_out

        pkg, act = fast_get_current_activity(mock_d)
        self.assertEqual(pkg, "in.phoenix.bpdcl")
        self.assertEqual(act, "in.phoenix.bpdcl.BillingManualActivity")

if __name__ == "__main__":
    unittest.main()
