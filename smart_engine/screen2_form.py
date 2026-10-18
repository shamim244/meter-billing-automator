"""
screen2_form.py – Screen 2: High-Speed BillingManual Form Controller.
Selects Meter Reading Status, Site Observation, and Location, then launches MR Bharat.
Uses direct persistent ADB socket shell keyevents and zero static sleeps.
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
        is_defective = (str(meter_type).upper() == "DEFECTIVE")
        target_status = "METER DEFECTIVE" if is_defective else "NORMAL"

        # 1. Select Present Status
        print(f"  [1] Selecting Present Status: {target_status}...")
        ps_btn = self.d(resourceId="in.phoenix.bpdcl:id/PresentStatus1")
        if not (ps_btn.exists(timeout=0.05) or ps_btn.wait(timeout=2.5)):
            print("  [!] PresentStatus1 not found!")
            return False

        ps_btn.click()
        if not self.d(text=target_status).click_exists(timeout=0.3):
            self.d(textContains=target_status).click_exists(timeout=0.2)

        # 2. Select Site Observation (OK) with smart prefill bypass
        obs_btn = self.d(resourceId="in.phoenix.bpdcl:id/atMOBS1")
        obs_text = obs_btn.get_text() if obs_btn.exists(timeout=0.05) else ""
        if obs_text == "OK":
            print("  [2] Site Observation already prefilled with 'OK' – Fast-path bypass!")
        else:
            print("  [2] Selecting Site Observation: OK...")
            if obs_btn.click_exists(timeout=0.2):
                # Fast DPAD sequence via direct socket shell (delay 2ms)
                dpad = " ".join(["20"] * 30)
                self.d.shell(f"input keyevent --delay 2 {dpad} 19 66")
            else:
                self.d.shell("input tap 691 1942")

        # 3. Select Meter Location Type (Inside) with smart prefill bypass
        loc_btn = self.d(resourceId="in.phoenix.bpdcl:id/meterloctypeiv")
        loc_text = loc_btn.get_text() if loc_btn.exists(timeout=0.05) else ""
        if loc_text == "Inside":
            print("  [3] Meter Location already prefilled with 'Inside' – Fast-path bypass!")
        else:
            print("  [3] Selecting Meter Location: Inside...")
            if loc_btn.click_exists(timeout=0.2):
                if not self.d(text="Inside").click_exists(timeout=0.3):
                    self.d(textContains="Inside").click_exists(timeout=0.2)
            else:
                self.d.shell("input tap 691 1790")

        # 4. Launch Camera via KwhCaptureButton (Zero sleep)
        print("  [4] Tapping KwhCaptureButton to launch MR Bharat...")
        cam_btn = self.d(resourceId="in.phoenix.bpdcl:id/KwhCaptureButton")
        if not cam_btn.click_exists(timeout=0.2):
            self.d.click(440, 1239)

        # 5. Event-based wait for MR Bharat screen
        t_wait = time.time()
        while time.time() - t_wait < timeout:
            # Check if camera shutter or pre-capture button appears
            if (self.d(resourceId="in.coral.bpdcl:id/captureImg").exists(timeout=0.05) or
                self.d(resourceId="in.coral.bpdcl:id/capture_readings_btn").exists(timeout=0.05)):
                print(f"  [+] MR Bharat reached in {round(time.time() - t_start, 2)}s!")
                return True

            act = ""
            try:
                act = self.d.app_current().get("activity", "")
            except Exception:
                pass

            if "coral" in act or "MeterReadingActivity" in act or "ScanMeterActivity" in act:
                print(f"  [+] MR Bharat activity reached ({act}) in {round(time.time() - t_start, 2)}s!")
                return True

            time.sleep(0.08)

        print("  [!] Timed out waiting for MR Bharat to launch.")
        return False

if __name__ == "__main__":
    mtype = sys.argv[1] if len(sys.argv) > 1 else "NORMAL"
    s2 = Screen2Form()
    ok = s2.fill_form_and_launch_camera(meter_type=mtype)
    sys.exit(0 if ok else 1)
