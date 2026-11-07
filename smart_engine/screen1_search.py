"""
screen1_search.py – Screen 1: High-Speed Consumer Search Controller (ConsumerSearchActivity).
Uses direct am start, universal coordinate caching, and dynamic event polling for BillingManual and alerts.
"""
import os
import sys
import time
import uiautomator2 as u2
from smart_engine.device import resolve_device_serial
from smart_engine.ui_cache import UniversalUICache, fast_get_current_activity
from smart_engine.telemetry import TelemetryManager

class Screen1Search:
    def __init__(self, device=None, serial=None):
        if not device:
            serial = resolve_device_serial(serial)
        self.d = device or u2.connect(serial)
        self.serial = serial
        self.cache = UniversalUICache.get_instance()
        self.telemetry = TelemetryManager.get_instance()

    def search_consumer(self, ca_number, timeout=8.0, trace_id=None):
        print(f"\n[*] [Screen 1] Fast Searching Consumer CA: {ca_number}...")
        try:
            self.d.screen_on()
            self.d.shell("svc power stayon true")
        except Exception:
            pass

        # Dismiss any lingering alerts from previous screen
        old_alert = self.d(resourceId="android:id/button1")
        if old_alert.exists(timeout=0.05):
            try:
                old_alert.click()
            except Exception:
                pass

        # 1. Start clean ConsumerSearchActivity directly
        t0 = time.time()
        self.d.shell("am start -n in.phoenix.bpdcl/in.phoenix.bpdcl.ConsumerSearchActivity --activity-clear-top")

        # 2. Enter CA number into bh_AccNo1search
        input_field = self.d(resourceId="in.phoenix.bpdcl:id/bh_AccNo1search")
        if input_field.wait(timeout=2.0):
            try:
                input_field.clear_text()
            except Exception:
                pass
            input_field.set_text(str(ca_number))
            input_method = "set_text"
        else:
            self.d.shell(f"input tap 727 543; input text {ca_number}")
            input_method = "shell_text"

        # Immediately dismiss soft keyboard so cons_search is visible and no keyboard touches occur
        try:
            self.d.press("back")
            time.sleep(0.05)
        except Exception:
            pass

        t_input_ms = int((time.time() - t0) * 1000)
        self.telemetry.log_interaction(
            trace_id=trace_id,
            step_num=1,
            screen_name="Screen 1",
            activity="ConsumerSearchActivity",
            action_name="enter_ca_and_dismiss_keyboard",
            how_method=input_method,
            duration_ms=t_input_ms,
            status="SUCCESS"
        )

        # 3. Click Search button (Universal Cache -> Selector -> Scaled fallback)
        t_click0 = time.time()
        search_btn = self.d(resourceId="in.phoenix.bpdcl:id/cons_search")
        tapped = self.cache.tap("screen1.search_btn", self.d, selector_obj=search_btn, fallback_coords=(450, 726))
        method_used = "cached_tap" if tapped else "click_exists"
        if not tapped:
            if not search_btn.click_exists(timeout=0.5):
                self.d.click(450, 726)
                method_used = "fallback_click"

        # Calculate coordinates for telemetry
        w, h = self.cache.get_resolution(self.d)
        rx, ry = round(450 / w, 3), round(726 / h, 3)
        self.telemetry.log_interaction(
            trace_id=trace_id,
            step_num=2,
            screen_name="Screen 1",
            activity="ConsumerSearchActivity",
            action_name="tap_search_button",
            coord_x=450,
            coord_y=726,
            ratio_x=rx,
            ratio_y=ry,
            how_method=method_used,
            duration_ms=int((time.time() - t_click0) * 1000),
            status="SUCCESS"
        )

        # 4. Dynamic Event Loop: Wait for BillingManual OR Alert popup
        t_start = time.time()
        while time.time() - t_start < timeout:
            # Fast check if BillingManual is reached (via fast activity check or PresentStatus1)
            _, act = fast_get_current_activity(self.d)
            ps_btn = self.d(resourceId="in.phoenix.bpdcl:id/PresentStatus1")

            if "BillingManual" in act or ps_btn.exists(timeout=0.05):
                elapsed_ms = int((time.time() - t_start) * 1000)
                print(f"  [+] BillingManual reached and ready in {round(elapsed_ms / 1000, 2)}s!")
                self.telemetry.log_interaction(
                    trace_id=trace_id,
                    step_num=3,
                    screen_name="Screen 1",
                    activity="BillingManual",
                    action_name="transition_billing_manual",
                    duration_ms=elapsed_ms,
                    status="SUCCESS"
                )
                return True

            # If not yet at BillingManual, check if an error / warning alert appeared
            alert = self.d(resourceId="android:id/alertTitle")
            if alert.exists(timeout=0.05):
                title = alert.get_text() if alert.exists() else "Alert"
                msg_elem = self.d(resourceId="android:id/message")
                msg = msg_elem.get_text() if msg_elem.exists() else ""
                print(f"  [!] Alert detected: '{title}' - '{msg}'")
                btn1 = self.d(resourceId="android:id/button1")
                if btn1.exists(timeout=0.5):
                    btn1.click()
                elapsed_ms = int((time.time() - t_start) * 1000)
                self.telemetry.log_interaction(
                    trace_id=trace_id,
                    step_num=3,
                    screen_name="Screen 1",
                    activity="ConsumerSearchActivity",
                    action_name="search_alert_dismissed",
                    duration_ms=elapsed_ms,
                    status="ALERT_INTERCEPTED",
                    alert_message=f"{title}: {msg}"
                )
                return False

            time.sleep(0.05)

        print("  [!] Failed to reach BillingManual within timeout.")
        self.telemetry.log_interaction(
            trace_id=trace_id,
            step_num=3,
            screen_name="Screen 1",
            activity="ConsumerSearchActivity",
            action_name="search_timeout",
            duration_ms=int((time.time() - t_start) * 1000),
            status="TIMEOUT"
        )
        return False

if __name__ == "__main__":
    ca = sys.argv[1] if len(sys.argv) > 1 else "10230047179"
    s1 = Screen1Search()
    ok = s1.search_consumer(ca)
    sys.exit(0 if ok else 1)
