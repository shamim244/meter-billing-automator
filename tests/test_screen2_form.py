import unittest
from unittest.mock import MagicMock
from smart_engine.screen2_form import Screen2Form

class TestScreen2Form(unittest.TestCase):
    def test_fill_form_invokes_direct_shell_without_subprocess(self):
        mock_d = MagicMock()
        mock_d.shell = MagicMock(return_value=("", 0))

        ps_btn = MagicMock()
        ps_btn.exists = MagicMock(return_value=True)
        ps_btn.wait = MagicMock(return_value=True)

        obs_btn = MagicMock()
        obs_btn.exists = MagicMock(return_value=True)
        obs_btn.wait = MagicMock(return_value=True)

        loc_btn = MagicMock()
        loc_btn.exists = MagicMock(return_value=True)
        loc_btn.wait = MagicMock(return_value=True)

        cam_btn = MagicMock()
        cam_btn.exists = MagicMock(return_value=True)
        cam_btn.wait = MagicMock(return_value=True)

        # Dropdown options
        opt_normal = MagicMock()
        opt_inside = MagicMock()

        # MR Bharat target element waiter
        mr_shutter = MagicMock()
        mr_shutter.wait = MagicMock(return_value=True)

        def selector_side_effect(resourceId=None, text=None):
            elem = MagicMock()
            if resourceId == "in.phoenix.bpdcl:id/PresentStatus1":
                return ps_btn
            elif resourceId == "in.phoenix.bpdcl:id/atMOBS1":
                return obs_btn
            elif resourceId == "in.phoenix.bpdcl:id/meterloctypeiv":
                return loc_btn
            elif resourceId == "in.phoenix.bpdcl:id/KwhCaptureButton":
                return cam_btn
            elif resourceId == "in.coral.bpdcl:id/captureImg":
                return mr_shutter
            elif text == "NORMAL":
                return opt_normal
            elif text == "Inside":
                return opt_inside
            return elem

        mock_d.side_effect = selector_side_effect
        mock_d.app_current.return_value = {"activity": "MeterReadingActivity", "package": "in.coral.bpdcl"}

        s2 = Screen2Form(device=mock_d)
        res = s2.fill_form_and_launch_camera(meter_type="NORMAL")

        self.assertTrue(res)
        # Verify direct shell DPAD execution occurred on mock_d.shell
        mock_d.shell.assert_called()
        self.assertTrue(any("input keyevent" in str(c) for c in mock_d.shell.call_args_list))

if __name__ == "__main__":
    unittest.main()
