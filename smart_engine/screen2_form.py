"""
screen2_form.py – Screen 2: BillingManual Form Controller (in.phoenix.billing.BillingManual).
Selects Meter Reading Status, Site Observation, and Location, then launches MR Bharat.
"""
import os
import sys
import time
import subprocess
import uiautomator2 as u2

class Screen2Form:
    def __init__(self, device=None, serial="192.168.9.40:5555"):
        self.d = device or u2.connect(serial)
        self.serial = serial

    def fill_form_and_launch_camera(self, meter_type="NORMAL", timeout=8.0):
        print("\n[*] [Screen 2] Filling BillingManual Form...")
        is_defective = (str(meter_type).upper() == "DEFECTIVE")
        target_status = "METER DEFECTIVE" if is_defective else "NORMAL"

        # 1. Select Present Status
        print(f"  [1] Selecting Present Status: {target_status}...")
        ps_btn = self.d(resourceId="in.phoenix.bpdcl:id/PresentStatus1")
        if ps_btn.exists(timeout=2.0):
            ps_btn.click()
            time.sleep(0.4)
            self.d(text=target_status).click_exists(timeout=1.5)
        else:
            print("  [!] PresentStatus1 not found!")
            return False

        time.sleep(0.3)

        # 2. Select Site Observation (OK)
        print("  [2] Selecting Site Observation: OK...")
        obs_btn = self.d(resourceId="in.phoenix.bpdcl:id/atMOBS1")
        if obs_btn.exists(timeout=2.0):
            obs_btn.click()
            time.sleep(0.35)
            # Reliable DPAD sequence to select OK
            dpad = " ".join(["20"] * 30)
            subprocess.run([
                "adb", "-s", self.serial, "shell",
                f"input keyevent --delay 10 {dpad} 19 66"
            ], capture_output=True)
            time.sleep(0.4)
        else:
            print("  [!] atMOBS1 not found!")
            return False

        # 3. Select Meter Location Type (Inside)
        print("  [3] Selecting Meter Location: Inside...")
        loc_btn = self.d(resourceId="in.phoenix.bpdcl:id/meterloctypeiv")
        if loc_btn.exists(timeout=2.0):
            loc_btn.click()
            time.sleep(0.4)
            self.d(text="Inside").click_exists(timeout=1.5)
        else:
            print("  [!] meterloctypeiv not found!")
            return False

        time.sleep(0.4)

        # 4. Launch Camera via KwhCaptureButton
        print("  [4] Tapping KwhCaptureButton to launch MR Bharat...")
        cam_btn = self.d(resourceId="in.phoenix.bpdcl:id/KwhCaptureButton")
        if cam_btn.exists(timeout=2.0):
            cam_btn.click()
        else:
            # Fallback to center coordinates
            self.d.click(440, 1239)

        # 5. Wait for MR Bharat to open
        t_start = time.time()
        while time.time() - t_start < timeout:
            act = self.d.app_current().get("activity", "")
            pkg = self.d.app_current().get("package", "")
            if "coral" in pkg or "MeterReadingActivity" in act or "ScanMeterActivity" in act:
                print(f"  [+] MR Bharat reached ({act}) in {round(time.time() - t_start, 2)}s!")
                time.sleep(0.5)
                return True
            time.sleep(0.3)

        print("  [!] Failed to launch MR Bharat within timeout.")
        return False

if __name__ == "__main__":
    s2 = Screen2Form()
    ok = s2.fill_form_and_launch_camera()
    sys.exit(0 if ok else 1)
