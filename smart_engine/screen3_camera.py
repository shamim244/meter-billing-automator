"""
screen3_camera.py – Screen 3: High-Speed MR Bharat Camera & Review Controller (in.coral.bpdcl).
Captures photo, enters reading, resolves secondary popup, and overrides doubt alerts.
Features a stabilized camera retry loop, alert recovery, and race condition watcher.
"""
import os
import sys
import time
import uiautomator2 as u2

class Screen3Camera:
    def __init__(self, device=None, serial="192.168.9.40:5555"):
        self.d = device or u2.connect(serial)
        self.serial = serial

    def handle_camera_and_review(self, reading_kwh=1355, timeout=30.0):
        t0 = time.time()
        print(f"\n[*] [Screen 3] MR Bharat: Fast Camera & Reading Entry ({reading_kwh} KWH)...")

        # 1. If on MeterReadingActivity with CAPTURE button, click it
        pre_capture = self.d(resourceId="in.coral.bpdcl:id/capture_readings_btn")
        if pre_capture.exists(timeout=0.3):
            print("  [1] Tapping initial CAPTURE button...")
            try:
                pre_capture.click()
            except Exception:
                pass

        # 2. Trigger Camera Shutter & Wait for Reading Input Dialog (up to 5 attempts)
        input_field = self.d(resourceId="in.coral.bpdcl:id/input")
        input_found = False

        for attempt in range(1, 6):
            print(f"  [2] Camera Capture Attempt {attempt}/5...")
            try:
                shutter = self.d(resourceId="in.coral.bpdcl:id/captureImg")
                shutter_text = self.d(text="CAPTURE")
                if shutter.wait(timeout=1.5):
                    shutter.click()
                elif shutter_text.exists(timeout=0.3):
                    shutter_text.click()
                else:
                    self.d.shell("input tap 794 2256")
            except Exception:
                self.d.shell("input tap 794 2256")

            # Wait up to 3.5s for input dialog or alert
            t_cap = time.time()
            while time.time() - t_cap < 3.5:
                try:
                    if input_field.exists(timeout=0.1):
                        input_found = True
                        break

                    alert = self.d(resourceId="in.coral.bpdcl:id/alertTitle")
                    alert_std = self.d(resourceId="android:id/alertTitle")
                    if alert.exists(timeout=0.05) or alert_std.exists(timeout=0.05):
                        msg_node = self.d(resourceId="android:id/message")
                        msg = (msg_node.get_text() or "") if msg_node.exists(timeout=0.05) else ""
                        print(f"  [!] Camera alert detected: '{msg}'")

                        if "previously saved" in msg.lower():
                            print("  [+] Accepting previously saved meter reading (tapping Yes)...")
                            yes_btn = self.d(resourceId="android:id/button1")
                            if yes_btn.exists(timeout=0.2):
                                yes_btn.click()
                            else:
                                self.d.shell("input tap 870 1389; input keyevent 66")
                            input_found = True
                            break
                        else:
                            print("  [*] Dismissing alert and allowing camera sensor to stabilize (1.2s)...")
                            ok_btn = self.d(resourceId="android:id/button1")
                            if ok_btn.exists(timeout=0.2):
                                ok_btn.click()
                            elif self.d(text="OK").exists(timeout=0.2):
                                self.d(text="OK").click()
                            else:
                                self.d.shell("input keyevent 66")

                            # Sensor stabilization delay: Allow camera focus & ML model to re-arm
                            time.sleep(1.2)
                            break
                except Exception:
                    time.sleep(0.1)

                time.sleep(0.08)

            if input_found:
                break

        # Check if already in MeterReadingActivity review screen or wait for input
        in_review = False
        try:
            cur = self.d.app_current()
            in_review = "MeterReadingActivity" in (cur.get("activity", "") or "")
        except Exception:
            pass

        if not input_found and not in_review:
            try:
                if not input_field.wait(timeout=2.0):
                    print("  [!] Reading input field not found after camera retries!")
                    return False
            except Exception:
                pass

        # 3. Enter Reading and Save if input field is present
        try:
            has_input = input_field.exists(timeout=0.2)
        except Exception:
            has_input = False

        if has_input:
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
            try:
                input_field.set_text(str(reading_kwh))
            except Exception:
                self.d.shell(f"input text {reading_kwh}")
            
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

            try:
                save_btn = self.d(text="Save")
                if save_btn.wait(timeout=1.5):
                    print("  [*] Tapping Save button...")
                    save_btn.click()
                else:
                    btn1 = self.d(resourceId="android:id/button1")
                    if btn1.exists(timeout=0.5):
                        btn1.click()
                    else:
                        self.d.shell("input tap 870 1389")
            except Exception:
                self.d.shell("input tap 870 1389")

        # 4. Multi-dialog Race Condition Watcher
        print("  [4] Watching for popups, revalidation alerts, and BillingManual return...")
        t_loop = time.time()
        revalidation_handled = False
        billing_ps = self.d(resourceId="in.phoenix.bpdcl:id/PresentStatus1")
        billing_cam = self.d(resourceId="in.phoenix.bpdcl:id/KwhCaptureButton")

        while time.time() - t_loop < timeout:
            # Check for BillingManual return (u2 element check with shell fallback)
            try:
                if billing_ps.exists(timeout=0.03) or billing_cam.exists(timeout=0.03):
                    print(f"\n>>> [SUCCESS] Screen 3 Complete: Returned to BillingManual in {round(time.time() - t0, 2)}s! <<<")
                    return True
            except Exception:
                pass

            try:
                out = self.d.shell("dumpsys window | grep mCurrentFocus")
                focus_text = out[0] if isinstance(out, tuple) else getattr(out, 'output', str(out))
                if "BillingManual" in focus_text:
                    print(f"\n>>> [SUCCESS] Screen 3 Complete: Returned to BillingManual in {round(time.time() - t0, 2)}s! <<<")
                    return True
            except Exception:
                pass

            # Check for generic dialog confirmation button (button1: OK / Submit / Yes / Confirm)
            try:
                sec_submit = self.d(resourceId="android:id/button1")
                sec_title = self.d(resourceId="in.coral.bpdcl:id/dialog_title_text")
                if sec_submit.exists(timeout=0.05) or sec_title.exists(timeout=0.05):
                    btn_text = (sec_submit.get_text() or "Submit").strip()
                    print(f"  [+] Confirmation popup detected ('{btn_text}')! Tapping button...")
                    sec_submit.click_exists(timeout=0.3)
                    t_loop = time.time()
                    time.sleep(0.2)
                    continue
            except Exception:
                pass

            # Check for Revalidation / Doubt warning
            if not revalidation_handled:
                try:
                    reval_btn = self.d(resourceId="in.coral.bpdcl:id/revalidate_btn")
                    if reval_btn.exists(timeout=0.05):
                        print("  [*] Revalidation required! Executing dynamic override sequence...")
                        reval_btn.click()
                        rep_btn = self.d(resourceId="in.coral.bpdcl:id/btn_report")
                        if rep_btn.wait(timeout=2.0):
                            rep_btn.click()
                        correct_opt = self.d(text="Readings are correct")
                        if correct_opt.wait(timeout=2.0):
                            print("  [*] Selected 'Readings are correct' remark.")
                            correct_opt.click()
                        # Final submit inside MR Bharat
                        submit_btn = self.d(resourceId="in.coral.bpdcl:id/submit_btn")
                        if submit_btn.wait(timeout=2.0):
                            print("  [*] Tapping final Submit in MR Bharat...")
                            submit_btn.click()
                        else:
                            print("  [*] Fallback tap for MR Bharat submit (792, 2231)...")
                            self.d.click(792, 2231)
                        revalidation_handled = True
                        t_loop = time.time()
                        time.sleep(0.5)
                        continue
                except Exception:
                    pass

            # Direct Submit or Save & Validate Later button in MR Bharat review screen
            try:
                submit_btn = self.d(resourceId="in.coral.bpdcl:id/submit_btn")
                save_later_btn = self.d(resourceId="in.coral.bpdcl:id/save_readings_main_btn")
                if submit_btn.click_exists(timeout=0.1):
                    print("  [*] Tapping direct Submit in MR Bharat...")
                    t_loop = time.time()
                    time.sleep(0.4)
                    continue
                elif save_later_btn.click_exists(timeout=0.1):
                    print("  [*] Tapping 'Save Readings and Validate Later' in MR Bharat...")
                    t_loop = time.time()
                    time.sleep(0.4)
                    continue
            except Exception:
                pass

            time.sleep(0.1)

            time.sleep(0.1)

        print("  [!] Timed out in MR Bharat review/submit stage.")
        return False

if __name__ == "__main__":
    reading = int(sys.argv[1]) if len(sys.argv) > 1 else 1355
    s3 = Screen3Camera()
    ok = s3.handle_camera_and_review(reading_kwh=reading)
    sys.exit(0 if ok else 1)
