"""
screen1_search.py – Screen 1: High-Speed Consumer Search Controller (ConsumerSearchActivity).
Uses direct am start, keyboard suppression, and dynamic event polling for BillingManual and alerts.
"""
import os
import sys
import time
import uiautomator2 as u2

class Screen1Search:
    def __init__(self, device=None, serial="192.168.9.40:5555"):
        self.d = device or u2.connect(serial)
        self.serial = serial

    def search_consumer(self, ca_number, timeout=8.0):
        print(f"\n[*] [Screen 1] Fast Searching Consumer CA: {ca_number}...")
        try:
            self.d.screen_on()
        except Exception:
            pass

        # 1. Start clean ConsumerSearchActivity directly
        self.d.shell("am start -n in.phoenix.bpdcl/in.phoenix.bpdcl.ConsumerSearchActivity --activity-clear-top")

        # 2. Enter CA number into bh_AccNo1search
        input_field = self.d(resourceId="in.phoenix.bpdcl:id/bh_AccNo1search")
        if input_field.wait(timeout=2.0):
            input_field.set_text(str(ca_number))
        else:
            self.d.shell(f"input tap 727 543; input text {ca_number}")

        # 3. Immediately click Search button (zero-sleep, no redundant XML dumps)
        search_btn = self.d(resourceId="in.phoenix.bpdcl:id/cons_search")
        if not search_btn.click_exists(timeout=0.1):
            # Fast fallback: dismiss keyboard (if active) and tap coordinates (450, 726)
            self.d.shell("input keyevent 4; input tap 450 726")

        # 4. Dynamic Event Loop: Wait for BillingManual OR Alert popup
        t_start = time.time()
        while time.time() - t_start < timeout:
            # Check for error / warning alerts first
            alert = self.d(resourceId="android:id/alertTitle")
            if alert.exists(timeout=0.05):
                title = alert.get_text() if alert.exists() else "Alert"
                msg_elem = self.d(resourceId="android:id/message")
                msg = msg_elem.get_text() if msg_elem.exists() else ""
                print(f"  [!] Alert detected: '{title}' - '{msg}'")
                btn1 = self.d(resourceId="android:id/button1")
                if btn1.exists(timeout=0.5):
                    btn1.click()
                return False

            # Check if BillingManual is reached (via activity name or PresentStatus1)
            act = ""
            try:
                act = self.d.app_current().get("activity", "")
            except Exception:
                pass

            ps_btn = self.d(resourceId="in.phoenix.bpdcl:id/PresentStatus1")
            if "BillingManual" in act or ps_btn.exists(timeout=0.05):
                print(f"  [+] BillingManual reached and ready in {round(time.time() - t_start, 2)}s!")
                return True

            time.sleep(0.08)

        print("  [!] Failed to reach BillingManual within timeout.")
        return False

if __name__ == "__main__":
    ca = sys.argv[1] if len(sys.argv) > 1 else "10230047179"
    s1 = Screen1Search()
    ok = s1.search_consumer(ca)
    sys.exit(0 if ok else 1)
