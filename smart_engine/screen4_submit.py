"""
screen4_submit.py – Screen 4: NBPDCL Final Submission & Stage-Only Safety Gate.
Optimized for zero-subprocess resets and fast activity navigation.
"""
import os
import sys
import time
import uiautomator2 as u2

class Screen4Submit:
    def __init__(self, device=None, serial="192.168.9.40:5555"):
        self.d = device or u2.connect(serial)
        self.serial = serial

    def handle_final_submit(self, do_submit=False, timeout=10.0):
        if not do_submit:
            print("\n[*] [Screen 4] [STAGE-ONLY MODE] Bill is filled and validated on device.")
            print("  [*] Skipping final NBPDCL submit as requested (Safe Mode).")
            print("  [*] Fast resetting to ConsumerSearchActivity for next consumer...")
            try:
                self.d.app_start("in.phoenix.bpdcl", ".ConsumerSearchActivity", stop=False)
            except Exception:
                self.d.shell("am start -n in.phoenix.bpdcl/in.phoenix.bpdcl.ConsumerSearchActivity --activity-clear-top")
            return True

        print("\n[*] [Screen 4] Executing Final NBPDCL Bill Generation...")
        # 1. Scroll to bottom of BillingManual
        self.d.swipe(540, 1800, 540, 400)
        time.sleep(0.2)
        self.d.swipe(540, 1800, 540, 400)
        time.sleep(0.2)

        # 2. Tap Submit button
        submit_btn = self.d(resourceId="in.phoenix.bpdcl:id/Submit")
        if submit_btn.wait(timeout=2.0):
            print("  [*] Tapping NBPDCL Submit button...")
            submit_btn.click()
        else:
            self.d.click(293, 2267)

        # 3. Confirm YES on Alert dialog
        yes_btn = self.d(resourceId="android:id/button1")
        if yes_btn.wait(timeout=2.0) and "YES" in (yes_btn.get_text() or "").upper():
            print("  [+] Confirming YES on Bill Generation Dialog...")
            yes_btn.click()
        else:
            self.d.click(900, 1388)

        # 4. Fast Wait for BillPrintOnline1 screen (zero dumpsys overhead)
        t_start = time.time()
        print_ready = False
        back_btn = self.d(resourceId="in.phoenix.bpdcl:id/printback")

        while time.time() - t_start < timeout:
            if back_btn.exists(timeout=0.05) or self.d(textContains="Print").exists(timeout=0.05):
                print_ready = True
                break
            time.sleep(0.08)

        if print_ready:
            print("  [+] Bill Print Screen loaded! Returning to Search...")
            self.d.swipe(540, 2000, 540, 300)
            back_btn = self.d(resourceId="in.phoenix.bpdcl:id/printback")
            if back_btn.wait(timeout=1.5):
                back_btn.click()
            else:
                self.d.click(718, 2305)
            time.sleep(0.3)

        # Always ensure device returns to ConsumerSearchActivity for next batch item
        try:
            self.d.app_start("in.phoenix.bpdcl", ".ConsumerSearchActivity", stop=False)
        except Exception:
            self.d.shell("am start -n in.phoenix.bpdcl/in.phoenix.bpdcl.ConsumerSearchActivity --activity-clear-top")

        print("\n>>> [SUCCESS] Consumer Billed & Submitted in NBPDCL! <<<\n")
        return True

if __name__ == "__main__":
    s4 = Screen4Submit()
    s4.handle_final_submit(do_submit=False)
