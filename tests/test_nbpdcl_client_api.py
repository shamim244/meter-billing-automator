import unittest
from unittest.mock import MagicMock, patch
from chat.nbpdcl_client import NBPDCLClient, build_review

class TestNBPDCLClientApi(unittest.TestCase):
    def setUp(self):
        self.client = NBPDCLClient(base_url="http://127.0.0.1:8000/api/v1", api_key="nbp_live_test_key_123")

    @patch("chat.nbpdcl_client.requests.get")
    def test_get_automation_queue_with_apply_tuning(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "success": True,
            "consumers": [
                {
                    "ca_number": "10230040377",
                    "smart_average_kwh": 46,
                    "base_avg_units": 46,
                    "tuned_avg_units": 50,
                    "min_avg_units": 30,
                    "max_avg_units": 90,
                    "is_clamped_min": False,
                    "is_clamped_max": False
                }
            ]
        }
        mock_get.return_value = mock_resp

        res = self.client.get_automation_queue(
            mru_id="8",
            cycle="OCT-2026",
            limit=10,
            apply_tuning=True,
            min_units_floor=125,
            max_units_ceiling=200,
            adjustment_percent=10.0,
            ca="10230062566"
        )
        self.assertTrue(res["success"])
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertIn("apply_tuning", kwargs["params"])
        self.assertEqual(kwargs["params"]["apply_tuning"], "true")
        self.assertEqual(kwargs["params"]["min_units_floor"], 125)
        self.assertEqual(kwargs["params"]["max_units_ceiling"], 200)
        self.assertEqual(kwargs["params"]["adjustment_percent"], 10.0)
        self.assertEqual(kwargs["params"]["ca"], "10230062566")

    @patch("chat.nbpdcl_client.requests.post")
    def test_update_consumer_average_tuning(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "success": True,
            "consumer": {
                "ca_number": "10230040377",
                "min_avg_units": 35,
                "max_avg_units": 85
            }
        }
        mock_post.return_value = mock_resp

        res = self.client.update_consumer_average_tuning(
            ca="10230040377",
            min_avg_units=35,
            max_avg_units=85,
            custom_avg_units=60
        )
        self.assertTrue(res["success"])
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertTrue(args[0].endswith("/consumers/10230040377/average-tuning"))
        self.assertEqual(kwargs["json"]["min_avg_units"], 35)
        self.assertEqual(kwargs["json"]["max_avg_units"], 85)
        self.assertEqual(kwargs["json"]["custom_avg_units"], 60)

    @patch("chat.nbpdcl_client.requests.post")
    def test_submit_batch_sync_supports_both_signatures(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "synced_count": 1}
        mock_post.return_value = mock_resp

        reviews = [{"ca_number": "10230040377", "status": "submitted", "working_reading": "1200"}]
        
        # Test signature with reviews only
        res = self.client.submit_batch_sync(reviews)
        self.assertTrue(res["success"])

        # Test explicit signature
        res2 = self.client.submit_batch_sync(reviews, billing_month=10, billing_year=2026)
        self.assertTrue(res2["success"])

if __name__ == "__main__":
    unittest.main()
