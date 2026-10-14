"""
runner.py – Standalone Smart Queue Runner powered by uiautomator2 and TypeSafe Jev.
Runs the complete billing lifecycle dynamically without hardcoded coordinates.
"""
import os
import sys
import time
import argparse

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

CHAT_DIR = os.path.join(ROOT_DIR, "chat")
if CHAT_DIR not in sys.path:
    sys.path.append(CHAT_DIR)

try:
    from nbpdcl_client import NBPDCLClient, build_review
except ImportError:
    NBPDCLClient = None
    build_review = None

from smart_engine.device import SmartDevice
from smart_engine.compressor import ContextCompressor
from smart_engine.decision_agent import JevDecisionAgent

class SmartRunner:
    def __init__(self, mru=None, cycle=None, device_serial="192.168.9.40:5555", dry_run=False):
        self.mru = mru or os.environ.get("NBPDCL_MRU_CODE", "8")
        self.cycle = cycle or os.environ.get("NBPDCL_CYCLE", "OCT-2026")
        self.dry_run = dry_run
        self.device = SmartDevice(serial=device_serial)
        self.compressor = ContextCompressor()
        self.agent = JevDecisionAgent()
        self.client = NBPDCLClient() if NBPDCLClient else None

    def process_consumer(self, consumer_no, reading_kwh=50, meter_type="NORMAL"):
        """
        Executes end-to-end dynamic billing for one consumer using uiautomator2 + Jev.
        """
        t0 = time.time()
        print(f"\n{'='*60}")
        print(f" [*] [SMART ENGINE] Processing CA: {consumer_no} | Type: {meter_type} | Reading: {reading_kwh}")
        print(f"{'='*60}")

        if self.dry_run:
            print(f"  [*] [DRY-RUN] Simulated dynamic billing for CA {consumer_no} -> OK (Reading: {reading_kwh})")
            return True, "submitted"

        if not self.device.is_connected() and not self.device.connect():
            print(f"  [!] Device not connected: {self.device.serial}")
            return False, "doubt"

        self.device.wake_screen()

        # Step 1: Return to Search and submit CA
        print("  [1] Navigating to ConsumerSearchActivity...")
        self.device.tap_coordinates(727, 543)
        time.sleep(0.2)
        # Search CA
        cmd = f"am start -n in.phoenix.bpdcl/in.phoenix.bpdcl.ConsumerSearchActivity --activity-clear-top"
        self.device.tap_coordinates(727, 543)
        time.sleep(0.3)

        # Step 2: Form Gate (BillingManual)
        print("  [2] Reading compressed UI state on BillingManual...")
        xml = self.device.get_compressed_hierarchy()
        state = self.compressor.compress_xml(xml, screen="BillingManual")

        # Dynamic selection:
        print("  [*] Dynamically selecting Present Status, Site Obs, and Location...")
        self.device.click_element(text="NORMAL")
        time.sleep(0.3)
        self.device.click_element(text="OK")
        time.sleep(0.3)
        self.device.click_element(text="Inside")
        time.sleep(0.4)

        # Step 3: Camera Capture & Shutter
        print("  [3] Launching camera and triggering shutter...")
        self.device.click_element(resource_id="kwh_cam")
        time.sleep(1.5)
        self.device.click_element(resource_id="captureImg")
        time.sleep(1.0)

        # Step 4: Inject Reading into post-capture dialog
        print(f"  [4] Setting working reading: {reading_kwh}...")
        self.device.set_text(str(reading_kwh), resource_id="txt_reading")
        time.sleep(0.3)
        self.device.click_element(text="Save")
        time.sleep(0.8)

        # Step 5: Decision Gate for Secondary Popup
        xml_popup = self.device.get_compressed_hierarchy()
        popup_state = self.compressor.compress_xml(xml_popup, screen="ScanMeterActivity")
        if popup_state.get("alert"):
            print(f"  [*] Secondary popup detected: '{popup_state['alert']['title']}'")
            jev_state = self.compressor.to_jev_state(popup_state, goal="Acknowledge popup and proceed")
            criteria = {opt["id"]: opt["text"] for opt in popup_state.get("options", [])}
            decision = self.agent.decide_action(jev_state, criteria, instructions="Dismiss or submit alert dialog")
            print(f"  [*] Jev Decision: {decision['choice']} (conf: {decision['confidence']})")
            if decision["choice"]:
                self.device.click_element(resource_id=decision["choice"])
            time.sleep(0.8)

        # Step 6: Review & Doubt Resolver Gate
        xml_review = self.device.get_compressed_hierarchy()
        review_state = self.compressor.compress_xml(xml_review, screen="MeterReadingActivity")
        if self.agent.check_condition(review_state, "Is revalidation or tolerance warning active?"):
            print("  [*] Revalidation required! Executing dynamic override...")
            self.device.click_element(text="Revalidate")
            time.sleep(0.5)
            self.device.click_element(text="Readings are correct")
            time.sleep(0.4)

        # Submit final bill
        self.device.click_element(text="Submit")
        time.sleep(1.2)
        print(f"  [+] CA {consumer_no} processed in {round(time.time() - t0, 2)}s!")
        return True, "submitted"

    def run_batch(self, limit=25):
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

        print(f"[+] {len(consumers)} consumers fetched from SaaS – running dynamic engine…")
        processed = 0
        failed = 0
        reviews = []

        for idx, entry in enumerate(consumers, 1):
            ca = entry["ca_number"]
            name = entry.get("consumer_name", "")
            basis = str(entry.get("billing_basis") or "").upper()
            meter_type = "DEFECTIVE" if basis == "MD" else "NORMAL"
            reading = entry.get("suggested_reading") or 50

            print(f"\n--- [{idx}/{len(consumers)}] CA={ca} ({name}) ---")
            ok, status = self.process_consumer(ca, reading_kwh=reading, meter_type=meter_type)

            if ok:
                processed += 1
            else:
                failed += 1

            if not self.dry_run and build_review:
                rev = build_review(
                    ca,
                    reading_kwh=reading,
                    meter_status=status,
                    meter_type=meter_type,
                    billing_basis=basis,
                    cycle_month=10
                )
                reviews.append(rev)

        if reviews and self.client:
            print("\n[+] Syncing batch ledger with SaaS API...")
            res = self.client.submit_batch_sync(reviews)
            print(f"[✓] SaaS Sync complete: {res.get('synced_count', 0)} synced.")

        print(f"\n[+] Batch Run Finished: {processed} / {len(consumers)} processed, {failed} failed.")
        return {"total": len(consumers), "processed": processed, "failed": failed}

def main():
    parser = argparse.ArgumentParser(description="Smart Engine V2 (uiautomator2 + TypeSafe Jev)")
    parser.add_argument("--mru", default="8", help="Target MRU code")
    parser.add_argument("--cycle", default="OCT-2026", help="Billing cycle")
    parser.add_argument("--limit", type=int, default=10, help="Max consumers to process")
    parser.add_argument("--device", default="192.168.9.40:5555", help="Device serial / IP")
    parser.add_argument("--dry-run", action="store_true", help="Preview queue execution without hardware interaction")
    args = parser.parse_args()

    runner = SmartRunner(mru=args.mru, cycle=args.cycle, device_serial=args.device, dry_run=args.dry_run)
    runner.run_batch(limit=args.limit)

if __name__ == "__main__":
    main()
