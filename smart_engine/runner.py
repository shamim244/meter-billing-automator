"""
runner.py – Ground-Truth Modular Smart Runner for NBPDCL Meter Billing.
Orchestrates Screen 1 (Search), Screen 2 (Form), Screen 3 (Camera & Review), and Screen 4 (Submit).
Optimized for high-throughput batch prefetching and sub-12s consumer cycles.
"""
import os
import sys
import time
import argparse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from chat.nbpdcl_client import NBPDCLClient, build_review
except ImportError:
    NBPDCLClient = None
    build_review = None

from smart_engine.screen1_search import Screen1Search
from smart_engine.screen2_form import Screen2Form
from smart_engine.screen3_camera import Screen3Camera
from smart_engine.screen4_submit import Screen4Submit

try:
    import uiautomator2 as u2
except ImportError:
    u2 = None

class SmartRunner:
    def __init__(self, mru="8", cycle="OCT-2026", device_serial="192.168.9.40:5555",
                 dry_run=False, final_submit=False, apply_tuning=False,
                 min_floor=None, max_ceiling=None, adjust_percent=None, ca=None):
        self.mru = str(mru)
        self.cycle = str(cycle)
        self.device_serial = device_serial
        self.dry_run = dry_run
        self.final_submit = final_submit
        self.apply_tuning = apply_tuning
        if min_floor is not None:
            self.min_floor = int(min_floor)
        elif os.environ.get("NBPDCL_MIN_FLOOR"):
            self.min_floor = int(os.environ.get("NBPDCL_MIN_FLOOR"))
        elif self.apply_tuning:
            self.min_floor = 125
        else:
            self.min_floor = None
        self.max_ceiling = int(max_ceiling) if max_ceiling is not None else None
        self.adjust_percent = float(adjust_percent) if adjust_percent is not None else None
        self.target_ca = str(ca).strip() if ca else None

        self.d = None
        if not dry_run:
            if u2 is None:
                raise RuntimeError("uiautomator2 required for live execution. Run 'pip install uiautomator2'.")
            print(f"[+] Connecting to device: {device_serial}...")
            self.d = u2.connect(device_serial)

        self.s1 = Screen1Search(device=self.d, serial=device_serial) if not dry_run else None
        self.s2 = Screen2Form(device=self.d, serial=device_serial) if not dry_run else None
        self.s3 = Screen3Camera(device=self.d, serial=device_serial) if not dry_run else None
        self.s4 = Screen4Submit(device=self.d, serial=device_serial) if not dry_run else None
        self.client = NBPDCLClient() if NBPDCLClient else None

        if not dry_run and self.d:
            try:
                self.d.screen_on()
                self.d.shell("svc power stayon true")
            except Exception:
                pass

    def ensure_device_unlocked(self, timeout=12.0):
        if self.dry_run or not self.d:
            return True
        try:
            self.d.screen_on()
        except Exception:
            pass

        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                out = self.d.shell("dumpsys window").output or ""
                if "iskeyguardshowing=true" not in out.lower():
                    return True
            except Exception:
                return True
            print("\n" + "!" * 60)
            print(" [⚠️ ACTION REQUIRED] Android device screen is LOCKED!")
            print(" Please unlock your phone screen so automation can proceed...")
            print("!" * 60 + "\n")
            time.sleep(1.5)

        print("[!] Timed out waiting for device unlock.")
        return False

    def _reset_to_search(self):
        try:
            if hasattr(self, 'd') and self.d:
                btn1 = self.d(resourceId="android:id/button1")
                if btn1.exists(timeout=0.1):
                    btn1.click()
                self.d.shell("am start -n in.phoenix.bpdcl/in.phoenix.bpdcl.ConsumerSearchActivity --activity-clear-top")
                time.sleep(0.3)
        except Exception:
            pass

    def process_consumer(self, ca_number, reading_kwh=1355, meter_type="NORMAL"):
        if not self.ensure_device_unlocked():
            return False, "doubt"
        t0 = time.time()
        print(f"\n{'='*60}")
        print(f" [*] [SMART RUNNER] CA: {ca_number} | Meter: {meter_type} | Reading: {reading_kwh} KWH")
        mode = "DRY-RUN" if self.dry_run else ("FINAL SUBMIT" if self.final_submit else "STAGE-ONLY (Safe Mode)")
        print(f" [*] Execution Mode: {mode}")
        print(f"{'='*60}")

        if self.dry_run:
            print(f"  [*] [DRY-RUN] Simulated pipeline for CA {ca_number} -> Success")
            return True, "submitted"

        # Screen 1: Fast Search CA and wait for BillingManual
        if not self.s1.search_consumer(ca_number):
            print("  [!] Screen 1 Search failed.")
            self._reset_to_search()
            return False, "pending"

        # Screen 2: Fill Form and Launch Camera
        if not self.s2.fill_form_and_launch_camera(meter_type=meter_type):
            print("  [!] Screen 2 Form failed.")
            self._reset_to_search()
            return False, "doubt"

        # Screen 3: Camera Capture, Reading Entry & Doubt Resolver
        if not self.s3.handle_camera_and_review(reading_kwh=reading_kwh):
            print("  [!] Screen 3 Camera / Review failed.")
            self._reset_to_search()
            return False, "doubt"

        # Screen 4: Final Submit or Stage-Only Reset
        if not self.s4.handle_final_submit(do_submit=self.final_submit):
            print("  [!] Screen 4 Submit / Reset failed.")
            self._reset_to_search()
            return False, "doubt"

        total_time = round(time.time() - t0, 2)
        status = "submitted" if self.final_submit else "staged"
        print(f"\n>>> [SUCCESS] CA {ca_number} finished in {total_time}s (Status: {status})! <<<\n")
        return True, status

    def run_batch(self, limit=1):
        target_str = f" | Target CA: {self.target_ca}" if self.target_ca else ""
        print(f"[+] Fetching automation queue (MRU: {self.mru}, Cycle: {self.cycle}, Limit: {limit}{target_str})…")
        if not self.client:
            print("[!] NBPDCLClient not initialized.")
            return {"total": 0, "processed": 0, "failed": 0}

        if self.apply_tuning:
            print(f"[+] Tuning Active: Floor={self.min_floor or 'Auto/Consumer'}, Ceiling={self.max_ceiling or 'None'}, Adj={self.adjust_percent or 0}%")

        queue = self.client.get_automation_queue(
            mru_id=self.mru,
            cycle=self.cycle,
            limit=limit,
            apply_tuning=self.apply_tuning,
            min_units_floor=self.min_floor,
            max_units_ceiling=self.max_ceiling,
            adjustment_percent=self.adjust_percent,
            ca=self.target_ca
        )
        if not queue.get("success", False):
            print(f"[!] API call failed: {queue.get('message', 'unknown')}")
            return {"total": 0, "processed": 0, "failed": 0}

        consumers = queue.get("consumers", [])
        if self.target_ca:
            matched = [c for c in consumers if str(c.get("ca_number")).strip() == self.target_ca]
            if matched:
                consumers = matched
            else:
                retry_q = self.client.get_automation_queue(
                    mru_id=self.mru,
                    cycle=self.cycle,
                    limit=250,
                    apply_tuning=self.apply_tuning,
                    min_units_floor=self.min_floor,
                    max_units_ceiling=self.max_ceiling,
                    adjustment_percent=self.adjust_percent,
                    ca=self.target_ca
                )
                retry_consumers = retry_q.get("consumers", [])
                matched = [c for c in retry_consumers if str(c.get("ca_number")).strip() == self.target_ca]
                if matched:
                    consumers = matched
                else:
                    lb = self.client.list_bills(search=self.target_ca, month=10, year=2026)
                    lb_data = lb.get("data", [])
                    matched_lb = [b for b in lb_data if str(b.get("ca_number")).strip() == self.target_ca]
                    if matched_lb:
                        b = matched_lb[0]
                        consumers = [{
                            "bill_id": b.get("id"),
                            "ca_number": b.get("ca_number"),
                            "consumer_name": b.get("consumer_name"),
                            "meter_number": b.get("meter_no"),
                            "billing_basis": b.get("billing_basis") or "NORMAL",
                            "previous_reading": b.get("previous_reading"),
                            "working_reading": b.get("working_reading"),
                            "base_avg_units": b.get("base_avg_units") or b.get("smart_average_kwh") or 50,
                            "smart_average_kwh": b.get("smart_average_kwh") or 50,
                            "suggested_reading": b.get("working_reading") or b.get("suggested_reading"),
                            "min_avg_units": b.get("min_avg_units"),
                            "is_clamped_min": True if b.get("min_avg_units") else False,
                            "review_status": b.get("review_status")
                        }]
                    else:
                        print(f"[!] Target CA {self.target_ca} not found in MRU {self.mru} cycle {self.cycle}.")
                        return {"total": 0, "processed": 0, "failed": 0}

        print(f"[+] {len(consumers)} consumers fetched from SaaS – running fast modular pipeline…")
        processed = 0
        failed = 0
        reviews = []
        batch_t0 = time.time()

        for idx, entry in enumerate(consumers, 1):
            ca = entry["ca_number"]
            name = entry.get("consumer_name", "")
            basis = str(entry.get("billing_basis") or "").upper()
            meter_type = "DEFECTIVE" if basis == "MD" else "NORMAL"
            reading = entry.get("suggested_reading")
            prev = int(entry.get("previous_reading") or 0)
            base_avg = int(entry.get("base_avg_units") or entry.get("smart_average_kwh") or 50)

            if self.apply_tuning:
                indiv_min = entry.get("min_avg_units")
                effective_floor = int(indiv_min) if (indiv_min is not None and int(indiv_min) > 0) else (self.min_floor or 125)

                if entry.get("is_clamped_min"):
                    tuned_avg = entry.get("tuned_avg_units") or effective_floor
                    print(f"  [*] Min Floor Clamped: Base {base_avg} kWh -> Tuned {tuned_avg} kWh (Reading: {reading})")
                elif base_avg < effective_floor:
                    tuned_avg = effective_floor
                    sug = entry.get("suggested_reading") or entry.get("working_reading")
                    if sug and int(sug) > base_avg:
                        reading = int(sug) - base_avg + tuned_avg
                    else:
                        reading = (prev if prev > 0 else 0) + tuned_avg
                    print(f"  [*] Min Floor Clamped: Base {base_avg} kWh -> Tuned {tuned_avg} kWh (Reading: {reading})")
                elif reading is None:
                    reading = prev + base_avg
            else:
                if reading is None:
                    reading = entry.get("working_reading") or (prev + base_avg if prev > 0 else 1355)

            if entry.get("is_clamped_max"):
                print(f"  [*] Max Ceiling Clamped: Base {entry.get('base_avg_units')} kWh -> Tuned {entry.get('tuned_avg_units')} kWh (Reading: {reading})")

            print(f"\n--- [{idx}/{len(consumers)}] CA={ca} ({name}) ---")
            ok, status = self.process_consumer(ca, reading_kwh=reading, meter_type=meter_type)

            if ok:
                processed += 1
            else:
                failed += 1

            if not self.dry_run and build_review and self.final_submit:
                rev = build_review(
                    ca_number=ca,
                    status=status,
                    billing_month=10,
                    billing_year=2026,
                    working_reading=reading
                )
                reviews.append(rev)

                # Immediate real-time sync to SaaS API so dashboard updates instantly
                if self.client and ok:
                    try:
                        self.client.submit_review(
                            ca_number=ca,
                            billing_month=10,
                            billing_year=2026,
                            status=status,
                            working_reading=reading,
                            remark="Billed via Smart Engine V2"
                        )
                        print(f"  [✓] SaaS API updated immediately: CA {ca} -> {status} (Reading: {reading})")
                    except Exception as e:
                        print(f"  [!] Real-time sync note: {e}")

        if reviews and self.client:
            print("\n[+] Syncing batch ledger with SaaS API...")
            res = self.client.submit_batch_sync(reviews)
            print(f"[✓] SaaS Sync complete: {res.get('synced_count', 0)} synced.")

        batch_elapsed = round(time.time() - batch_t0, 2)
        avg_speed = round(batch_elapsed / max(processed, 1), 2)
        print(f"\n{'='*60}")
        print(f"[+] Batch Finished: {processed}/{len(consumers)} in {batch_elapsed}s (Avg: {avg_speed}s/meter, {failed} failed)")
        print(f"{'='*60}\n")
        return {"total": len(consumers), "processed": processed, "failed": failed, "elapsed_seconds": batch_elapsed}

def main():
    parser = argparse.ArgumentParser(description="Smart Engine V2 - Ground-Truth High-Speed Runner")
    parser.add_argument("--mru", default="8", help="Target MRU code")
    parser.add_argument("--cycle", default="OCT-2026", help="Billing cycle")
    parser.add_argument("--limit", type=int, default=1, help="Max consumers to process")
    parser.add_argument("--ca", default=None, help="Target a specific consumer account number")
    parser.add_argument("--device", default="192.168.9.40:5555", help="Device serial / IP")
    parser.add_argument("--dry-run", action="store_true", help="Preview queue execution without hardware interaction")
    parser.add_argument("--final-submit", action="store_true", help="Execute final bill generation in NBPDCL (Default: Stage-Only)")
    parser.add_argument("--apply-tuning", action="store_true", help="Apply batch smart average tuning to suggested reading (Default: False - pure baseline)")
    parser.add_argument("--min-floor", type=int, default=None, help="Minimum average consumption floor (kWh) for batch tuning")
    parser.add_argument("--max-ceiling", type=int, default=None, help="Maximum average consumption ceiling (kWh)")
    parser.add_argument("--adjust-percent", type=float, default=None, help="Batch tuning adjustment percent")
    args = parser.parse_args()

    runner = SmartRunner(
        mru=args.mru,
        cycle=args.cycle,
        device_serial=args.device,
        dry_run=args.dry_run,
        final_submit=args.final_submit,
        apply_tuning=args.apply_tuning,
        min_floor=args.min_floor,
        max_ceiling=args.max_ceiling,
        adjust_percent=args.adjust_percent,
        ca=args.ca
    )
    runner.run_batch(limit=args.limit)

if __name__ == "__main__":
    main()
