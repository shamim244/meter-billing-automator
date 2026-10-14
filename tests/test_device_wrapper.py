import unittest
from unittest.mock import MagicMock, patch
from smart_engine.device import SmartDevice

class TestSmartDeviceWrapper(unittest.TestCase):
    def setUp(self):
        self.device = SmartDevice(serial="192.168.9.40:5555")

    @patch("smart_engine.device.u2.connect")
    def test_connect_success(self, mock_u2_connect):
        mock_d = MagicMock()
        mock_d.info = {"currentPackageName": "in.phoenix.bpdcl"}
        mock_u2_connect.return_value = mock_d

        connected = self.device.connect()
        self.assertTrue(connected)
        self.assertIsNotNone(self.device.d)
        mock_u2_connect.assert_called_once_with("192.168.9.40:5555")

    def test_click_element_with_mock(self):
        self.device.d = MagicMock()
        self.device.click_element(text="Submit")
        self.device.d.assert_called_once_with(text="Submit")
        self.device.d.return_value.click.assert_called_once()

    def test_set_text_with_mock(self):
        self.device.d = MagicMock()
        self.device.set_text(text="2522", resource_id="txt_reading")
        self.device.d.assert_called_once_with(resourceId="txt_reading")
        self.device.d.return_value.set_text.assert_called_once_with("2522")

    def test_get_compressed_hierarchy_with_mock(self):
        self.device.d = MagicMock()
        self.device.d.dump_hierarchy.return_value = "<hierarchy><node text='OK'/></hierarchy>"
        xml = self.device.get_compressed_hierarchy()
        self.assertIn("node text='OK'", xml)
        self.device.d.dump_hierarchy.assert_called_once_with(compressed=True)

if __name__ == "__main__":
    unittest.main()
