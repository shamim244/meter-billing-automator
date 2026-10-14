"""
screen1_search.py – Screen 1: Consumer Search Controller (ConsumerSearchActivity).
"""
import os
import sys
import time
import subprocess
import uiautomator2 as u2

class Screen1Search:
    def __init__(self, device=None, serial="192.168.9.40:5555"):
        self.d = device or u2.connect(serial)
        self.serial = serial

    def search_consumer(self, ca_number, timeout=8.0):
        print(f"\n[*] [Screen 1] Searching Consumer CA: {ca_number}...")
        self.d.screen_on()

        # 1. Start clean ConsumerSearchActivity
        subprocess.run([
            "adb", "-s", self.serial, "shell",
            "am start -n in.phoenix.bpdcl/in.phoenix.bpdcl.ConsumerSearchActivity --activity-clear-top"
        ], capture_output=True)
        time.sleep(0.4)

        # 2. Dismiss keyboard
        self.d.press("back")
        time.sleep(0.2)

        # 3. Type CA number into bh_AccNo1search
        input_field = self.d(resourceId="in.phoenix.bpdcl:id/bh_AccNo1search")
        if input_field.exists(timeout=2.0):
            input_field.click()
            time.sleep(0.2)
            input_field.set_text(str(ca_number))
        else:
            subprocess.run(["adb", "-s", self.serial, "shell", f"input tap 727 543; input text {ca_number}"], capture_output=True)

        time.sleep(0.2)
        self.d.press("back")  # Dismiss keyboard

        # 4. Click Search button
        search_btn = self.d(resourceId="in.phoenix.bpdcl:id/cons_search")
        if search_btn.exists(timeout=1.0):
            search_btn.click()
        else:
            subprocess.run(["adb", "-s", self.serial, "shell", "input tap 450 726"], capture_output=True)

        # 5. Wait for BillingManual
        t_start = time.time()
        while time.time() - t_start < timeout:
            act = self.d.app_current().get("activity", "")
            if "BillingManual" in act:
                print("  [+] BillingManual reached! Waiting 1.1s for GPS settlement...")
                time.sleep(1.1)
                return True

            # Detect error alerts (e.g. invalid data or consumer not found)
            alert = self.d(resourceId="android:id/alertTitle")
            if alert.exists(timeout=0.1):
                msg = self.d(resourceId="android:id/message").get_text() if self.d(resourceId="android:id/message").exists() else ""
                print(f"  [!] Alert detected: '{alert.get_text()}' - '{msg}'")
                self.d(resourceId="android:id/button1").click_exists(timeout=0.5)
                return False

            time.sleep(0.3)

        print("  [!] Failed to reach BillingManual within timeout.")
        return False

if __name__ == "__main__":
    ca = sys.argv[1] if len(sys.argv) > 1 else "10230047179"
    s1 = Screen1Search()
    ok = s1.search_consumer(ca)
    sys.exit(0 if ok else 1)
