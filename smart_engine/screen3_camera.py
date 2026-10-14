"""
screen3_camera.py – Screen 3: MR Bharat Camera & Review Controller (in.coral.bpdcl).
Captures photo, enters reading, resolves secondary popup, and overrides doubt alerts.
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
        print(f"\n[*] [Screen 3] MR Bharat: Camera & Reading Entry ({reading_kwh} KWH)...")

        # 1. If on MeterReadingActivity with CAPTURE button, click it
        pre_capture = self.d(resourceId="in.coral.bpdcl:id/capture_readings_btn")
        if pre_capture.exists(timeout=2.0):
            print("  [1] Tapping initial CAPTURE button...")
            pre_capture.click()
            time.sleep(0.8)

        # 2. On ScanMeterActivity: Trigger Shutter
        print("  [2] Triggering Camera Shutter (captureImg)...")
        shutter = self.d(resourceId="in.coral.bpdcl:id/captureImg")
        if shutter.exists(timeout=3.0):
            shutter.click()
        else:
            self.d.click(794, 2256)

        time.sleep(1.0)

        # 3. Reading Input Dialog
        print(f"  [3] Waiting for reading input dialog to enter {reading_kwh}...")
        input_field = self.d(resourceId="in.coral.bpdcl:id/input")
        if input_field.exists(timeout=5.0):
            input_field.set_text(str(reading_kwh))
            time.sleep(0.3)
            save_btn = self.d(text="Save")
            if save_btn.exists(timeout=1.5):
                print("  [*] Tapping Save button...")
                save_btn.click()
            else:
                self.d.click(870, 1389)
        else:
            print("  [!] Reading input field not found!")
            return False

        time.sleep(0.8)

        # 4. Secondary Confirmation Popup ("Electro Mechanical Meter" / "All required parameters")
        print("  [4] Checking for secondary confirmation popup...")
        sec_submit = self.d(text="Submit")
        sec_title = self.d(resourceId="in.coral.bpdcl:id/dialog_title_text")
        if sec_title.exists(timeout=2.0) or sec_submit.exists(timeout=2.0):
            print(f"  [+] Secondary popup detected! Tapping Submit...")
            sec_submit.click_exists(timeout=1.5)
            time.sleep(0.8)

        # 5. Review Screen & Revalidation Override (The Doubt Resolver)
        print("  [5] Review stage: Checking for Revalidation / Doubt warning...")
        reval_btn = self.d(resourceId="in.coral.bpdcl:id/revalidate_btn")
        if reval_btn.exists(timeout=3.0):
            print("  [*] Revalidation required! Executing dynamic override sequence...")
            reval_btn.click()
            time.sleep(0.5)

            report_btn = self.d(resourceId="in.coral.bpdcl:id/btn_report")
            if report_btn.exists(timeout=2.0):
                report_btn.click()
                time.sleep(0.4)

            correct_opt = self.d(text="Readings are correct")
            if correct_opt.exists(timeout=2.0):
                print("  [*] Selected 'Readings are correct' remark.")
                correct_opt.click()
                time.sleep(0.4)

            # Final submit inside MR Bharat
            submit_btn = self.d(resourceId="in.coral.bpdcl:id/submit_btn")
            if submit_btn.exists(timeout=2.0):
                print("  [*] Tapping final Submit in MR Bharat...")
                submit_btn.click()
        else:
            # Direct submit if no revalidation required
            submit_btn = self.d(resourceId="in.coral.bpdcl:id/submit_btn")
            if submit_btn.exists(timeout=2.0):
                print("  [*] Tapping direct Submit in MR Bharat...")
                submit_btn.click()

        # 6. Verify return to NBPDCL BillingManual
        print("  [6] Waiting for return to NBPDCL BillingManual...")
        t_start = time.time()
        while time.time() - t_start < timeout:
            cur_act = self.d.app_current().get("activity", "")
            if "BillingManual" in cur_act:
                print(f"\n>>> [SUCCESS] Screen 3 Complete: Returned to BillingManual in {round(time.time() - t_start, 2)}s! <<<\n")
                return True
            time.sleep(0.3)

        print("  [!] Failed to return to BillingManual.")
        return False

if __name__ == "__main__":
    s3 = Screen3Camera()
    ok = s3.handle_camera_and_review(1355)
    sys.exit(0 if ok else 1)
