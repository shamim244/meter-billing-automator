import unittest
from unittest.mock import MagicMock, patch
from smart_engine.screen1_search import Screen1Search

class TestScreen1Search(unittest.TestCase):
    def test_search_consumer_uses_fast_input_and_wait(self):
        mock_d = MagicMock()
        mock_d.app_start = MagicMock()
        mock_d.set_fastinput_ime = MagicMock()
        # Full package name returned by real Android device
        mock_d.app_current.return_value = {
            "activity": "in.phoenix.billing.BillingManual",
            "package": "in.phoenix.bpdcl"
        }

        # Mock element for bh_AccNo1search
        acc_field = MagicMock()
        acc_field.exists = MagicMock(return_value=True)
        acc_field.wait = MagicMock(return_value=True)
        # Mock element for cons_search
        search_btn = MagicMock()
        search_btn.exists = MagicMock(return_value=True)
        search_btn.wait = MagicMock(return_value=True)
        # Mock element for PresentStatus1 (GPS/Form readiness)
        ps_btn = MagicMock()
        ps_btn.exists = MagicMock(return_value=True)
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
        acc_field.set_text.assert_called_with("10230047179")
        self.assertTrue(any("am start" in str(c) for c in mock_d.shell.call_args_list))

    def test_search_consumer_detects_error_alert(self):
        mock_d = MagicMock()
        mock_d.app_current.return_value = {
            "activity": "in.phoenix.bpdcl.ConsumerSearchActivity",
            "package": "in.phoenix.bpdcl"
        }

        acc_field = MagicMock()
        acc_field.wait = MagicMock(return_value=True)
        search_btn = MagicMock()
        search_btn.wait = MagicMock(return_value=True)

        alert_mock = MagicMock()
        alert_mock.exists = MagicMock(return_value=True)
        alert_mock.get_text = MagicMock(return_value="Consumer Not Found")

        msg_mock = MagicMock()
        msg_mock.exists = MagicMock(return_value=True)
        msg_mock.get_text = MagicMock(return_value="Invalid CA number")

        btn1_mock = MagicMock()
        btn1_mock.click_exists = MagicMock(return_value=True)

        def selector_side_effect(resourceId=None, text=None):
            if resourceId == "in.phoenix.bpdcl:id/bh_AccNo1search":
                return acc_field
            elif resourceId == "in.phoenix.bpdcl:id/cons_search":
                return search_btn
            elif resourceId == "android:id/alertTitle":
                return alert_mock
            elif resourceId == "android:id/message":
                return msg_mock
            elif resourceId == "android:id/button1":
                return btn1_mock
            elem = MagicMock()
            elem.exists = MagicMock(return_value=False)
            return elem

        mock_d.side_effect = selector_side_effect

        s1 = Screen1Search(device=mock_d)
        res = s1.search_consumer("99999999999", timeout=1.0)
        self.assertFalse(res)

if __name__ == "__main__":
    unittest.main()
