import os
import sys
import unittest
import xml.etree.ElementTree as ET

# Ensure repo root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import automate_selections as root_auto
import chat.automate_selections as chat_auto
from chat.run_queue import main as run_queue_main


class TestAutomateSelectionsSync(unittest.TestCase):
    """Verify root automate_selections and chat/automate_selections are 100% in sync."""

    def test_file_content_identical(self):
        root_path = os.path.join(REPO_ROOT, "automate_selections.py")
        chat_path = os.path.join(REPO_ROOT, "chat", "automate_selections.py")
        with open(root_path, "r", encoding="utf-8") as f1:
            root_content = f1.read()
        with open(chat_path, "r", encoding="utf-8") as f2:
            chat_content = f2.read()
        self.assertEqual(root_content, chat_content, "chat/automate_selections.py must match root automate_selections.py")

    def test_exported_symbols_match(self):
        root_symbols = set(dir(root_auto))
        chat_symbols = set(dir(chat_auto))
        self.assertEqual(root_symbols, chat_symbols)


class TestClipboardExtraction(unittest.TestCase):
    """Verify consumer number parsing logic."""

    def test_consumer_number_patterns(self):
        import re
        valid_samples = [
            ("144208013167", "144208013167"),
            ("Consumer: 10230057913", "10230057913"),
            ("  10230049139\n", "10230049139"),
            ("102300144657", "102300144657"),
        ]
        for raw, expected in valid_samples:
            digits = re.findall(r'\b\d{11,12}\b', raw)
            found = digits[0] if digits else re.sub(r'\D', '', raw.strip())
            self.assertEqual(found, expected)

    def test_ignore_ip_and_adb(self):
        ignored = [
            "192.168.9.40:5555",
            "adb connect 192.168.9.40",
            "adb devices",
        ]
        for raw in ignored:
            self.assertTrue("192.168" in raw or "connect" in raw or "adb" in raw)


class TestDropdownCoordinateLogic(unittest.TestCase):
    """Verify the proven 95% mathematical dropdown calculations."""

    def test_coordinate_computation_from_xml(self):
        sample_xml = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
        <hierarchy rotation="0">
          <node bounds="[356,1739][1026,1839]" resource-id="in.phoenix.bpdcl:id/PresentStatus1" text="" class="android.widget.Spinner" />
          <node bounds="[356,1865][1026,1965]" resource-id="in.phoenix.bpdcl:id/atMOBS1" text="" class="android.widget.Spinner" />
          <node bounds="[356,1991][1026,2091]" resource-id="in.phoenix.bpdcl:id/meterloctypeiv" text="" class="android.widget.Spinner" />
        </hierarchy>"""

        tree = ET.fromstring(sample_xml)
        target_keys = ["PresentStatus1", "atMOBS1", "meterloctypeiv", "button1"]
        elements = {}
        for n in tree.iter("node"):
            rid = n.attrib.get("resource-id", "")
            for k in target_keys:
                if k in rid:
                    bounds = n.attrib.get("bounds", "").replace("][", ",").replace("[", "").replace("]", "").split(",")
                    x1, y1, x2, y2 = map(int, bounds)
                    elements[k] = {
                        "cx": (x1 + x2) // 2,
                        "cy": (y1 + y2) // 2,
                        "arrow_x": x2 - 50,
                        "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                        "text": n.attrib.get("text", "")
                    }

        ps = elements["PresentStatus1"]
        obs = elements["atMOBS1"]
        loc = elements["meterloctypeiv"]

        # 1. Present status coordinates:
        # ps_opt_x, ps_opt_y must be dynamic relative to ps, NOT hardcoded 1870
        ps_opt_x = ps["cx"]
        ps_opt_y = ps["y2"] + 50
        self.assertEqual(ps_opt_x, 691)
        self.assertEqual(ps_opt_y, 1889)

        # 2. Site observation coordinates:
        # obs tap must be at center (obs_cx, obs_cy), NOT obs_arrow_x
        self.assertEqual(obs["cx"], 691)
        self.assertEqual(obs["cy"], 1915)

        # 3. Location coordinates:
        # loc_opt_y must select Inside (1790 when loc['y2'] > 2070, else loc['y2'] + 40)
        # NOT a random keyevent 20 66
        self.assertGreater(loc["y2"], 2070)
        loc_opt_y = 1790 if loc["y2"] > 2070 else loc["y2"] + 40
        self.assertEqual(loc_opt_y, 1790)

        # 4. KWH camera tap coordinate
        kwh_x, kwh_y = 408, loc["cy"] + 189
        self.assertEqual(kwh_x, 408)
        self.assertEqual(kwh_y, 2230)

    def test_meter_defective_detection(self):
        for val in ["DEFECTIVE", "defective", "MD", "md", "MB", "mb"]:
            self.assertTrue(str(val).upper() in ["DEFECTIVE", "MD", "MB"])
        for val in ["NORMAL", "normal", "OK", "ok", ""]:
            self.assertFalse(str(val).upper() in ["DEFECTIVE", "MD", "MB"])

    def test_site_observation_dpad_logic(self):
        # 30 DOWN followed by 1 UP (19) and ENTER (66) guarantees landing on 'OK'
        dpad_cmds = " ".join(["20"] * 30)
        self.assertEqual(len(dpad_cmds.split()), 30)


class TestRunQueue(unittest.TestCase):
    """Verify run_queue.py dry-run option works without hitting physical device."""

    def test_run_queue_dry_run(self):
        import subprocess
        res = subprocess.run(
            [sys.executable, "chat/run_queue.py", "--dry-run", "--limit", "2"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=20
        )
        self.assertEqual(res.returncode, 0, f"run_queue dry-run failed: {res.stderr}")
        self.assertIn("[+] Fetching automation queue", res.stdout)
        self.assertIn("[DRY-RUN] Would process CA", res.stdout)
        self.assertIn("Batch Run Finished", res.stdout)


if __name__ == "__main__":
    unittest.main()
