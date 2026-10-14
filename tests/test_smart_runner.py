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
                    "ca_number": "144208013167",
                    "consumer_name": "SHAMSHER ALI",
                    "billing_basis": "MD",
                    "suggested_reading": 50
                },
                {
                    "ca_number": "10230057913",
                    "consumer_name": "MD NASIR",
                    "billing_basis": "OK",
                    "suggested_reading": 50
                }
            ]
        }

        runner = SmartRunner(mru="8", cycle="OCT-2026", dry_run=True)
        stats = runner.run_batch(limit=2)

        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["processed"], 2)
        self.assertEqual(stats["failed"], 0)

if __name__ == "__main__":
    unittest.main()
