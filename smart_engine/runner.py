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
    def __init__(self, mru="8", cycle="OCT-2026", device_serial="192.168.9.40:5555", dry_run=False, final_submit=False):
        self.mru = str(mru)
        self.cycle = str(cycle)
        self.device_serial = device_serial
        self.dry_run = dry_run
        self.final_submit = final_submit

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

    def process_consumer(self, ca_number, reading_kwh=1355, meter_type="NORMAL"):
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
            return False, "pending"

        # Screen 2: Fill Form and Launch Camera
        if not self.s2.fill_form_and_launch_camera(meter_type=meter_type):
            print("  [!] Screen 2 Form failed.")
            return False, "doubt"

        # Screen 3: Camera Capture, Reading Entry & Doubt Resolver
        if not self.s3.handle_camera_and_review(reading_kwh=reading_kwh):
            print("  [!] Screen 3 Camera / Review failed.")
            return False, "doubt"

        # Screen 4: Final Submit or Stage-Only Reset
        if not self.s4.handle_final_submit(do_submit=self.final_submit):
            print("  [!] Screen 4 Submit / Reset failed.")
            return False, "doubt"

        total_time = round(time.time() - t0, 2)
        status = "submitted" if self.final_submit else "staged"
        print(f"\n>>> [SUCCESS] CA {ca_number} finished in {total_time}s (Status: {status})! <<<\n")
        return True, status

    def run_batch(self, limit=1):
        print(f"[+] Fetching automation queue (MRU: {self.mru}, Cycle: {self.cycle}, Limit: {limit})…")
        if not self.client:
            print("[!] NBPDCLClient not initialized.")
            return {"total": 0, "processed": 0, "failed": 0}

        queue = self.client.get_automation_queue(mru_id=self.mru, cycle=self.cycle, limit=limit)
        if not queue.get("success", False):
            print(f"[!] API call failed: {queue.get('message', 'unknown')}")
            return {"total": 0, "processed": 0, "failed": 0}

        consumers = queue.get("consumers", [])
        if not consumers:
            print("[+] Queue empty – nothing to do.")
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
            reading = entry.get("suggested_reading") or 1355

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
    parser.add_argument("--device", default="192.168.9.40:5555", help="Device serial / IP")
    parser.add_argument("--dry-run", action="store_true", help="Preview queue execution without hardware interaction")
    parser.add_argument("--final-submit", action="store_true", help="Execute final bill generation in NBPDCL (Default: Stage-Only)")
    args = parser.parse_args()

    runner = SmartRunner(
        mru=args.mru,
        cycle=args.cycle,
        device_serial=args.device,
        dry_run=args.dry_run,
        final_submit=args.final_submit
    )
    runner.run_batch(limit=args.limit)

if __name__ == "__main__":
    main()
