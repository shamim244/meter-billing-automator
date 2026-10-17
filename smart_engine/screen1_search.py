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
            self.d.shell("svc power stayon true")
        except Exception:
            pass

        # Dismiss any lingering alerts from previous screen
        old_alert = self.d(resourceId="android:id/button1")
        if old_alert.exists(timeout=0.1):
            try:
                old_alert.click()
            except Exception:
                pass

        # 1. Clean return to ConsumerSearchActivity
        self.d.shell("am start -n in.phoenix.bpdcl/in.phoenix.bpdcl.ConsumerSearchActivity --activity-clear-top")

        # 2. Enter CA number into bh_AccNo1search
        input_field = self.d(resourceId="in.phoenix.bpdcl:id/bh_AccNo1search")
        if input_field.wait(timeout=1.5):
            try:
                input_field.clear_text()
            except Exception:
                pass
            input_field.set_text(str(ca_number))
        else:
            dpad_del = " ".join(["67"] * 25)
            self.d.shell(f"input tap 727 543; input keyevent 123 {dpad_del}; input text {ca_number}")

        # 3. Immediately click Search button
        search_btn = self.d(resourceId="in.phoenix.bpdcl:id/cons_search")
        if not search_btn.click_exists(timeout=0.1):
            self.d.shell("input keyevent 4; input tap 450 726")

        # 3. Dynamic Event Loop: Wait for BillingManual OR Alert popup
        # Uses direct element inspection (30ms) instead of expensive app_current dumpsys (1500ms)
        t_start = time.time()
        ps_btn = self.d(resourceId="in.phoenix.bpdcl:id/PresentStatus1")
        alert = self.d(resourceId="android:id/alertTitle")

        while time.time() - t_start < timeout:
            if ps_btn.exists(timeout=0.05):
                time.sleep(0.3)
                print(f"  [+] BillingManual reached and settled in {round(time.time() - t_start, 2)}s!")
                return True

            if alert.exists(timeout=0.05):
                title = alert.get_text() if alert.exists() else "Alert"
                msg_elem = self.d(resourceId="android:id/message")
                msg = msg_elem.get_text() if msg_elem.exists() else ""
                print(f"  [!] Alert detected: '{title}' - '{msg}'")
                btn1 = self.d(resourceId="android:id/button1")
                if btn1.exists(timeout=0.3):
                    btn1.click()
                return False

            time.sleep(0.05)

        print("  [!] Failed to reach BillingManual within timeout.")
        return False

if __name__ == "__main__":
    ca = sys.argv[1] if len(sys.argv) > 1 else "10230047179"
    s1 = Screen1Search()
    ok = s1.search_consumer(ca)
    sys.exit(0 if ok else 1)
