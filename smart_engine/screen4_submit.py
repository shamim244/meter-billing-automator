"""
screen4_submit.py – Screen 4: NBPDCL Final Submission & Stage-Only Safety Gate.
"""
import os
import sys
import time
import subprocess
import uiautomator2 as u2

class Screen4Submit:
    def __init__(self, device=None, serial="192.168.9.40:5555"):
        self.d = device or u2.connect(serial)
        self.serial = serial

    def handle_final_submit(self, do_submit=False, timeout=10.0):
        if not do_submit:
            print("\n[*] [Screen 4] [STAGE-ONLY MODE] Bill is filled and validated on device.")
            print("  [*] Skipping final NBPDCL submit as requested (Safe Mode).")
            print("  [*] Resetting to ConsumerSearchActivity for next consumer...")
            subprocess.run([
                "adb", "-s", self.serial, "shell",
                "am start -n in.phoenix.bpdcl/in.phoenix.bpdcl.ConsumerSearchActivity --activity-clear-top"
            ], capture_output=True)
            time.sleep(0.5)
            return True

        print("\n[*] [Screen 4] Executing Final NBPDCL Bill Generation...")
        # 1. Scroll to bottom of BillingManual
        self.d.swipe(540, 1800, 540, 400)
        time.sleep(0.4)
        self.d.swipe(540, 1800, 540, 400)
        time.sleep(0.4)

        # 2. Tap Submit button
        submit_btn = self.d(resourceId="in.phoenix.bpdcl:id/Submit")
        if submit_btn.exists(timeout=2.0):
            print("  [*] Tapping NBPDCL Submit button...")
            submit_btn.click()
        else:
            self.d.click(293, 2267)

        time.sleep(0.8)

        # 3. Confirm YES on Alert dialog
        yes_btn = self.d(resourceId="android:id/button1")
        if yes_btn.exists(timeout=2.0) and "YES" in yes_btn.get_text():
            print("  [+] Confirming YES on Bill Generation Dialog...")
            yes_btn.click()
        else:
            self.d.click(900, 1388)

        # 4. Wait for BillPrintOnline1
        t_start = time.time()
        print_ready = False
        while time.time() - t_start < timeout:
            act = self.d.app_current().get("activity", "")
            if "BillPrint" in act or "Print" in act:
                print_ready = True
                break
            time.sleep(0.4)

        if print_ready:
            print("  [+] Bill Print Screen loaded! Returning to Search...")
            time.sleep(0.6)
            self.d.swipe(540, 2000, 540, 300)
            time.sleep(0.4)
            back_btn = self.d(resourceId="in.phoenix.bpdcl:id/printback")
            if back_btn.exists(timeout=1.5):
                back_btn.click()
            else:
                self.d.click(718, 2305)
            time.sleep(0.8)

        print("\n>>> [SUCCESS] Consumer Billed & Submitted in NBPDCL! <<<\n")
        return True

if __name__ == "__main__":
    s4 = Screen4Submit()
    s4.handle_final_submit(do_submit=False)
