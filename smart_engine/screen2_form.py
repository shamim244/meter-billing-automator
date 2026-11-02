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

class Screen2Form:
    def __init__(self, device=None, serial=None):
        if not device:
            serial = resolve_device_serial(serial)
        self.d = device or u2.connect(serial)
        self.serial = serial
        self.cache = UniversalUICache.get_instance()

    def fill_form_and_launch_camera(self, meter_type="NORMAL", timeout=8.0):
        t_start = time.time()
        print("\n[*] [Screen 2] Fast Filling BillingManual Form...")
        is_defective = (str(meter_type).upper() == "DEFECTIVE")
        target_status = "Meter Defective" if is_defective else "NORMAL"

        # 1. Select Present Status
        print(f"  [1] Selecting Present Status: {target_status}...")
        ps_btn = self.d(resourceId="in.phoenix.bpdcl:id/PresentStatus1")
        if not (ps_btn.exists(timeout=0.05) or ps_btn.wait(timeout=2.5)):
            print("  [!] PresentStatus1 not found!")
            return False

        # Tap Present Status spinner (Cached -> Selector)
        if not self.cache.tap("screen2.present_status", self.d, selector_obj=ps_btn):
            ps_btn.click()

        # Tap target status option
        status_sel = self.d(text=target_status)
        if not self.cache.tap(f"screen2.status_{target_status}", self.d, selector_obj=status_sel):
            if not status_sel.click_exists(timeout=0.3):
                if not self.d(text="METER DEFECTIVE").click_exists(timeout=0.2):
                    self.d(textContains="DEFECTIVE" if is_defective else "NORMAL").click_exists(timeout=0.2)

        # 2. Select Site Observation with smart prefill bypass
        target_obs = "DEFECTIVE" if is_defective else "OK"
        obs_btn = self.d(resourceId="in.phoenix.bpdcl:id/atMOBS1")
        try:
            obs_text = obs_btn.get_text()
        except Exception:
            obs_text = ""

        if obs_text == target_obs:
            print(f"  [2] Site Observation already prefilled with '{target_obs}' – Fast-path bypass!")
        else:
            print(f"  [2] Selecting Site Observation: {target_obs}...")
            obs_tapped = self.cache.tap("screen2.obs_btn", self.d, selector_obj=obs_btn, fallback_coords=(691, 1942))
            if not obs_tapped and not obs_btn.click_exists(timeout=0.2):
                self.d.shell("input tap 691 1942")

            if is_defective:
                def_sel = self.d(text="DEFECTIVE")
                if not self.cache.tap("screen2.obs_defective", self.d, selector_obj=def_sel):
                    if not def_sel.click_exists(timeout=0.3):
                        if not self.d(textContains="DEFECTIVE").click_exists(timeout=0.2):
                            # DPAD down to bottom (DEFECTIVE is last of 6 options) and press enter
                            dpad = " ".join(["20"] * 30)
                            self.d.shell(f"input keyevent --delay 2 {dpad} 66")
            else:
                ok_sel = self.d(text="OK")
                if not self.cache.tap("screen2.obs_ok", self.d, selector_obj=ok_sel):
                    # Fast DPAD sequence via direct socket shell (delay 2ms)
                    dpad = " ".join(["20"] * 30)
                    self.d.shell(f"input keyevent --delay 2 {dpad} 19 66")

        # 3. Select Meter Location Type (Inside) with smart prefill bypass
        loc_btn = self.d(resourceId="in.phoenix.bpdcl:id/meterloctypeiv")
        try:
            loc_text = loc_btn.get_text()
        except Exception:
            loc_text = ""

        if loc_text == "Inside":
            print("  [3] Meter Location already prefilled with 'Inside' – Fast-path bypass!")
        else:
            print("  [3] Selecting Meter Location: Inside...")
            loc_tapped = self.cache.tap("screen2.loc_btn", self.d, selector_obj=loc_btn, fallback_coords=(691, 1790))
            if not loc_tapped and not loc_btn.click_exists(timeout=0.2):
                self.d.shell("input tap 691 1790")

            inside_sel = self.d(text="Inside")
            if not self.cache.tap("screen2.loc_inside", self.d, selector_obj=inside_sel):
                if not inside_sel.click_exists(timeout=0.3):
                    self.d(textContains="Inside").click_exists(timeout=0.2)

        # 4. Launch Camera via KwhCaptureButton (Zero sleep)
        print("  [4] Tapping KwhCaptureButton to launch MR Bharat...")
        cam_btn = self.d(resourceId="in.phoenix.bpdcl:id/KwhCaptureButton")
        if not self.cache.tap("screen2.cam_btn", self.d, selector_obj=cam_btn, fallback_coords=(440, 1239)):
            if not cam_btn.click_exists(timeout=0.2):
                self.d.click(440, 1239)

        # 5. Event-based wait for MR Bharat screen
        t_wait = time.time()
        while time.time() - t_wait < timeout:
            # Check fast activity first (~110ms)
            _, act = fast_get_current_activity(self.d)
            if "coral" in act or "MeterReadingActivity" in act or "ScanMeterActivity" in act:
                print(f"  [+] MR Bharat activity reached ({act}) in {round(time.time() - t_start, 2)}s!")
                return True

            # Check if camera shutter or pre-capture button appears
            if (self.d(resourceId="in.coral.bpdcl:id/captureImg").exists(timeout=0.05) or
                self.d(resourceId="in.coral.bpdcl:id/capture_readings_btn").exists(timeout=0.05)):
                print(f"  [+] MR Bharat reached in {round(time.time() - t_start, 2)}s!")
                return True

            time.sleep(0.05)

        print("  [!] Timed out waiting for MR Bharat to launch.")
        return False

if __name__ == "__main__":
    mtype = sys.argv[1] if len(sys.argv) > 1 else "NORMAL"
    s2 = Screen2Form()
    ok = s2.fill_form_and_launch_camera(meter_type=mtype)
    sys.exit(0 if ok else 1)
