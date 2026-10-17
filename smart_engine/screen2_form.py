"""
screen2_form.py – Screen 2: High-Speed BillingManual Form Controller.
Restores the 95% reliable selection system from automate_selections.py.
Extracts exact element bounds and dispatches the proven chained ADB flow.
"""
import os
import sys
import time
import uiautomator2 as u2

class Screen2Form:
    def __init__(self, device=None, serial="192.168.9.40:5555"):
        self.d = device or u2.connect(serial)
        self.serial = serial

    def fill_form_and_launch_camera(self, meter_type="NORMAL", timeout=8.0):
        t_start = time.time()
        print("\n[*] [Screen 2] Fast Filling BillingManual Form...")
        is_defective = (str(meter_type).upper() in ["DEFECTIVE", "MD", "MB"])
        target_status = "METER DEFECTIVE" if is_defective else "NORMAL"

        # 1. Locate UI elements on BillingManual
        ps_btn = self.d(resourceId="in.phoenix.bpdcl:id/PresentStatus1")
        obs_btn = self.d(resourceId="in.phoenix.bpdcl:id/atMOBS1")
        loc_btn = self.d(resourceId="in.phoenix.bpdcl:id/meterloctypeiv")

        if not (ps_btn.exists(timeout=0.1) or ps_btn.wait(timeout=2.0)):
            print("  [!] PresentStatus1 not found!")
            return False

        # 2. Extract exact bounds or use proven fallback coordinates
        try:
            ps_info = ps_btn.info.get("bounds", {}) if ps_btn.exists(timeout=0.1) else {}
            ps_arrow_x = ps_info.get("right", 1026) - 50
            ps_arrow_y = (ps_info.get("top", 1766) + ps_info.get("bottom", 1866)) // 2
            ps_opt_x = (ps_info.get("left", 408) + ps_info.get("right", 1026)) // 2
            ps_opt_y = ps_info.get("bottom", 1866) + 50
        except Exception:
            ps_arrow_x, ps_arrow_y = 976, 1816
            ps_opt_x, ps_opt_y = 691, 1890

        try:
            obs_info = obs_btn.info.get("bounds", {}) if obs_btn.exists(timeout=0.1) else {}
            obs_cx = (obs_info.get("left", 408) + obs_info.get("right", 1026)) // 2
            obs_cy = (obs_info.get("top", 1892) + obs_info.get("bottom", 1992)) // 2
        except Exception:
            obs_cx, obs_cy = 691, 1942

        try:
            loc_info = loc_btn.info.get("bounds", {}) if loc_btn.exists(timeout=0.1) else {}
            loc_arrow_x = loc_info.get("right", 1026) - 50
            loc_arrow_y = (loc_info.get("top", 2018) + loc_info.get("bottom", 2118)) // 2
            loc_opt_x = (loc_info.get("left", 408) + loc_info.get("right", 1026)) // 2
            loc_opt_y = 1790 if loc_info.get("bottom", 2118) > 2070 else loc_info.get("bottom", 2118) + 40
        except Exception:
            loc_arrow_x, loc_arrow_y = 976, 2068
            loc_opt_x, loc_opt_y = 691, 1790

        kwh_x, kwh_y = 408, 2257

        # 3. Check prefilled cache (OK + Inside)
        obs_text = (obs_btn.get_text() or "") if obs_btn.exists(timeout=0.05) else ""
        loc_text = (loc_btn.get_text() or "") if loc_btn.exists(timeout=0.05) else ""
        is_prefilled = (obs_text == "OK" and loc_text == "Inside")

        # 4. Build the proven chained flow from automate_selections.py
        if is_defective:
            print("  [*] Defective Meter Mode: Selecting METER DEFECTIVE, DEFECTIVE, and Inside...")
            dpad_bottom = " ".join(["20"] * 10)
            flow = (
                f"input tap {ps_arrow_x} {ps_arrow_y}; sleep 0.35; input tap {ps_opt_x} 1950; sleep 0.45; "
                f"input tap {obs_cx} {obs_cy}; sleep 0.35; input keyevent --delay 15 {dpad_bottom} 66; sleep 0.45; "
                f"input tap {loc_arrow_x} {loc_arrow_y}; sleep 0.35; input tap {loc_opt_x} 1790; sleep 0.45; "
                f"input tap {kwh_x} {kwh_y}"
            )
        elif is_prefilled:
            print("  [+] PRE-FILLED CACHE DETECTED! Site Observation (OK) & Location (Inside) already set.")
            print("  [*] Fast-Path: Selecting ONLY NORMAL -> Camera...")
            flow = (
                f"input tap {ps_arrow_x} {ps_arrow_y}; sleep 0.35; input tap {ps_opt_x} {ps_opt_y}; sleep 0.4; "
                f"input tap {kwh_x} {kwh_y}"
            )
        else:
            print("  [*] Fresh Consumer: Selecting NORMAL, OK (30 DPAD), and Inside...")
            dpad_cmds = " ".join(["20"] * 30)
            flow = (
                f"input tap {ps_arrow_x} {ps_arrow_y}; sleep 0.35; input tap {ps_opt_x} {ps_opt_y}; sleep 0.45; "
                f"input tap {obs_cx} {obs_cy}; sleep 0.35; input keyevent --delay 10 {dpad_cmds} 19 66; sleep 0.45; "
                f"input tap {loc_arrow_x} {loc_arrow_y}; sleep 0.35; input tap {loc_opt_x} {loc_opt_y}; sleep 0.45; "
                f"input tap {kwh_x} {kwh_y}"
            )

        # 5. Dispatch the single chained ADB shell flow
        self.d.shell(flow)

        # 6. Wait for MR Bharat Camera to launch
        t_wait = time.time()
        shutter = self.d(resourceId="in.coral.bpdcl:id/captureImg")
        pre_cap = self.d(resourceId="in.coral.bpdcl:id/capture_readings_btn")

        while time.time() - t_wait < timeout:
            if shutter.exists(timeout=0.03) or pre_cap.exists(timeout=0.03):
                print(f"  [+] MR Bharat reached in {round(time.time() - t_start, 2)}s!")
                return True

            # If 2.5s elapsed without launch, tap KwhCaptureButton fallback
            if time.time() - t_wait > 2.5:
                self.d.shell(f"input tap {kwh_x} {kwh_y}")
                time.sleep(0.5)

            time.sleep(0.08)

        print("  [!] Timed out waiting for MR Bharat to launch.")
        return False

if __name__ == "__main__":
    mtype = sys.argv[1] if len(sys.argv) > 1 else "NORMAL"
    s2 = Screen2Form()
    ok = s2.fill_form_and_launch_camera(meter_type=mtype)
    sys.exit(0 if ok else 1)
