"""
screen2_form.py – Screen 2: High-Speed BillingManual Form Controller.
Selects Meter Reading Status, Site Observation, and Location, then launches MR Bharat.
Uses universal coordinate caching, single-pass reads, direct socket shell keyevents, and zero static sleeps.
"""
import os
import sys
import time
import uiautomator2 as u2
from smart_engine.device import resolve_device_serial
from smart_engine.ui_cache import UniversalUICache, fast_get_current_activity
from smart_engine.telemetry import TelemetryManager

class Screen2Form:
    def __init__(self, device=None, serial=None):
        if not device:
            serial = resolve_device_serial(serial)
        self.d = device or u2.connect(serial)
        self.serial = serial
        self.cache = UniversalUICache.get_instance()
        self.telemetry = TelemetryManager.get_instance()

    def fill_form_and_launch_camera(self, meter_type="NORMAL", timeout=8.0, trace_id=None):
        t_start = time.time()
        print("\n[*] [Screen 2] Fast Filling BillingManual Form...")
        is_defective = (str(meter_type).upper() == "DEFECTIVE")
        target_status = "Meter Defective" if is_defective else "NORMAL"

        # 1. Select Present Status
        t0 = time.time()
        print(f"  [1] Selecting Present Status: {target_status}...")
        ps_btn = self.d(resourceId="in.phoenix.bpdcl:id/PresentStatus1")
        if not (ps_btn.exists(timeout=0.05) or ps_btn.wait(timeout=2.5)):
            print("  [!] PresentStatus1 not found!")
            self.telemetry.log_interaction(
                trace_id=trace_id,
                step_num=4,
                screen_name="Screen 2",
                activity="BillingManual",
                action_name="select_present_status",
                duration_ms=int((time.time() - t0) * 1000),
                status="FAILED",
                alert_message="PresentStatus1 not found"
            )
            return False

        ps_btn.click()
        status_sel = self.d(text=target_status)
        if not status_sel.click_exists(timeout=0.4):
            if not self.d(text="METER DEFECTIVE").click_exists(timeout=0.2):
                self.d(textContains="DEFECTIVE" if is_defective else "NORMAL").click_exists(timeout=0.2)

        self.telemetry.log_interaction(
            trace_id=trace_id,
            step_num=4,
            screen_name="Screen 2",
            activity="BillingManual",
            action_name="select_present_status",
            duration_ms=int((time.time() - t0) * 1000),
            status="SUCCESS",
            prefill_state=target_status
        )

        # 2. Select Site Observation with smart prefill bypass
        t0 = time.time()
        target_obs = "DEFECTIVE" if is_defective else "OK"
        obs_btn = self.d(resourceId="in.phoenix.bpdcl:id/atMOBS1")
        try:
            obs_text = obs_btn.get_text()
        except Exception:
            obs_text = ""

        if obs_text == target_obs:
            print(f"  [2] Site Observation already prefilled with '{target_obs}' – Fast-path bypass!")
            self.telemetry.log_interaction(
                trace_id=trace_id,
                step_num=5,
                screen_name="Screen 2",
                activity="BillingManual",
                action_name="select_site_observation",
                how_method="bypass_prefilled",
                duration_ms=int((time.time() - t0) * 1000),
                status="SUCCESS",
                prefill_state=f"bypassed_{target_obs}"
            )
        else:
            print(f"  [2] Selecting Site Observation: {target_obs}...")
            if not obs_btn.click_exists(timeout=0.3):
                self.d.shell("input tap 691 1942")

            if is_defective:
                def_sel = self.d(text="DEFECTIVE")
                if not def_sel.click_exists(timeout=0.4):
                    if not self.d(textContains="DEFECTIVE").click_exists(timeout=0.2):
                        # DPAD down to bottom (DEFECTIVE is last of 6 options) and press enter
                        dpad = " ".join(["20"] * 30)
                        self.d.shell(f"input keyevent --delay 2 {dpad} 66")
            else:
                # Fast DPAD sequence via direct socket shell (delay 2ms)
                dpad = " ".join(["20"] * 30)
                self.d.shell(f"input keyevent --delay 2 {dpad} 19 66")

            self.telemetry.log_interaction(
                trace_id=trace_id,
                step_num=5,
                screen_name="Screen 2",
                activity="BillingManual",
                action_name="select_site_observation",
                how_method="dpad_keyevent",
                duration_ms=int((time.time() - t0) * 1000),
                status="SUCCESS",
                prefill_state=f"selected_{target_obs}"
            )

        # 3. Select Meter Location Type (Inside) with smart prefill bypass
        t0 = time.time()
        loc_btn = self.d(resourceId="in.phoenix.bpdcl:id/meterloctypeiv")
        try:
            loc_text = loc_btn.get_text()
        except Exception:
            loc_text = ""

        if loc_text == "Inside":
            print("  [3] Meter Location already prefilled with 'Inside' – Fast-path bypass!")
            self.telemetry.log_interaction(
                trace_id=trace_id,
                step_num=6,
                screen_name="Screen 2",
                activity="BillingManual",
                action_name="select_meter_location",
                how_method="bypass_prefilled",
                duration_ms=int((time.time() - t0) * 1000),
                status="SUCCESS",
                prefill_state="bypassed_Inside"
            )
        else:
            print("  [3] Selecting Meter Location: Inside...")
            if not loc_btn.click_exists(timeout=0.3):
                self.d.shell("input tap 691 1790")

            inside_sel = self.d(text="Inside")
            if not inside_sel.click_exists(timeout=0.4):
                self.d(textContains="Inside").click_exists(timeout=0.2)

            self.telemetry.log_interaction(
                trace_id=trace_id,
                step_num=6,
                screen_name="Screen 2",
                activity="BillingManual",
                action_name="select_meter_location",
                how_method="selector_tap",
                duration_ms=int((time.time() - t0) * 1000),
                status="SUCCESS",
                prefill_state="selected_Inside"
            )

        # 4. Launch Camera via KwhCaptureButton (Zero sleep)
        t0 = time.time()
        print("  [4] Tapping KwhCaptureButton to launch MR Bharat...")
        cam_btn = self.d(resourceId="in.phoenix.bpdcl:id/KwhCaptureButton")
        if not cam_btn.click_exists(timeout=0.5):
            self.d.click(440, 1239)

        w, h = self.cache.get_resolution(self.d)
        rx, ry = round(440 / w, 3), round(1239 / h, 3)

        # 5. Event-based wait for MR Bharat screen
        t_wait = time.time()
        retried_cam = False
        while time.time() - t_wait < timeout:
            # Check fast activity first (~110ms)
            _, act = fast_get_current_activity(self.d)
            if "coral" in act or "MeterReadingActivity" in act or "ScanMeterActivity" in act:
                print(f"  [+] MR Bharat activity reached ({act}) in {round(time.time() - t_start, 2)}s!")
                self.telemetry.log_interaction(
                    trace_id=trace_id,
                    step_num=7,
                    screen_name="Screen 2",
                    activity=act,
                    action_name="launch_camera_button",
                    coord_x=440,
                    coord_y=1239,
                    ratio_x=rx,
                    ratio_y=ry,
                    how_method="click",
                    duration_ms=int((time.time() - t0) * 1000),
                    status="SUCCESS"
                )
                return True

            # Check if camera shutter or pre-capture button appears
            if (self.d(resourceId="in.coral.bpdcl:id/captureImg").exists(timeout=0.05) or
                self.d(resourceId="in.coral.bpdcl:id/capture_readings_btn").exists(timeout=0.05)):
                print(f"  [+] MR Bharat reached in {round(time.time() - t_start, 2)}s!")
                self.telemetry.log_interaction(
                    trace_id=trace_id,
                    step_num=7,
                    screen_name="Screen 2",
                    activity="MRBharat",
                    action_name="launch_camera_button",
                    coord_x=440,
                    coord_y=1239,
                    ratio_x=rx,
                    ratio_y=ry,
                    how_method="click",
                    duration_ms=int((time.time() - t0) * 1000),
                    status="SUCCESS"
                )
                return True

            # If 2.5s pass and still on BillingManual, retry camera button tap once
            if not retried_cam and time.time() - t_wait > 2.5:
                retried_cam = True
                print("  [*] Retrying KwhCaptureButton tap...")
                if not cam_btn.click_exists(timeout=0.3):
                    self.d.click(440, 1239)

            time.sleep(0.08)

        print("  [!] Timed out waiting for MR Bharat to launch.")
        self.telemetry.log_interaction(
            trace_id=trace_id,
            step_num=7,
            screen_name="Screen 2",
            activity="BillingManual",
            action_name="launch_camera_timeout",
            coord_x=440,
            coord_y=1239,
            ratio_x=rx,
            ratio_y=ry,
            how_method="click",
            duration_ms=int((time.time() - t0) * 1000),
            status="TIMEOUT",
            alert_message="MR Bharat launch timed out"
        )
        return False

if __name__ == "__main__":
    mtype = sys.argv[1] if len(sys.argv) > 1 else "NORMAL"
    s2 = Screen2Form()
    ok = s2.fill_form_and_launch_camera(meter_type=mtype)
    sys.exit(0 if ok else 1)
