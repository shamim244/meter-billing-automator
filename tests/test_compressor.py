import unittest
from smart_engine.compressor import ContextCompressor

MOCK_FORM_XML = """
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="in.phoenix.bpdcl" bounds="[0,0][1080,2400]">
    <node index="0" text="" resource-id="" class="android.widget.LinearLayout" bounds="[0,0][1080,2400]">
      <node index="0" text="NORMAL" resource-id="in.phoenix.bpdcl:id/PresentStatus1" class="android.widget.Spinner" clickable="true" bounds="[30,1746][1050,1886]"/>
      <node index="1" text="OK" resource-id="in.phoenix.bpdcl:id/atMOBS1" class="android.widget.Spinner" clickable="true" bounds="[30,1872][1050,2012]"/>
      <node index="2" text="Inside" resource-id="in.phoenix.bpdcl:id/meterloctypeiv" class="android.widget.Spinner" clickable="true" bounds="[30,1998][1050,2138]"/>
      <node index="3" text="Submit" resource-id="in.phoenix.bpdcl:id/Submit" class="android.widget.Button" clickable="true" bounds="[200,2200][880,2340]"/>
    </node>
  </node>
</hierarchy>
"""

MOCK_ALERT_XML = """
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.coral.meter" bounds="[0,0][1080,2400]">
    <node index="0" text="Electro Mechanical Meter" resource-id="android:id/alertTitle" class="android.widget.TextView" bounds="[100,1000][980,1100]"/>
    <node index="1" text="KW is not available in the Meter." resource-id="android:id/message" class="android.widget.TextView" bounds="[100,1120][980,1250]"/>
    <node index="2" text="Cancel" resource-id="android:id/button2" class="android.widget.Button" clickable="true" bounds="[100,1320][450,1450]"/>
    <node index="3" text="Submit" resource-id="android:id/button1" class="android.widget.Button" clickable="true" bounds="[630,1320][980,1450]"/>
  </node>
</hierarchy>
"""

class TestContextCompressor(unittest.TestCase):
    def setUp(self):
        self.compressor = ContextCompressor()

    def test_extract_form_options(self):
        result = self.compressor.compress_xml(MOCK_FORM_XML, screen="BillingManual")
        self.assertEqual(result["screen"], "BillingManual")
        self.assertIsNone(result.get("alert"))
        options = result["options"]
        self.assertEqual(len(options), 4)
        texts = [opt["text"] for opt in options]
        self.assertIn("NORMAL", texts)
        self.assertIn("OK", texts)
        self.assertIn("Inside", texts)
        self.assertIn("Submit", texts)

    def test_extract_alert_dialog(self):
        result = self.compressor.compress_xml(MOCK_ALERT_XML, screen="ScanMeterActivity")
        self.assertEqual(result["screen"], "ScanMeterActivity")
        alert = result.get("alert")
        self.assertIsNotNone(alert)
        self.assertEqual(alert["title"], "Electro Mechanical Meter")
        self.assertIn("KW is not available", alert["message"])
        options = result["options"]
        btn_texts = [opt["text"] for opt in options]
        self.assertIn("Submit", btn_texts)
        self.assertIn("Cancel", btn_texts)

    def test_to_jev_state_token_size(self):
        result = self.compressor.compress_xml(MOCK_ALERT_XML, screen="ScanMeterActivity")
        jev_state = self.compressor.to_jev_state(result, goal="Acknowledge alert and proceed")
        self.assertIn("goal", jev_state)
        self.assertIn("visible_options", jev_state)
        # Verify minimal structure (< 500 characters)
        import json
        dumped = json.dumps(jev_state)
        self.assertLess(len(dumped), 500)

if __name__ == "__main__":
    unittest.main()
