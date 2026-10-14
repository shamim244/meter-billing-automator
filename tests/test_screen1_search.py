import unittest
from unittest.mock import MagicMock, patch
from smart_engine.screen1_search import Screen1Search

class TestScreen1Search(unittest.TestCase):
    def test_search_consumer_uses_fast_input_and_wait(self):
        mock_d = MagicMock()
        mock_d.app_start = MagicMock()
        mock_d.set_fastinput_ime = MagicMock()
        mock_d.wait_activity = MagicMock(return_value=True)

        # Mock element for bh_AccNo1search
        acc_field = MagicMock()
        acc_field.exists = MagicMock(return_value=True)
        # Mock element for cons_search
        search_btn = MagicMock()
        search_btn.exists = MagicMock(return_value=True)
        # Mock element for PresentStatus1 (GPS/Form readiness)
        ps_btn = MagicMock()
        ps_btn.wait = MagicMock(return_value=True)
        # Mock alertTitle
        alert_mock = MagicMock()
        alert_mock.exists = MagicMock(return_value=False)

        def selector_side_effect(resourceId=None, text=None):
            elem = MagicMock()
            if resourceId == "in.phoenix.bpdcl:id/bh_AccNo1search":
                return acc_field
            elif resourceId == "in.phoenix.bpdcl:id/cons_search":
                return search_btn
            elif resourceId == "in.phoenix.bpdcl:id/PresentStatus1":
                return ps_btn
            elif resourceId == "android:id/alertTitle":
                return alert_mock
            return elem

        mock_d.side_effect = selector_side_effect

        s1 = Screen1Search(device=mock_d)
        res = s1.search_consumer("10230047179")

        self.assertTrue(res)
        mock_d.set_fastinput_ime.assert_called_with(True)
        mock_d.app_start.assert_called_with(
            "in.phoenix.bpdcl",
            ".ConsumerSearchActivity",
            stop=False
        )

if __name__ == "__main__":
    unittest.main()
