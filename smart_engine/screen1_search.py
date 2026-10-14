"""
screen1_search.py – Screen 1: High-Speed Consumer Search Controller (ConsumerSearchActivity).
Uses Fast IME and event-driven activity/element waiters to eliminate idle latency.
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

        # 1. Start clean ConsumerSearchActivity via direct socket
        try:
            self.d.app_start("in.phoenix.bpdcl", ".ConsumerSearchActivity", stop=False)
        except Exception:
            # Fallback if app_start fails
            self.d.shell("am start -n in.phoenix.bpdcl/in.phoenix.bpdcl.ConsumerSearchActivity --activity-clear-top")

        # 2. Enable Fast IME to prevent on-screen keyboard from popping up
        try:
            self.d.set_fastinput_ime(True)
        except Exception:
            pass

        # 3. Enter CA number into bh_AccNo1search
        input_field = self.d(resourceId="in.phoenix.bpdcl:id/bh_AccNo1search")
        if input_field.wait(timeout=2.5):
            input_field.set_text(str(ca_number))
        else:
            # Direct shell input tap fallback
            self.d.shell(f"input tap 727 543; input text {ca_number}")

        # 4. Click Search button
        search_btn = self.d(resourceId="in.phoenix.bpdcl:id/cons_search")
        if search_btn.wait(timeout=1.5):
            search_btn.click()
        else:
            self.d.shell("input tap 450 726")

        # 5. Event-driven wait for BillingManual
        t_start = time.time()
        # First check with fast wait_activity
        if self.d.wait_activity(".BillingManual", timeout=timeout):
            # Wait for form readiness (PresentStatus1 loaded)
            ps_btn = self.d(resourceId="in.phoenix.bpdcl:id/PresentStatus1")
            if ps_btn.wait(timeout=3.0):
                print(f"  [+] BillingManual reached and ready in {round(time.time() - t_start, 2)}s!")
                return True
            print("  [+] BillingManual activity reached (ready).")
            return True

        # Check for alert errors if wait_activity timed out
        alert = self.d(resourceId="android:id/alertTitle")
        if alert.exists(timeout=0.2):
            msg = self.d(resourceId="android:id/message").get_text() if self.d(resourceId="android:id/message").exists() else ""
            print(f"  [!] Alert detected: '{alert.get_text()}' - '{msg}'")
            self.d(resourceId="android:id/button1").click_exists(timeout=0.5)
            return False

        print("  [!] Failed to reach BillingManual within timeout.")
        return False

if __name__ == "__main__":
    ca = sys.argv[1] if len(sys.argv) > 1 else "10230047179"
    s1 = Screen1Search()
    ok = s1.search_consumer(ca)
    sys.exit(0 if ok else 1)
