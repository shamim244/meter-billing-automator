"""
test_telemetry.py – Unit tests for TelemetryManager SQLite and JSON logging.
"""
import os
import json
import tempfile
import unittest
from smart_engine.telemetry import TelemetryManager

class TestTelemetryManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_telemetry.sqlite")
        self.tm = TelemetryManager(db_path=self.db_path)

    def tearDown(self):
        self.tm.close()
        self.temp_dir.cleanup()

    def test_start_and_finish_trace(self):
        trace_id = self.tm.start_trace(
            ca_number="102303575593",
            mru="18",
            cycle="NOV-2026",
            device_serial="192.168.9.40:5555",
            screen_resolution="1080x2400",
            meter_type="NORMAL",
            base_kwh=45
        )
        self.assertIsNotNone(trace_id)

        # Log interactions
        self.tm.log_interaction(
            trace_id=trace_id,
            step_num=1,
            screen_name="Screen 1",
            activity="ConsumerSearchActivity",
            action_name="tap_search_button",
            coord_x=450,
            coord_y=726,
            ratio_x=0.416,
            ratio_y=0.302,
            how_method="cached_tap",
            duration_ms=115,
            status="SUCCESS"
        )

        self.tm.log_interaction(
            trace_id=trace_id,
            step_num=2,
            screen_name="Screen 3",
            activity="MeterReadingActivity",
            action_name="camera_shutter",
            coord_x=794,
            coord_y=2256,
            ratio_x=0.735,
            ratio_y=0.940,
            how_method="cached_tap",
            duration_ms=1450,
            status="ALERT_INTERCEPTED",
            alert_message="Please move AWAY from meter to capture!"
        )

        self.tm.finish_trace(
            trace_id=trace_id,
            final_reading=2636,
            overall_status="submitted",
            total_duration_ms=5420
        )

        # Verify dataset export
        dataset = self.tm.export_dataset(cycle="NOV-2026")
        self.assertEqual(len(dataset), 1)
        trace = dataset[0]
        self.assertEqual(trace["ca_number"], "102303575593")
        self.assertEqual(trace["final_reading"], 2636)
        self.assertEqual(trace["overall_status"], "submitted")
        self.assertEqual(len(trace["interactions"]), 2)
        self.assertEqual(trace["interactions"][0]["action_name"], "tap_search_button")
        self.assertEqual(trace["interactions"][1]["status"], "ALERT_INTERCEPTED")
        self.assertEqual(trace["interactions"][1]["alert_message"], "Please move AWAY from meter to capture!")

    def test_json_and_jsonl_export(self):
        t1 = self.tm.start_trace(ca_number="1001", cycle="NOV-2026", meter_type="NORMAL")
        self.tm.log_interaction(t1, 1, "Screen 1", "Search", "search", 400, 700, 0.4, 0.3)
        self.tm.finish_trace(t1, 1500, "submitted", 2100)

        t2 = self.tm.start_trace(ca_number="1002", cycle="NOV-2026", meter_type="DEFECTIVE")
        self.tm.log_interaction(t2, 1, "Screen 1", "Search", "search", 400, 700, 0.4, 0.3)
        self.tm.finish_trace(t2, 0, "submitted", 3400)

        json_path = os.path.join(self.temp_dir.name, "out.json")
        jsonl_path = os.path.join(self.temp_dir.name, "out.jsonl")

        count_json = self.tm.export_json(json_path)
        count_jsonl = self.tm.export_jsonl(jsonl_path)

        self.assertEqual(count_json, 2)
        self.assertEqual(count_jsonl, 2)

        # Validate JSON content
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]["ca_number"], "1001")

        # Validate JSONL content
        with open(jsonl_path, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
            self.assertEqual(len(lines), 2)
            self.assertEqual(lines[1]["ca_number"], "1002")

    def test_summary_metrics(self):
        t1 = self.tm.start_trace(ca_number="2001", cycle="OCT-2026")
        self.tm.finish_trace(t1, 100, "submitted", 4000)

        t2 = self.tm.start_trace(ca_number="2002", cycle="OCT-2026")
        self.tm.finish_trace(t2, None, "failed", 1500)

        summary = self.tm.get_summary()
        self.assertEqual(summary["total_traces"], 2)
        self.assertEqual(summary["status_counts"]["submitted"], 1)
        self.assertEqual(summary["status_counts"]["failed"], 1)

    def test_resilience_on_none_trace(self):
        # Should not raise exception
        self.tm.log_interaction(None, 1, "Screen", "Act", "click")
        self.tm.finish_trace(None)

if __name__ == "__main__":
    unittest.main()
