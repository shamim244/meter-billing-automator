"""
run_queue.py – Fetch next unsubmitted consumers from NBPDCL SaaS, run the ADB automation, read results, and push reviews back.

Usage: python run_queue.py --mru 8 --cycle 'OCT-2026' --limit 50
"""

import argparse
import json
import os
import sys
import time

# Ensure repository root and chat dir are on sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if CHAT_DIR not in sys.path:
    sys.path.insert(0, CHAT_DIR)

from nbpdcl_client import NBPDCLClient, build_review
# Import the original automation core.  It runs a single consumer with the `process_consumer_pipeline` function.
from automate_selections import process_consumer_pipeline

__all__ = ["main"]


def main():
    parser = argparse.ArgumentParser(description="Automation queue runner – NBPDCL SaaS + ADB code.")
    parser.add_argument("--mru", help="MRU code (optional)")
    parser.add_argument("--cycle", help="Cycle string (optional) – e.g. SEP-2026")
    parser.add_argument("--limit", type=int, default=25, help="Max consumers per batch")
    parser.add_argument("--dry-run", action="store_true", help="Preview queue without executing device automation or submitting reviews")
    args = parser.parse_args()

    client = NBPDCLClient()
    mru = args.mru or os.environ.get("NBPDCL_MRU_CODE")
    cycle = args.cycle or os.environ.get("NBPDCL_CYCLE")
    print(f"[+] Fetching automation queue (MRU: {mru}, Cycle: {cycle})…")
    queue = client.get_automation_queue(mru_id=mru, cycle=cycle, limit=args.limit)
    if not queue.get("success", False):
        print("[!] API failed: ", queue.get("message", "unknown"))
        sys.exit(1)

    consumers = queue.get("consumers", [])
    if not consumers:
        print("[+] Queue empty – nothing to do.")
        return

    print(f"[+] {len(consumers)} consumers fetched – processing…")

    processed = 0
    failed = 0
    reviews = []  # for batch sync at the end

    for idx, entry in enumerate(consumers, 1):
        ca = entry["ca_number"]
        name = entry.get("consumer_name", "")
        print(f"\n--- [{idx}/{len(consumers)}] CA={ca} ({name})---")

        working = entry.get("suggested_reading")
        basis = str(entry.get("billing_basis") or "").upper()
        meter_type = "DEFECTIVE" if basis in ["MD", "MB", "DEFECTIVE"] else "NORMAL"
        print(f"[*] Meter Type: {meter_type} (Billing Basis: {basis or 'OK'})")
        if meter_type == "NORMAL":
            print(f"[*] Suggested 4-Box Reading from SaaS: {working} KWH")
        else:
            print(f"[*] Defective Meter – Billed on Average Basis (0.0 OCR)")

        if args.dry_run:
            print(f"  [*] [DRY-RUN] Would process CA {ca} with reading={working}, meter_type={meter_type}")
            processed += 1
            continue

        # Run ADB pipeline end-to-end with injected suggested reading and meter type
        ok = process_consumer_pipeline(
            ca,
            reading_kwh=working,
            meter_type=meter_type,
            use_dump=True,
            auto_back=True,
            auto_submit=True
        )

        status = "submitted" if ok else "doubt"
        cycle_month = int(entry.get("billing_month") or queue.get("cycle_month", 8))
        cycle_year = int(entry.get("billing_year") or queue.get("cycle_year", 2026))

        # Immediate real-time update to SaaS platform
        try:
            client.submit_review(
                ca_number=ca,
                billing_month=cycle_month,
                billing_year=cycle_year,
                status=status,
                working_reading=working,
                remark=f"Auto-billed via ADB Bot ({meter_type})" if ok else "Pipeline interrupted",
            )
            print(f"  [✓] SaaS Ledger Synced: CA {ca} marked {status.upper()} (Reading: {working})")
        except Exception as e:
            print(f"  [!] Immediate status sync warning: {e}")

        # Build review payload for batch sync backup
        review = build_review(
            ca_number=ca,
            status=status,
            billing_month=cycle_month,
            billing_year=cycle_year,
            working_reading=working,
            reason_code=None if ok else "CHECK_MANUALLY",
            remark=f"Auto-billed via ADB Bot ({meter_type})" if ok else "Pipeline interrupted",
        )
        reviews.append(review)

        if ok:
            processed += 1
        else:
            failed += 1

    print(f"\n[+] Batch Run Finished: {processed} / {len(consumers)} submitted, {failed} doubtful.")

    # Batch upload the verdicts if we have any
    if reviews:
        print("[+] Submitting batch sync…")
        c_m = int(queue.get("cycle_month", 8))
        c_y = int(queue.get("cycle_year", 2026))
        try:
            resp = client.batch_sync(billing_month=c_m, billing_year=c_y, reviews=reviews)
            print("[✓] Batch sync result:", json.dumps(resp, indent=2))
        except Exception as exc:
            print("[✗] Batch sync failed:", exc)

if __name__ == "__main__":
    main()
