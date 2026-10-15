"""
screen3_camera.py – Screen 3: High-Speed MR Bharat Camera & Review Controller (in.coral.bpdcl).
Captures photo, enters reading, resolves secondary popup, and overrides doubt alerts.
Uses non-blocking element waiters and an event-driven race condition watcher to minimize latency.
"""
import os
import sys
import time
import uiautomator2 as u2

class Screen3Camera:
    def __init__(self, device=None, serial="192.168.9.40:5555"):
        self.d = device or u2.connect(serial)
        self.serial = serial

    def handle_camera_and_review(self, reading_kwh=1355, timeout=12.0):
        t0 = time.time()
        print(f"\n[*] [Screen 3] MR Bharat: Fast Camera & Reading Entry ({reading_kwh} KWH)...")

        # 1. If on MeterReadingActivity with CAPTURE button, click it
        pre_capture = self.d(resourceId="in.coral.bpdcl:id/capture_readings_btn")
        if pre_capture.exists(timeout=0.3):
            print("  [1] Tapping initial CAPTURE button...")
            pre_capture.click()

        # 2. Trigger Camera Shutter & Wait for Reading Input Dialog
        input_field = self.d(resourceId="in.coral.bpdcl:id/input")
        input_found = False

        for attempt in range(1, 4):
            print(f"  [2] Camera Capture Attempt {attempt}/3...")
            shutter = self.d(resourceId="in.coral.bpdcl:id/captureImg")
            if shutter.wait(timeout=2.0):
                shutter.click()
            else:
                self.d.click(794, 2256)

            # Wait up to 3.5s for input dialog or alert
            t_cap = time.time()
            while time.time() - t_cap < 3.5:
                if input_field.exists(timeout=0.1):
                    input_found = True
                    break

                # Check if 'Invalid Image' or 'Please capture clear' alert appeared
                alert = self.d(resourceId="in.coral.bpdcl:id/alertTitle")
                if alert.exists(timeout=0.05):
                    msg = self.d(resourceId="android:id/message").get_text() if self.d(resourceId="android:id/message").exists() else ""
                    print(f"  [!] Camera alert detected: '{msg}'. Dismissing and retrying...")
                    self.d(resourceId="android:id/button1").click_exists(timeout=0.5)
                    # Turn on flash on retry
                    self.d(resourceId="in.coral.bpdcl:id/flash_switch").click_exists(timeout=0.3)
                    break
                time.sleep(0.1)

            if input_found:
                break

        if not input_found and not input_field.wait(timeout=2.0):
            print("  [!] Reading input field not found after camera retries!")
            return False

        # 3. Enter Reading and Save (Clear all existing text first)
        print(f"  [3] Injecting KWH Reading: {reading_kwh}...")
        try:
            input_field.click()
            time.sleep(0.15)
        except Exception:
            pass

        # Select all and clear existing text / OCR residue
        try:
            input_field.clear_text()
        except Exception:
            pass

        # Send explicit backspaces to ensure field is 100% clean
        dpad_del = " ".join(["67"] * 20)
        self.d.shell(f"input keyevent 123 {dpad_del}")

        # Inject the correct reading
        input_field.set_text(str(reading_kwh))
        
        # Verify text was entered; fallback to shell input if needed
        try:
            curr_text = input_field.get_text()
            if not curr_text or curr_text != str(reading_kwh):
                self.d.shell(f"input text {reading_kwh}")
        except Exception:
            pass

        # Dismiss soft keyboard so Save button is not obscured
        try:
            self.d.press("back")
            time.sleep(0.15)
        except Exception:
            pass

        save_btn = self.d(text="Save")
        if save_btn.wait(timeout=1.5):
            print("  [*] Tapping Save button...")
            save_btn.click()
        else:
            self.d(resourceId="android:id/button1").click_exists(timeout=0.5)

        # 4. Multi-dialog Race Condition Watcher
        print("  [4] Watching for popups, revalidation alerts, and BillingManual return...")
        t_loop = time.time()
        revalidation_handled = False
        secondary_handled = False

        while time.time() - t_loop < timeout:
            # Check if returned to BillingManual
            act = ""
            pkg = ""
            try:
                cur = self.d.app_current()
                act = cur.get("activity", "")
                pkg = cur.get("package", "")
            except Exception:
                pass

            if "BillingManual" in act or ("in.phoenix.bpdcl" in pkg and "coral" not in pkg):
                print(f"\n>>> [SUCCESS] Screen 3 Complete: Returned to BillingManual in {round(time.time() - t0, 2)}s! <<<")
                return True

            # Check for Secondary Confirmation Popup ("Electro Mechanical Meter")
            if not secondary_handled:
                sec_title = self.d(resourceId="in.coral.bpdcl:id/dialog_title_text")
                sec_submit = self.d(text="Submit")
                if sec_title.exists(timeout=0.05) or sec_submit.exists(timeout=0.05):
                    print("  [+] Secondary confirmation popup detected! Tapping Submit...")
                    sec_submit.click_exists(timeout=0.5)
                    secondary_handled = True
                    time.sleep(0.1)
                    continue

            # Check for Revalidation / Doubt warning
            if not revalidation_handled:
                reval_btn = self.d(resourceId="in.coral.bpdcl:id/revalidate_btn")
                if reval_btn.exists(timeout=0.05):
                    print("  [*] Revalidation required! Executing dynamic override sequence...")
                    reval_btn.click()
                    rep_btn = self.d(resourceId="in.coral.bpdcl:id/btn_report")
                    if rep_btn.wait(timeout=1.5):
                        rep_btn.click()
                    correct_opt = self.d(text="Readings are correct")
                    if correct_opt.wait(timeout=1.5):
                        print("  [*] Selected 'Readings are correct' remark.")
                        correct_opt.click()
                    # Final submit inside MR Bharat
                    submit_btn = self.d(resourceId="in.coral.bpdcl:id/submit_btn")
                    if submit_btn.wait(timeout=1.5):
                        print("  [*] Tapping final Submit in MR Bharat...")
                        submit_btn.click()
                    revalidation_handled = True
                    time.sleep(0.1)
                    continue

            # Direct Submit button in MR Bharat review screen
            submit_btn = self.d(resourceId="in.coral.bpdcl:id/submit_btn")
            if submit_btn.exists(timeout=0.05):
                print("  [*] Tapping direct Submit in MR Bharat...")
                submit_btn.click()
                time.sleep(0.2)
                continue

            time.sleep(0.08)

        print("  [!] Timed out in MR Bharat review/submit stage.")
        return False

if __name__ == "__main__":
    reading = int(sys.argv[1]) if len(sys.argv) > 1 else 1355
    s3 = Screen3Camera()
    ok = s3.handle_camera_and_review(reading_kwh=reading)
    sys.exit(0 if ok else 1)
