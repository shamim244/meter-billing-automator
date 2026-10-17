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
        time.sleep(0.3)

        # 2. Enter CA number into bh_AccNo1search with strict sanitization
        input_field = self.d(resourceId="in.phoenix.bpdcl:id/bh_AccNo1search")
        if input_field.wait(timeout=2.0):
            try:
                input_field.click()
                time.sleep(0.1)
                input_field.clear_text()
            except Exception:
                pass

            # Send backspaces to erase any stale digits
            dpad_del = " ".join(["67"] * 25)
            self.d.shell(f"input keyevent 123 {dpad_del}")
            time.sleep(0.1)

            input_field.set_text(str(ca_number))
            time.sleep(0.15)

            # Verification check: Ensure input matches ca_number exactly
            try:
                entered = input_field.get_text()
                if entered != str(ca_number):
                    # Fallback input via shell
                    self.d.shell(f"input keyevent 123 {dpad_del}; input text {ca_number}")
            except Exception:
                pass
        else:
            dpad_del = " ".join(["67"] * 25)
            self.d.shell(f"input tap 727 543; input keyevent 123 {dpad_del}; input text {ca_number}")

        # Hide soft keyboard so Search button is never obscured
        try:
            self.d.press("back")
            time.sleep(0.15)
        except Exception:
            pass

        # 3. Click Search button
        search_btn = self.d(resourceId="in.phoenix.bpdcl:id/cons_search")
        if not search_btn.click_exists(timeout=0.5):
            self.d.shell("input tap 450 726")

        # 4. Dynamic Event Loop: Wait for BillingManual OR Alert popup
        # Direct element inspection for speed and stability
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
                if btn1.wait(timeout=0.5):
                    btn1.click()
                elif self.d(text="OK").exists:
                    self.d(text="OK").click()
                return False

            time.sleep(0.08)

        print("  [!] Failed to reach BillingManual within timeout.")
        return False

if __name__ == "__main__":
    ca = sys.argv[1] if len(sys.argv) > 1 else "10230047179"
    s1 = Screen1Search()
    ok = s1.search_consumer(ca)
    sys.exit(0 if ok else 1)
