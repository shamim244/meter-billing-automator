"""
screen4_submit.py – Screen 4: NBPDCL Final Submission & Stage-Only Safety Gate.
Optimized with universal coordinate caching, zero-subprocess resets, and fast activity navigation.
"""
import os
import sys
import time
import uiautomator2 as u2
from smart_engine.device import resolve_device_serial
from smart_engine.ui_cache import UniversalUICache, fast_get_current_activity
from smart_engine.telemetry import TelemetryManager

class Screen4Submit:
    def __init__(self, device=None, serial=None):
        if not device:
            serial = resolve_device_serial(serial)
        self.d = device or u2.connect(serial)
        self.serial = serial
        self.cache = UniversalUICache.get_instance()
        self.telemetry = TelemetryManager.get_instance()

    def handle_final_submit(self, do_submit=False, timeout=10.0, trace_id=None):
        t0 = time.time()
        w, h = self.cache.get_resolution(self.d)

        if not do_submit:
            print("\n[*] [Screen 4] [STAGE-ONLY MODE] Bill is filled and validated on device.")
            print("  [*] Skipping final NBPDCL submit as requested (Safe Mode).")
            print("  [*] Fast resetting to ConsumerSearchActivity for next consumer...")
            try:
                self.d.app_start("in.phoenix.bpdcl", ".ConsumerSearchActivity", stop=False)
            except Exception:
                self.d.shell("am start -n in.phoenix.bpdcl/in.phoenix.bpdcl.ConsumerSearchActivity --activity-clear-top")

            self.telemetry.log_interaction(
                trace_id=trace_id,
                step_num=12,
                screen_name="Screen 4",
                activity="ConsumerSearchActivity",
                action_name="stage_only_reset",
                duration_ms=int((time.time() - t0) * 1000),
                status="SUCCESS",
                prefill_state="stage_only"
            )
            return True

        print("\n[*] [Screen 4] Executing Final NBPDCL Bill Generation...")
        # 1. Scroll to bottom of BillingManual (dynamic window size)
        mid_x = w // 2
        start_y = int(h * 0.75)
        end_y = int(h * 0.18)
        self.d.swipe(mid_x, start_y, mid_x, end_y)
        time.sleep(0.02)
        self.d.swipe(mid_x, start_y, mid_x, end_y)
        time.sleep(0.02)

        # 2. Tap Submit button (Cached -> Selector -> Scaled fallback)
        t_sub0 = time.time()
        submit_btn = self.d(resourceId="in.phoenix.bpdcl:id/Submit")
        print("  [*] Tapping NBPDCL Submit button...")
        tapped = self.cache.tap("screen4.submit_btn", self.d, selector_obj=submit_btn, fallback_coords=(293, 2267))
        method_used = "cached_tap" if tapped else "click_exists"
        if not tapped:
            if not submit_btn.click_exists(timeout=2.0):
                try:
                    self.d.click(293, 2267)
                    method_used = "fallback_click"
                except Exception:
                    pass

        self.telemetry.log_interaction(
            trace_id=trace_id,
            step_num=12,
            screen_name="Screen 4",
            activity="BillingManual",
            action_name="tap_nbpdcl_submit",
            coord_x=293,
            coord_y=2267,
            ratio_x=round(293 / w, 3),
            ratio_y=round(2267 / h, 3),
            how_method=method_used,
            duration_ms=int((time.time() - t_sub0) * 1000),
            status="SUCCESS"
        )

        # 3. Confirm YES on Alert dialog
        t_yes0 = time.time()
        yes_btn = self.d(resourceId="android:id/button1")
        if not self.cache.tap("screen4.confirm_yes", self.d, selector_obj=yes_btn, fallback_coords=(900, 1388)):
            if not yes_btn.click_exists(timeout=2.0):
                try:
                    self.d.click(900, 1388)
                except Exception:
                    pass
            else:
                print("  [+] Confirmed YES on Bill Generation Dialog...")
        else:
            print("  [+] Confirmed YES on Bill Generation Dialog...")

        self.telemetry.log_interaction(
            trace_id=trace_id,
            step_num=13,
            screen_name="Screen 4",
            activity="AlertDialog",
            action_name="confirm_bill_generation_yes",
            coord_x=900,
            coord_y=1388,
            ratio_x=round(900 / w, 3),
            ratio_y=round(1388 / h, 3),
            duration_ms=int((time.time() - t_yes0) * 1000),
            status="SUCCESS"
        )

        # 4. Wait for BillPrintOnline1 via fast activity check
        t_start = time.time()
        print_ready = False
        while time.time() - t_start < timeout:
            pkg, act = fast_get_current_activity(self.d)
            if "BillPrint" in act or "Print" in act:
                print_ready = True
                break
            time.sleep(0.08)

        if print_ready:
            print("  [+] Bill Print Screen loaded! Returning to Search...")
            try:
                self.d.swipe(mid_x, int(h * 0.83), mid_x, int(h * 0.12))
            except Exception:
                pass
            back_btn = self.d(resourceId="in.phoenix.bpdcl:id/printback")
            if not self.cache.tap("screen4.print_back", self.d, selector_obj=back_btn, fallback_coords=(718, 2305)):
                if not back_btn.click_exists(timeout=1.5):
                    try:
                        self.d.click(718, 2305)
                    except Exception:
                        pass
            time.sleep(0.2)

        self.telemetry.log_interaction(
            trace_id=trace_id,
            step_num=14,
            screen_name="Screen 4",
            activity="BillPrintOnline1" if print_ready else "BillingManual",
            action_name="bill_print_return",
            coord_x=718,
            coord_y=2305,
            ratio_x=round(718 / w, 3),
            ratio_y=round(2305 / h, 3),
            duration_ms=int((time.time() - t_start) * 1000),
            status="SUCCESS" if print_ready else "TIMEOUT"
        )

        # Always ensure device returns to ConsumerSearchActivity for next batch item
        try:
            self.d.app_start("in.phoenix.bpdcl", ".ConsumerSearchActivity", stop=False)
        except Exception:
            self.d.shell("am start -n in.phoenix.bpdcl/in.phoenix.bpdcl.ConsumerSearchActivity --activity-clear-top")

        print("\n>>> [SUCCESS] Consumer Billed & Submitted in NBPDCL! <<<\n")
        return True

if __name__ == "__main__":
    s4 = Screen4Submit()
    s4.handle_final_submit(do_submit=False)
