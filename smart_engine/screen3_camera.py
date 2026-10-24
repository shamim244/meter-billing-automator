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

    def handle_camera_and_review(self, reading_kwh=1355, timeout=25.0):
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
            clicked = False
            try:
                if shutter.wait(timeout=1.0):
                    shutter.click()
                    clicked = True
            except Exception:
                clicked = False

            if not clicked:
                try:
                    self.d.click(794, 2256)
                except Exception:
                    pass

            # Wait up to 3.5s for input dialog or alert
            t_cap = time.time()
            while time.time() - t_cap < 3.5:
                if input_field.exists(timeout=0.1):
                    input_found = True
                    break

                # Check if alert appeared
                alert = self.d(resourceId="in.coral.bpdcl:id/alertTitle")
                if alert.exists(timeout=0.05):
                    msg = self.d(resourceId="android:id/message").get_text() if self.d(resourceId="android:id/message").exists() else ""
                    print(f"  [!] Camera alert detected: '{msg}'")
                    if "previously saved" in msg.lower():
                        print("  [+] Accepting previously saved meter reading (tapping Yes)...")
                        self.d(resourceId="android:id/button1").click_exists(timeout=0.5)
                        input_found = True
                        break
                    else:
                        print("  [*] Dismissing alert and retrying shutter...")
                        self.d(resourceId="android:id/button1").click_exists(timeout=0.5)
                        self.d(resourceId="in.coral.bpdcl:id/flash_switch").click_exists(timeout=0.3)
                        break
                time.sleep(0.1)

            if input_found:
                break

        # Check if already in MeterReadingActivity review screen or wait for input
        in_review = "MeterReadingActivity" in (self.d.app_current().get("activity", "") or "")
        if not input_found and not in_review and not input_field.wait(timeout=2.0):
            print("  [!] Reading input field not found after camera retries!")
            return False

        # 3. Enter Reading and Save if input field is present
        if input_field.exists(timeout=0.2):
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
            print("  [*] Tapping Save button...")
            saved = False
            try:
                if save_btn.wait(timeout=1.5):
                    save_btn.click()
                    saved = True
            except Exception:
                saved = False

            if not saved:
                try:
                    if not self.d(resourceId="android:id/button1").click_exists(timeout=0.5):
                        self.d.click(870, 1389)
                except Exception:
                    pass

        # 4. Multi-dialog Race Condition Watcher
        print("  [4] Watching for popups, revalidation alerts, and BillingManual return...")
        t_loop = time.time()
        revalidation_handled = False

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

            # Check for generic dialog confirmation button (button1: OK / Submit / Yes / Confirm)
            sec_submit = self.d(resourceId="android:id/button1")
            sec_title = self.d(resourceId="in.coral.bpdcl:id/dialog_title_text")
            if sec_submit.exists(timeout=0.08) or sec_title.exists(timeout=0.08):
                btn_text = (sec_submit.get_text() or "Submit").strip()
                print(f"  [+] Confirmation popup detected ('{btn_text}')! Tapping button...")
                sec_submit.click_exists(timeout=0.5)
                t_loop = time.time()
                time.sleep(0.3)
                continue

            # Check for Revalidation / Doubt warning
            if not revalidation_handled:
                try:
                    reval_btn = self.d(resourceId="in.coral.bpdcl:id/revalidate_btn")
                    if reval_btn.exists(timeout=0.05):
                        print("  [*] Revalidation required! Executing dynamic override sequence...")
                        reval_btn.click_exists(timeout=1.0)
                        rep_btn = self.d(resourceId="in.coral.bpdcl:id/btn_report")
                        if rep_btn.exists(timeout=2.0):
                            rep_btn.click_exists(timeout=1.0)
                        correct_opt = self.d(text="Readings are correct")
                        if correct_opt.exists(timeout=2.0):
                            print("  [*] Selected 'Readings are correct' remark.")
                            correct_opt.click_exists(timeout=1.0)
                        # Final submit inside MR Bharat
                        submit_btn = self.d(resourceId="in.coral.bpdcl:id/submit_btn")
                        if not submit_btn.click_exists(timeout=2.0):
                            print("  [*] Fallback tap for MR Bharat submit (792, 2231)...")
                            self.d.click(792, 2231)
                        revalidation_handled = True
                        t_loop = time.time()
                        time.sleep(0.5)
                        continue
                except Exception as e_rev:
                    print(f"  [!] Revalidation sequence exception: {e_rev}")

            # Direct Submit or Save & Validate Later button in MR Bharat review screen
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

            time.sleep(0.1)

        print("  [!] Timed out in MR Bharat review/submit stage.")
        return False

    def handle_defective_camera(self, timeout=20.0):
        t0 = time.time()
        print("\n[*] [Screen 3] MR Bharat: Fast Defective Meter Workflow (Defective/Burnt)...")

        # 1. Wait for Coral MeterReadingActivity (up to 4.0s)
        t_wait = time.time()
        while time.time() - t_wait < 4.0:
            act = ""
            try:
                act = self.d.app_current().get("activity", "")
            except Exception:
                pass
            if "MeterReadingActivity" in act or self.d(resourceId="in.coral.bpdcl:id/rdbtn_defective").exists(timeout=0.08):
                break
            time.sleep(0.1)

        # 2. Select Defective/Burnt radio button (3rd option)
        print("  [1] Selecting 'Defective/Burnt' radio button...")
        defective_radio = self.d(resourceId="in.coral.bpdcl:id/rdbtn_defective")
        if not defective_radio.click_exists(timeout=1.0):
            if not self.d(textContains="Defective").click_exists(timeout=0.5):
                self.d.click(822, 591)
        time.sleep(0.3)

        # 3. Select 'Actually Defective' from Abnormalities popup
        print("  [2] Selecting 'Actually Defective' from Abnormalities...")
        act_def = self.d(text="Actually Defective")
        if not act_def.click_exists(timeout=1.5):
            if not self.d(textContains="Actually Defective").click_exists(timeout=0.5):
                self.d.click(563, 405)
        time.sleep(0.3)

        # 4. Tap 'TAKE PHOTO' button
        print("  [3] Tapping 'TAKE PHOTO' button...")
        take_btn = self.d(resourceId="in.coral.bpdcl:id/take_pic_btn")
        if not take_btn.click_exists(timeout=1.0):
            if not self.d(text="TAKE PHOTO").click_exists(timeout=0.5):
                self.d.click(540, 762)

        # 5. Wait for Camera Viewfinder (CapturePhotoActivity) & Trigger Shutter
        print("  [4] Waiting for camera shutter in CapturePhotoActivity...")
        t_cam = time.time()
        shutter_clicked = False
        while time.time() - t_cam < 8.0:
            shutter = self.d(resourceId="in.coral.bpdcl:id/captureImageBtn")
            if shutter.exists(timeout=0.1):
                shutter.click_exists(timeout=0.5)
                shutter_clicked = True
                print("  [+] Camera shutter captured!")
                break
            time.sleep(0.1)

        if not shutter_clicked:
            print("  [*] Fallback tap for camera shutter (540, 2313)...")
            self.d.click(540, 2313)

        time.sleep(0.5)

        # 6. Return to MeterReadingActivity review & Tap Coral Submit
        print("  [5] Tapping final Submit in MR Bharat review...")
        t_rev = time.time()
        while time.time() - t_rev < timeout:
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
                print(f"\n>>> [SUCCESS] Screen 3 Complete (Defective): Returned to BillingManual in {round(time.time() - t0, 2)}s! <<<")
                return True

            # Check for generic dialog confirmation button
            sec_submit = self.d(resourceId="android:id/button1")
            if sec_submit.exists(timeout=0.1):
                btn_text = (sec_submit.get_text() or "Submit").strip()
                print(f"  [+] Confirmation popup detected ('{btn_text}')! Tapping button...")
                sec_submit.click_exists(timeout=0.5)
                time.sleep(0.3)
                continue

            # Tap Submit in MR Bharat review
            submit_btn = self.d(resourceId="in.coral.bpdcl:id/submit_btn")
            if submit_btn.click_exists(timeout=0.2):
                print("  [*] Tapped Submit in MR Bharat review...")
                time.sleep(0.4)
                continue
            else:
                self.d.click(792, 2231)

            time.sleep(0.1)

        print("  [!] Timed out in Defective MR Bharat submit stage.")
        return False

if __name__ == "__main__":
    reading = int(sys.argv[1]) if len(sys.argv) > 1 else 1355
    s3 = Screen3Camera()
    ok = s3.handle_camera_and_review(reading_kwh=reading)
    sys.exit(0 if ok else 1)
