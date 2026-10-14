import unittest
from unittest.mock import MagicMock
from smart_engine.screen3_camera import Screen3Camera

class TestScreen3Camera(unittest.TestCase):
    def test_camera_handles_revalidate_and_submit(self):
        mock_d = MagicMock()

        # Elements
        pre_capture = MagicMock()
        pre_capture.exists = MagicMock(return_value=False)
        pre_capture.wait = MagicMock(return_value=False)

        shutter = MagicMock()
        shutter.exists = MagicMock(return_value=True)
        shutter.wait = MagicMock(return_value=True)

        input_field = MagicMock()
        input_field.exists = MagicMock(return_value=True)
        input_field.wait = MagicMock(return_value=True)

        save_btn = MagicMock()
        save_btn.exists = MagicMock(return_value=True)
        save_btn.wait = MagicMock(return_value=True)

        sec_title = MagicMock()
        sec_title.exists = MagicMock(return_value=False)

        sec_submit = MagicMock()
        sec_submit.exists = MagicMock(return_value=False)

        reval_btn = MagicMock()
        # Simulate revalidate appearing
        reval_btn.exists = MagicMock(return_value=True)
        reval_btn.wait = MagicMock(return_value=True)

        rep_btn = MagicMock()
        rep_btn.exists = MagicMock(return_value=True)
        rep_btn.wait = MagicMock(return_value=True)

        remark_opt = MagicMock()
        remark_opt.exists = MagicMock(return_value=True)
        remark_opt.wait = MagicMock(return_value=True)

        final_submit = MagicMock()
        final_submit.exists = MagicMock(return_value=True)
        final_submit.wait = MagicMock(return_value=True)

        # Device activity mock: initially in MR Bharat, then transitions back to BillingManual
        mock_d.app_current.side_effect = [
            {"activity": "ScanMeterActivity", "package": "in.coral.bpdcl"},
            {"activity": "BillingManual", "package": "in.phoenix.bpdcl"},
            {"activity": "BillingManual", "package": "in.phoenix.bpdcl"}
        ]

        def selector_side_effect(resourceId=None, text=None):
            elem = MagicMock()
            if resourceId == "in.coral.bpdcl:id/capture_readings_btn":
                return pre_capture
            elif resourceId == "in.coral.bpdcl:id/captureImg":
                return shutter
            elif resourceId == "in.coral.bpdcl:id/input":
                return input_field
            elif text == "Save":
                return save_btn
            elif resourceId == "in.coral.bpdcl:id/dialog_title_text":
                return sec_title
            elif resourceId == "in.coral.bpdcl:id/revalidate_btn":
                return reval_btn
            elif resourceId == "in.coral.bpdcl:id/btn_report":
                return rep_btn
            elif text == "Readings are correct":
                return remark_opt
            elif resourceId == "in.coral.bpdcl:id/submit_btn":
                return final_submit
            return elem

        mock_d.side_effect = selector_side_effect

        s3 = Screen3Camera(device=mock_d)
        res = s3.handle_camera_and_review(reading_kwh=1355)

        self.assertTrue(res)
        input_field.set_text.assert_called_with("1355")
        shutter.click.assert_called()

if __name__ == "__main__":
    unittest.main()
