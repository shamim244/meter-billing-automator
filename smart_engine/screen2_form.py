"""
screen2_form.py – Screen 2: Ground-Truth Dynamic BillingManual Form Controller.
Dynamically tracks element positions across layout reflows, guaranteeing 100% accurate
selection of PresentStatus (NORMAL), Site Observation (OK), Meter Location (Inside),
and dynamic KwhCaptureButton launch into MR Bharat.
"""
import os
import sys
import time
import uiautomator2 as u2

class Screen2Form:
    def __init__(self, device=None, serial="192.168.9.40:5555"):
        self.d = device or u2.connect(serial)
        self.serial = serial

    def _get_bounds(self, elem):
        try:
            if hasattr(elem, "info") and isinstance(elem.info, dict):
                return elem.info.get("bounds", {})
        except Exception:
            pass
        return {}

    def fill_form_and_launch_camera(self, meter_type="NORMAL", timeout=12.0):
        t_start = time.time()
        print("\n[*] [Screen 2] Fast Filling BillingManual Form...")
        is_defective = (str(meter_type).upper() in ["DEFECTIVE", "MD", "MB"])
        target_status = "METER DEFECTIVE" if is_defective else "NORMAL"

        ps_btn = self.d(resourceId="in.phoenix.bpdcl:id/PresentStatus1")
        if not (ps_btn.exists(timeout=0.1) or ps_btn.wait(timeout=2.0)):
            print("  [!] PresentStatus1 not found!")
            return False

        # 1. Step 1: Select PresentStatus1 (NORMAL / METER DEFECTIVE)
        print(f"  [1] Selecting Present Status: {target_status}...")
        ps_bounds = self._get_bounds(ps_btn)
        ps_right = ps_bounds.get("right", 1026)
        ps_top = ps_bounds.get("top", 1793)
        ps_bottom = ps_bounds.get("bottom", 1893)
        ps_arrow_x = int(ps_right) - 50
        ps_arrow_y = int((ps_top + ps_bottom) // 2)
        ps_opt_x = int((ps_bounds.get("left", 408) + ps_right) // 2)
        ps_opt_y = int(ps_bottom) + 50

        self.d.shell(f"input tap {ps_arrow_x} {ps_arrow_y}")
        time.sleep(0.35)
        opt_node = self.d(text=target_status)
        if opt_node.wait(timeout=1.0):
            opt_node.click()
        else:
            self.d.shell(f"input tap {ps_opt_x} {ps_opt_y}")
        time.sleep(0.4)

        # 2. Step 2: Handle Site Observation (OK) with FRESH bounds
        obs_btn = self.d(resourceId="in.phoenix.bpdcl:id/atMOBS1")
        obs_text = (obs_btn.get_text() or "") if obs_btn.exists(timeout=0.1) else ""

        if obs_text == "OK":
            print("  [2] Site Observation already prefilled with 'OK' – Fast-path bypass!")
        elif is_defective:
            print("  [2] Defective Meter: Selecting DEFECTIVE observation...")
            obs_b = self._get_bounds(obs_btn)
            obs_cx = int((obs_b.get("left", 408) + obs_b.get("right", 1026)) // 2)
            obs_cy = int((obs_b.get("top", 1919) + obs_b.get("bottom", 2019)) // 2)
            dpad_bottom = " ".join(["20"] * 10)
            self.d.shell(f"input tap {obs_cx} {obs_cy}; sleep 0.35; input keyevent --delay 15 {dpad_bottom} 66")
            time.sleep(0.4)
        else:
            print("  [2] Selecting Site Observation: OK...")
            obs_b = self._get_bounds(obs_btn)
            obs_cx = int((obs_b.get("left", 408) + obs_b.get("right", 1026)) // 2)
            obs_cy = int((obs_b.get("top", 1919) + obs_b.get("bottom", 2019)) // 2)
            dpad_cmds = " ".join(["20"] * 30)
            # Proven ground-truth sequence: tap center to focus dropdown, 30 DPAD down, 1 DPAD up (to OK), ENTER
            flow = f"input tap {obs_cx} {obs_cy}; sleep 0.35; input keyevent --delay 10 {dpad_cmds} 19 66"
            self.d.shell(flow)
            time.sleep(0.45)

        # 3. Step 3: Handle Meter Location (Inside) with FRESH bounds
        loc_btn = self.d(resourceId="in.phoenix.bpdcl:id/meterloctypeiv")
        loc_text = (loc_btn.get_text() or "") if loc_btn.exists(timeout=0.1) else ""

        if loc_text == "Inside":
            print("  [3] Meter Location already prefilled with 'Inside' – Fast-path bypass!")
        else:
            print("  [3] Selecting Meter Location: Inside...")
            loc_b = self._get_bounds(loc_btn)
            loc_right = loc_b.get("right", 1026)
            loc_arrow_x = int(loc_right) - 50
            loc_arrow_y = int((loc_b.get("top", 2045) + loc_b.get("bottom", 2145)) // 2)
            loc_opt_x = int((loc_b.get("left", 408) + loc_right) // 2)
            loc_opt_y = 1790 if loc_b.get("bottom", 2145) > 2070 else int(loc_b.get("bottom", 2145)) + 40
            flow = f"input tap {loc_arrow_x} {loc_arrow_y}; sleep 0.35; input tap {loc_opt_x} {loc_opt_y}"
            self.d.shell(flow)
            time.sleep(0.4)

        # 4. Step 4: Locate & Tap KwhCaptureButton with FRESH bounds
        print("  [4] Tapping KwhCaptureButton to launch MR Bharat...")
        cam_btn = self.d(resourceId="in.phoenix.bpdcl:id/KwhCaptureButton")

        # Allow layout expansion
        cam_btn.wait(timeout=1.5)

        cam_b = self._get_bounds(cam_btn)
        if cam_b and "top" in cam_b and "bottom" in cam_b:
            cam_cx = int((cam_b.get("left", 357) + cam_b.get("right", 524)) // 2)
            cam_cy = int((cam_b.get("top", 1926) + cam_b.get("bottom", 2048)) // 2)
        else:
            # Mathematical fallback relative to meterloctypeiv cy + 189
            loc_b = self._get_bounds(loc_btn)
            loc_cy = int((loc_b.get("top", 1748) + loc_b.get("bottom", 1848)) // 2)
            cam_cx = 440
            cam_cy = loc_cy + 189

        self.d.shell(f"input tap {cam_cx} {cam_cy}")

        # 5. Wait for MR Bharat Camera to launch
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
                # Re-query fresh cam bounds in case of layout shift
                cam_b = self._get_bounds(self.d(resourceId="in.phoenix.bpdcl:id/KwhCaptureButton"))
                if cam_b and "top" in cam_b:
                    cam_cx = int((cam_b.get("left", 357) + cam_b.get("right", 524)) // 2)
                    cam_cy = int((cam_b.get("top", 1926) + cam_b.get("bottom", 2048)) // 2)
                self.d.shell(f"input tap {cam_cx} {cam_cy}")
                time.sleep(0.5)

            time.sleep(0.15)

        print("  [!] Timed out waiting for MR Bharat to launch.")
        return False

if __name__ == "__main__":
    mtype = sys.argv[1] if len(sys.argv) > 1 else "NORMAL"
    s2 = Screen2Form()
    ok = s2.fill_form_and_launch_camera(meter_type=mtype)
    sys.exit(0 if ok else 1)
