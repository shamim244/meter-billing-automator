"""
screen2_form.py – Screen 2: Dynamic BillingManual Form Controller.
Combines dynamic uiautomator2 element inspection, text-based option selection,
smart prefilled caching, scroll-into-view, and fallback chained shell execution.
"""
import os
import sys
import time
import uiautomator2 as u2

class Screen2Form:
    def __init__(self, device=None, serial="192.168.9.40:5555"):
        self.d = device or u2.connect(serial)
        self.serial = serial

    def fill_form_and_launch_camera(self, meter_type="NORMAL", timeout=10.0):
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

        # 2. Extract exact bounds or use proven fallbacks
        try:
            ps_info = ps_btn.info if hasattr(ps_btn, 'info') and isinstance(ps_btn.info, dict) else {}
            ps_bounds = ps_info.get("bounds", {}) if isinstance(ps_info, dict) else {}
            ps_right = ps_bounds.get("right", 1026) if isinstance(ps_bounds.get("right"), (int, float)) else 1026
            ps_top = ps_bounds.get("top", 1793) if isinstance(ps_bounds.get("top"), (int, float)) else 1793
            ps_bottom = ps_bounds.get("bottom", 1893) if isinstance(ps_bounds.get("bottom"), (int, float)) else 1893
            ps_arrow_x = int(ps_right) - 50
            ps_arrow_y = int((ps_top + ps_bottom) // 2)
            ps_left = ps_bounds.get("left", 408) if isinstance(ps_bounds.get("left"), (int, float)) else 408
            ps_opt_x = int((ps_left + ps_right) // 2)
            ps_opt_y = int(ps_bottom) + 50
        except Exception:
            ps_arrow_x, ps_arrow_y = 976, 1843
            ps_opt_x, ps_opt_y = 691, 1943

        try:
            obs_info = obs_btn.info if hasattr(obs_btn, 'info') and isinstance(obs_btn.info, dict) else {}
            obs_bounds = obs_info.get("bounds", {}) if isinstance(obs_info, dict) else {}
            obs_right = obs_bounds.get("right", 1026) if isinstance(obs_bounds.get("right"), (int, float)) else 1026
            obs_top = obs_bounds.get("top", 1919) if isinstance(obs_bounds.get("top"), (int, float)) else 1919
            obs_bottom = obs_bounds.get("bottom", 2019) if isinstance(obs_bounds.get("bottom"), (int, float)) else 2019
            obs_left = obs_bounds.get("left", 408) if isinstance(obs_bounds.get("left"), (int, float)) else 408
            obs_arrow_x = int(obs_right) - 50
            obs_arrow_y = int((obs_top + obs_bottom) // 2)
            obs_cx = int((obs_left + obs_right) // 2)
            obs_cy = obs_arrow_y
        except Exception:
            obs_arrow_x, obs_arrow_y = 976, 1969
            obs_cx, obs_cy = 691, 1969

        try:
            loc_info = loc_btn.info if hasattr(loc_btn, 'info') and isinstance(loc_btn.info, dict) else {}
            loc_bounds = loc_info.get("bounds", {}) if isinstance(loc_info, dict) else {}
            loc_right = loc_bounds.get("right", 1026) if isinstance(loc_bounds.get("right"), (int, float)) else 1026
            loc_top = loc_bounds.get("top", 2045) if isinstance(loc_bounds.get("top"), (int, float)) else 2045
            loc_bottom = loc_bounds.get("bottom", 2145) if isinstance(loc_bounds.get("bottom"), (int, float)) else 2145
            loc_left = loc_bounds.get("left", 408) if isinstance(loc_bounds.get("left"), (int, float)) else 408
            loc_arrow_x = int(loc_right) - 50
            loc_arrow_y = int((loc_top + loc_bottom) // 2)
            loc_opt_x = int((loc_left + loc_right) // 2)
            loc_opt_y = 1790 if loc_bottom > 2070 else int(loc_bottom) + 40
        except Exception:
            loc_arrow_x, loc_arrow_y = 976, 2095
            loc_opt_x, loc_opt_y = 691, 1790

        # 3. Check prefilled cache (OK + Inside)
        obs_text = (obs_btn.get_text() or "") if obs_btn.exists(timeout=0.05) else ""
        loc_text = (loc_btn.get_text() or "") if loc_btn.exists(timeout=0.05) else ""
        is_prefilled = (obs_text == "OK" and loc_text == "Inside")

        # 4. Select PresentStatus1 (NORMAL / METER DEFECTIVE)
        print(f"  [1] Selecting Present Status: {target_status}...")
        self.d.click(ps_arrow_x, ps_arrow_y)
        time.sleep(0.3)
        target_node = self.d(text=target_status)
        if target_node.wait(timeout=1.0):
            target_node.click()
        else:
            self.d.click(ps_opt_x, ps_opt_y)
        time.sleep(0.3)

        # 5. Handle Site Observation
        if is_prefilled:
            print("  [2] Site Observation already prefilled with 'OK' – Fast-path bypass!")
        elif is_defective:
            print("  [2] Defective Meter: Selecting DEFECTIVE observation...")
            self.d.click(obs_cx, obs_cy)
            time.sleep(0.3)
            dpad_bottom = " ".join(["20"] * 10)
            self.d.shell(f"input keyevent --delay 15 {dpad_bottom} 66")
            time.sleep(0.3)
        else:
            print("  [2] Selecting Site Observation: OK...")
            self.d.click(obs_arrow_x, obs_arrow_y)
            time.sleep(0.3)
            # Check if OK is already visible in popup
            ok_node = self.d(text="OK")
            if ok_node.exists(timeout=0.2):
                ok_node.click()
            else:
                # Fast proven DPAD scroll directly to OK
                dpad_cmds = " ".join(["20"] * 30)
                self.d.shell(f"input keyevent --delay 10 {dpad_cmds} 19 66")
            time.sleep(0.3)

        # 6. Handle Meter Location
        if is_prefilled:
            print("  [3] Meter Location already prefilled with 'Inside' – Fast-path bypass!")
        else:
            print("  [3] Selecting Meter Location: Inside...")
            self.d.click(loc_arrow_x, loc_arrow_y)
            time.sleep(0.3)
            inside_node = self.d(text="Inside")
            if inside_node.wait(timeout=1.0):
                inside_node.click()
            else:
                self.d.click(loc_opt_x, loc_opt_y)
            time.sleep(0.3)

        # 7. Locate & Scroll to KwhCaptureButton
        print("  [4] Tapping KwhCaptureButton to launch MR Bharat...")
        cam_btn = self.d(resourceId="in.phoenix.bpdcl:id/KwhCaptureButton")

        # Give Android layout up to 1.5s to expand KWH row
        if not cam_btn.wait(timeout=1.5):
            # Scroll down to ensure it is rendered
            self.d.swipe(540, 1800, 540, 1200, 0.2)
            time.sleep(0.3)

        if cam_btn.exists(timeout=0.5):
            try:
                info = cam_btn.info if hasattr(cam_btn, 'info') and isinstance(cam_btn.info, dict) else {}
                bounds = info.get("bounds", {}) if isinstance(info, dict) else {}
                bottom = bounds.get("bottom", 0) if isinstance(bounds, dict) else 0
                if isinstance(bottom, (int, float)) and bottom > 2330:
                    self.d.swipe(540, 1800, 540, 1500, 0.2)
                    time.sleep(0.2)
            except Exception:
                pass
            cam_btn.click()
        else:
            # Fallback to coordinate tap
            self.d.shell("input tap 440 2284")

        # 8. Wait for MR Bharat Camera to launch
        t_wait = time.time()
        shutter = self.d(resourceId="in.coral.bpdcl:id/captureImg")
        pre_cap = self.d(resourceId="in.coral.bpdcl:id/capture_readings_btn")

        while time.time() - t_wait < timeout:
            try:
                if shutter.exists(timeout=0.05) or pre_cap.exists(timeout=0.05):
                    print(f"  [+] MR Bharat reached in {round(time.time() - t_start, 2)}s!")
                    return True
            except Exception:
                pass

            # Fast shell fallback check in case u2 jsonrpc dropped momentarily during camera init
            try:
                out = self.d.shell("dumpsys window | grep mCurrentFocus")
                focus_text = out[0] if isinstance(out, tuple) else getattr(out, 'output', str(out))
                if "MeterReadingActivity" in focus_text or "ScanMeterActivity" in focus_text:
                    print(f"  [+] MR Bharat reached in {round(time.time() - t_start, 2)}s!")
                    return True
            except Exception:
                pass

            # If 2.5s elapsed without launch, retry tapping KwhCaptureButton
            if time.time() - t_wait > 2.5:
                try:
                    if cam_btn.exists(timeout=0.1):
                        cam_btn.click()
                    else:
                        self.d.shell("input tap 440 2284")
                except Exception:
                    self.d.shell("input tap 440 2284")
                time.sleep(0.5)

            time.sleep(0.15)

        print("  [!] Timed out waiting for MR Bharat to launch.")
        return False

if __name__ == "__main__":
    mtype = sys.argv[1] if len(sys.argv) > 1 else "NORMAL"
    s2 = Screen2Form()
    ok = s2.fill_form_and_launch_camera(meter_type=mtype)
    sys.exit(0 if ok else 1)
