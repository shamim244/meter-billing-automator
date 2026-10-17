import unittest
from unittest.mock import MagicMock, patch
from smart_engine.runner import SmartRunner

class TestSmartRunner(unittest.TestCase):
    @patch("smart_engine.runner.NBPDCLClient")
    def test_dry_run_queue_processing(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_automation_queue.return_value = {
            "success": True,
            "consumers": [
                {
                    "ca_number": "10230062566",
                    "consumer_name": "KOTARU CH DAS BIDESHI DAS",
                    "billing_basis": "OK",
                    "suggested_reading": 1140
                },
                {
                    "ca_number": "10230057913",
                    "consumer_name": "MD NASIR",
                    "billing_basis": "OK",
                    "suggested_reading": 50
                }
            ]
        }

        runner = SmartRunner(
            mru="8",
            cycle="OCT-2026",
            dry_run=True,
            apply_tuning=True,
            min_floor=125,
            max_ceiling=200,
            adjust_percent=5.0,
            ca="10230062566"
        )
        stats = runner.run_batch(limit=2)

        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["failed"], 0)

        mock_client.get_automation_queue.assert_called_once_with(
            mru_id="8",
            cycle="OCT-2026",
            limit=2,
            apply_tuning=True,
            min_units_floor=125,
            max_units_ceiling=200,
            adjustment_percent=5.0,
            ca="10230062566"
        )

if __name__ == "__main__":
    unittest.main()
