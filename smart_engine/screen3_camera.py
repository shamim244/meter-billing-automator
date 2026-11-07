"""
screen3_camera.py – Screen 3: High-Speed MR Bharat Camera & Review Controller (in.coral.bpdcl).
Captures photo, enters reading, resolves secondary popup, and overrides doubt alerts.
Uses universal coordinate caching, non-blocking element waiters, and an event-driven watcher to minimize latency.
"""
import os
import sys
import time
import uiautomator2 as u2
from smart_engine.device import resolve_device_serial
from smart_engine.ui_cache import UniversalUICache, fast_get_current_activity
from smart_engine.telemetry import TelemetryManager

class Screen3Camera:
    def __init__(self, device=None, serial=None):
        if not device:
            serial = resolve_device_serial(serial)
        self.d = device or u2.connect(serial)
        self.serial = serial
        self.cache = UniversalUICache.get_instance()
        self.telemetry = TelemetryManager.get_instance()

    def handle_camera_and_review(self, reading_kwh=1355, timeout=25.0, trace_id=None):
        t0 = time.time()
        print(f"\n[*] [Screen 3] MR Bharat: Fast Camera & Reading Entry ({reading_kwh} KWH)...")

        w, h = self.cache.get_resolution(self.d)

        # 1. If on MeterReadingActivity with CAPTURE button, click it
        pre_capture = self.d(resourceId="in.coral.bpdcl:id/capture_readings_btn")
        if pre_capture.exists(timeout=0.3):
            print("  [1] Tapping initial CAPTURE button...")
            pre_capture.click()
            self.telemetry.log_interaction(
                trace_id=trace_id,
                step_num=8,
                screen_name="Screen 3",
                activity="MeterReadingActivity",
                action_name="tap_initial_capture_btn",
                duration_ms=int((time.time() - t0) * 1000),
                status="SUCCESS"
            )

        # 2. Trigger Camera Shutter & Wait for Reading Input Dialog
        input_field = self.d(resourceId="in.coral.bpdcl:id/input")
        input_found = False

        for attempt in range(1, 4):
            t_shutter0 = time.time()
            print(f"  [2] Camera Capture Attempt {attempt}/3...")
            shutter = self.d(resourceId="in.coral.bpdcl:id/captureImg")
            clicked = self.cache.tap("screen3.shutter", self.d, selector_obj=shutter, fallback_coords=(794, 2256))
            if not clicked:
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

            rx, ry = round(794 / w, 3), round(2256 / h, 3)

            # Wait up to 3.5s for input dialog or alert
            t_cap = time.time()
            alert_msg = ""
            while time.time() - t_cap < 3.5:
                if input_field.exists(timeout=0.1):
                    input_found = True
                    self.telemetry.log_interaction(
                        trace_id=trace_id,
                        step_num=9,
                        screen_name="Screen 3",
                        activity="ScanMeterActivity",
                        action_name=f"camera_shutter_attempt_{attempt}",
                        coord_x=794,
                        coord_y=2256,
                        ratio_x=rx,
                        ratio_y=ry,
                        how_method="cached_tap" if clicked else "fallback",
                        duration_ms=int((time.time() - t_shutter0) * 1000),
                        status="SUCCESS"
                    )
                    break

                # Check if alert appeared
                alert = self.d(resourceId="in.coral.bpdcl:id/alertTitle")
                if alert.exists(timeout=0.05):
                    msg = self.d(resourceId="android:id/message").get_text() if self.d(resourceId="android:id/message").exists() else ""
                    print(f"  [!] Camera alert detected: '{msg}'")
                    alert_msg = msg
                    if "previously saved" in msg.lower():
                        print("  [+] Accepting previously saved meter reading (tapping Yes)...")
                        self.d(resourceId="android:id/button1").click_exists(timeout=0.5)
                        input_found = True
                        self.telemetry.log_interaction(
                            trace_id=trace_id,
                            step_num=9,
                            screen_name="Screen 3",
                            activity="ScanMeterActivity",
                            action_name=f"camera_shutter_attempt_{attempt}",
                            coord_x=794,
                            coord_y=2256,
                            ratio_x=rx,
                            ratio_y=ry,
                            duration_ms=int((time.time() - t_shutter0) * 1000),
                            status="POPUP_ACCEPTED",
                            alert_message=msg
                        )
                        break
                    else:
                        print("  [*] Dismissing alert and retrying shutter...")
                        self.d(resourceId="android:id/button1").click_exists(timeout=0.5)
                        self.d(resourceId="in.coral.bpdcl:id/flash_switch").click_exists(timeout=0.3)
                        self.telemetry.log_interaction(
                            trace_id=trace_id,
                            step_num=9,
                            screen_name="Screen 3",
                            activity="ScanMeterActivity",
                            action_name=f"camera_shutter_attempt_{attempt}",
                            coord_x=794,
                            coord_y=2256,
                            ratio_x=rx,
                            ratio_y=ry,
                            duration_ms=int((time.time() - t_shutter0) * 1000),
                            status="ALERT_INTERCEPTED",
                            alert_message=msg
                        )
                        break
                time.sleep(0.1)

            if input_found:
                break

        # Check if already in MeterReadingActivity review screen or wait for input
        _, cur_act = fast_get_current_activity(self.d)
        in_review = "MeterReadingActivity" in cur_act
        if not input_found and not in_review and not input_field.wait(timeout=2.0):
            print("  [!] Reading input field not found after camera retries!")
            self.telemetry.log_interaction(
                trace_id=trace_id,
                step_num=10,
                screen_name="Screen 3",
                activity=cur_act,
                action_name="reading_input_missing",
                duration_ms=int((time.time() - t0) * 1000),
                status="FAILED",
                alert_message="Input field missing after camera retries"
            )
            return False

        # 3. Enter Reading and Save if input field is present
        if input_field.exists(timeout=0.2):
            t_inj0 = time.time()
            print(f"  [3] Injecting KWH Reading: {reading_kwh}...")
            try:
                input_field.click()
                time.sleep(0.1)
            except Exception:
                pass

            # Inject the correct reading directly via set_text
            input_field.set_text(str(reading_kwh))
            
            # Dismiss soft keyboard if present
            try:
                self.d.press("back")
                time.sleep(0.1)
            except Exception:
                pass

            save_btn = self.d(text="Save")
            print("  [*] Tapping Save button...")
            saved = self.cache.tap("screen3.save_btn", self.d, selector_obj=save_btn, fallback_coords=(870, 1389))
            if not saved:
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

            self.telemetry.log_interaction(
                trace_id=trace_id,
                step_num=10,
                screen_name="Screen 3",
                activity="MeterReadingActivity",
                action_name="inject_and_save_reading",
                coord_x=870,
                coord_y=1389,
                ratio_x=round(870 / w, 3),
                ratio_y=round(1389 / h, 3),
                duration_ms=int((time.time() - t_inj0) * 1000),
                status="SUCCESS",
                prefill_state=str(reading_kwh)
            )

        # 4. Multi-dialog Race Condition Watcher
        print("  [4] Watching for popups, revalidation alerts, and BillingManual return...")
        t_loop = time.time()
        revalidation_handled = False

        while time.time() - t_loop < timeout:
            # Check fast activity check first
            pkg, act = fast_get_current_activity(self.d)
            if "BillingManual" in act or ("in.phoenix.bpdcl" in pkg and "coral" not in pkg):
                elapsed = round(time.time() - t0, 2)
                print(f"\n>>> [SUCCESS] Screen 3 Complete: Returned to BillingManual in {elapsed}s! <<<")
                self.telemetry.log_interaction(
                    trace_id=trace_id,
                    step_num=11,
                    screen_name="Screen 3",
                    activity="BillingManual",
                    action_name="return_to_billing_manual",
                    duration_ms=int(elapsed * 1000),
                    status="SUCCESS"
                )
                return True

            # Check for generic dialog confirmation button (button1: OK / Submit / Yes / Confirm)
            sec_submit = self.d(resourceId="android:id/button1")
            sec_title = self.d(resourceId="in.coral.bpdcl:id/dialog_title_text")
            if sec_submit.exists(timeout=0.08) or sec_title.exists(timeout=0.08):
                btn_text = (sec_submit.get_text() or "Submit").strip()
                print(f"  [+] Confirmation popup detected ('{btn_text}')! Tapping button...")
                sec_submit.click_exists(timeout=0.5)
                self.telemetry.log_interaction(
                    trace_id=trace_id,
                    step_num=11,
                    screen_name="Screen 3",
                    activity="MeterReadingActivity",
                    action_name="confirm_popup_submit",
                    duration_ms=int((time.time() - t_loop) * 1000),
                    status="SUCCESS",
                    alert_message=btn_text
                )
                t_loop = time.time()
                time.sleep(0.2)
                continue

            # Check for Revalidation / Doubt warning
            if not revalidation_handled:
                try:
                    reval_btn = self.d(resourceId="in.coral.bpdcl:id/revalidate_btn")
                    if reval_btn.exists(timeout=0.05):
                        t_rev0 = time.time()
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
                        if not self.cache.tap("screen3.submit_btn", self.d, selector_obj=submit_btn, fallback_coords=(792, 2231)):
                            if not submit_btn.click_exists(timeout=2.0):
                                print("  [*] Fallback tap for MR Bharat submit (792, 2231)...")
                                self.d.click(792, 2231)
                        revalidation_handled = True
                        self.telemetry.log_interaction(
                            trace_id=trace_id,
                            step_num=11,
                            screen_name="Screen 3",
                            activity="MeterReadingActivity",
                            action_name="revalidation_override",
                            coord_x=792,
                            coord_y=2231,
                            ratio_x=round(792 / w, 3),
                            ratio_y=round(2231 / h, 3),
                            duration_ms=int((time.time() - t_rev0) * 1000),
                            status="OVERRIDE_EXECUTED",
                            alert_message="Readings are correct"
                        )
                        t_loop = time.time()
                        time.sleep(0.3)
                        continue
                except Exception as e_rev:
                    print(f"  [!] Revalidation sequence exception: {e_rev}")

            # Direct Submit or Save & Validate Later button in MR Bharat review screen
            submit_btn = self.d(resourceId="in.coral.bpdcl:id/submit_btn")
            save_later_btn = self.d(resourceId="in.coral.bpdcl:id/save_readings_main_btn")
            if submit_btn.click_exists(timeout=0.1):
                print("  [*] Tapping direct Submit in MR Bharat...")
                t_loop = time.time()
                time.sleep(0.3)
                continue
            elif save_later_btn.click_exists(timeout=0.1):
                print("  [*] Tapping 'Save Readings and Validate Later' in MR Bharat...")
                t_loop = time.time()
                time.sleep(0.3)
                continue

            time.sleep(0.08)

        print("  [!] Timed out in MR Bharat review/submit stage.")
        self.telemetry.log_interaction(
            trace_id=trace_id,
            step_num=11,
            screen_name="Screen 3",
            activity="MeterReadingActivity",
            action_name="review_timeout",
            duration_ms=int((time.time() - t0) * 1000),
            status="TIMEOUT",
            alert_message="Timed out in MR Bharat review stage"
        )
        return False

    def handle_defective_camera(self, timeout=20.0, trace_id=None):
        t0 = time.time()
        print("\n[*] [Screen 3] MR Bharat: Fast Defective Meter Workflow (Defective/Burnt)...")

        w, h = self.cache.get_resolution(self.d)

        # 1. Wait for Coral MeterReadingActivity (up to 4.0s)
        t_wait = time.time()
        while time.time() - t_wait < 4.0:
            pkg, act = fast_get_current_activity(self.d)
            if "MeterReadingActivity" in act or self.d(resourceId="in.coral.bpdcl:id/rdbtn_defective").exists(timeout=0.08):
                break
            time.sleep(0.08)

        # 2. Select Defective/Burnt radio button (3rd option)
        print("  [1] Selecting 'Defective/Burnt' radio button...")
        defective_radio = self.d(resourceId="in.coral.bpdcl:id/rdbtn_defective")
        if not self.cache.tap("screen3.defective_radio", self.d, selector_obj=defective_radio, fallback_coords=(822, 591)):
            if not defective_radio.click_exists(timeout=1.0):
                if not self.d(textContains="Defective").click_exists(timeout=0.5):
                    self.d.click(822, 591)

        self.telemetry.log_interaction(
            trace_id=trace_id,
            step_num=8,
            screen_name="Screen 3",
            activity="MeterReadingActivity",
            action_name="select_defective_radio",
            coord_x=822,
            coord_y=591,
            ratio_x=round(822 / w, 3),
            ratio_y=round(591 / h, 3),
            status="SUCCESS",
            prefill_state="Defective/Burnt"
        )
        time.sleep(0.2)

        # 3. Select 'Actually Defective' from Abnormalities popup
        print("  [2] Selecting 'Actually Defective' from Abnormalities...")
        act_def = self.d(text="Actually Defective")
        if not self.cache.tap("screen3.actually_defective", self.d, selector_obj=act_def, fallback_coords=(563, 405)):
            if not act_def.click_exists(timeout=1.5):
                if not self.d(textContains="Actually Defective").click_exists(timeout=0.5):
                    self.d.click(563, 405)

        self.telemetry.log_interaction(
            trace_id=trace_id,
            step_num=9,
            screen_name="Screen 3",
            activity="MeterReadingActivity",
            action_name="select_actually_defective_abnormality",
            coord_x=563,
            coord_y=405,
            ratio_x=round(563 / w, 3),
            ratio_y=round(405 / h, 3),
            status="SUCCESS"
        )
        time.sleep(0.2)

        # 4. Tap 'TAKE PHOTO' button
        print("  [3] Tapping 'TAKE PHOTO' button...")
        take_btn = self.d(resourceId="in.coral.bpdcl:id/take_pic_btn")
        if not self.cache.tap("screen3.take_photo", self.d, selector_obj=take_btn, fallback_coords=(540, 762)):
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
                shutter_clicked = self.cache.tap("screen3.defective_shutter", self.d, selector_obj=shutter, fallback_coords=(540, 2313))
                if not shutter_clicked:
                    shutter.click_exists(timeout=0.5)
                    shutter_clicked = True
                print("  [+] Camera shutter captured!")
                break
            time.sleep(0.08)

        if not shutter_clicked:
            print("  [*] Fallback tap for camera shutter (540, 2313)...")
            self.d.click(540, 2313)

        self.telemetry.log_interaction(
            trace_id=trace_id,
            step_num=10,
            screen_name="Screen 3",
            activity="CapturePhotoActivity",
            action_name="defective_camera_shutter",
            coord_x=540,
            coord_y=2313,
            ratio_x=round(540 / w, 3),
            ratio_y=round(2313 / h, 3),
            duration_ms=int((time.time() - t_cam) * 1000),
            status="SUCCESS"
        )
        time.sleep(0.3)

        # 6. Return to MeterReadingActivity review & Tap Coral Submit
        print("  [5] Tapping final Submit in MR Bharat review...")
        t_rev = time.time()
        while time.time() - t_rev < timeout:
            # Check if returned to BillingManual
            pkg, act = fast_get_current_activity(self.d)
            if "BillingManual" in act or ("in.phoenix.bpdcl" in pkg and "coral" not in pkg):
                elapsed = round(time.time() - t0, 2)
                print(f"\n>>> [SUCCESS] Screen 3 Complete (Defective): Returned to BillingManual in {elapsed}s! <<<")
                self.telemetry.log_interaction(
                    trace_id=trace_id,
                    step_num=11,
                    screen_name="Screen 3",
                    activity="BillingManual",
                    action_name="return_to_billing_manual_defective",
                    duration_ms=int(elapsed * 1000),
                    status="SUCCESS"
                )
                return True

            # Check for generic dialog confirmation button
            sec_submit = self.d(resourceId="android:id/button1")
            if sec_submit.exists(timeout=0.1):
                btn_text = (sec_submit.get_text() or "Submit").strip()
                print(f"  [+] Confirmation popup detected ('{btn_text}')! Tapping button...")
                sec_submit.click_exists(timeout=0.5)
                time.sleep(0.2)
                continue

            # Tap Submit in MR Bharat review
            submit_btn = self.d(resourceId="in.coral.bpdcl:id/submit_btn")
            if not self.cache.tap("screen3.defective_submit", self.d, selector_obj=submit_btn, fallback_coords=(792, 2231)):
                if submit_btn.click_exists(timeout=0.2):
                    print("  [*] Tapped Submit in MR Bharat review...")
                    time.sleep(0.3)
                    continue
                else:
                    self.d.click(792, 2231)

            time.sleep(0.08)

        print("  [!] Timed out in Defective MR Bharat submit stage.")
        return False

if __name__ == "__main__":
    reading = int(sys.argv[1]) if len(sys.argv) > 1 else 1355
    s3 = Screen3Camera()
    ok = s3.handle_camera_and_review(reading_kwh=reading)
    sys.exit(0 if ok else 1)
