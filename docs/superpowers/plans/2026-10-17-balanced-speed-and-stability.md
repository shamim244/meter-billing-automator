# Balanced Speed and Workflow Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a balanced, moderate automation speed (~15–20s per meter) across all 4 screens that eliminates dropped taps and race conditions while guaranteeing immediate per-consumer SaaS API synchronization.

**Architecture:** Replace reckless 0ms polling and high-overhead `dumpsys` calls with deterministic 200–350ms UI animation settlement buffers and fast in-memory element checks (`d(resourceId=...).exists`), paired with immediate per-meter REST sync (`/bills/review`).

**Tech Stack:** Python 3, `uiautomator2`, Android ADB over TCP/IP, Laravel REST API v1 (`NBPDCLClient`).

**Spec:** User directive: "Speed is very important, but we can't afford the tool breaking and workflow broken due to the speed. We have to balance more... now our priority is moderate, balance."

---

## Global Constraints
- Target device: `192.168.9.40:5555`.
- Target MRU: `8`, Cycle: `OCT-2026`.
- Minimum floor: `125 kWh` guaranteed when `--apply-tuning` is active.
- Never use repeated `d.app_current()` dumpsys in tight loops (causes 1.5–7s Wi-Fi ADB network stalls).
- Always include safe 200–350ms animation settlement pauses when opening/closing spinners and dialogs.
- Always sync each completed meter immediately to the SaaS database via `client.submit_review()`.
- Safe rollback checkpoint: `speed-sync-v2` tag in Git.

---

## Review Focus
1. **Screen 2 Dropdown Transition:** Rapid clicks while previous spinner is closing get discarded by Android window manager -> Added 250ms settlement pause.
2. **Screen 2 NoneType crash:** `get_text()` returns `None` on unpopulated accessibility nodes -> Coerced with `(get_text() or "")`.
3. **Screen 3 Revalidation Dialog Race:** MR Bharat takes 3–5s to process OCR and revalidation remarks -> Watchdog loop with dynamic reset and generic AlertDialog button detection.
4. **Immediate API Sync Failure:** Script stopped mid-batch leaves previous meters un-synced -> Real-time atomic patch call per consumer.
5. **Screen 1 Search Residue:** Old digits in search field cause "Invalid CA" NBPDCL alert -> Chained clear and set sequence.

---

## Tasks

### Task 1: Screen 1 Moderate Search Pacing & GPS Settlement
**Files:**
- Modify: `smart_engine/screen1_search.py`
- Test: `tests/test_screen1_search.py`

**Interfaces:**
- Consumes: `ca_number: str`
- Produces: `search_consumer(ca_number: str, timeout: float = 8.0) -> bool`

- [ ] **Step 1: Write test for Screen 1 safe settlement buffer**
Ensure `search_consumer` sends the clear-type-search sequence and verifies `PresentStatus1` appears without `app_current` lag.
- [ ] **Step 2: Implement balanced pacing in `smart_engine/screen1_search.py`**
Include a 250ms post-search settlement pause to let NBPDCL's modal GPS check dismiss cleanly.
- [ ] **Step 3: Run unit tests**
Run: `python -m unittest tests/test_screen1_search.py`
Expected: `Ran 2 tests in ... OK`
- [ ] **Step 4: Commit checkpoint**
`git commit -am "feat(screen1): moderate search pacing with clean GPS settlement"`

---

### Task 2: Screen 2 Form Pacing & Defensive Dropdown Handling
**Files:**
- Modify: `smart_engine/screen2_form.py`
- Test: `tests/test_screen2_form.py`

**Interfaces:**
- Consumes: `meter_type: str = "NORMAL"`
- Produces: `fill_form_and_launch_camera(meter_type: str = "NORMAL", timeout: float = 8.0) -> bool`

- [ ] **Step 1: Write test for Screen 2 NoneType protection & settlement delays**
Verify `ps_btn`, `obs_btn`, and `loc_btn` handle `None` text gracefully and execute safe delays between dropdown interactions.
- [ ] **Step 2: Implement balanced pacing in `smart_engine/screen2_form.py`**
- Bypass `PresentStatus1` if already `NORMAL`. If clicked, wait 200ms before selecting.
- Check `atMOBS1`: If already `OK`, bypass. If clicked, use DPAD / text selection with 200ms pause.
- Check `meterloctypeiv`: If already `Inside`, bypass.
- Tap `KwhCaptureButton`: Wait 250ms after dropdown closure before clicking; verify launch with fast in-memory element poll.
- [ ] **Step 3: Run unit tests**
Run: `python -m unittest tests/test_screen2_form.py`
Expected: `Ran 3 tests in ... OK`
- [ ] **Step 4: Commit checkpoint**
`git commit -am "feat(screen2): balanced form filling with safe animation settlement"`

---

### Task 3: Screen 3 MR Bharat Camera, Reading Entry & Multi-Dialog Watcher
**Files:**
- Modify: `smart_engine/screen3_camera.py`
- Test: `tests/test_screen3_camera.py`

**Interfaces:**
- Consumes: `reading_kwh: int = 1355`
- Produces: `handle_camera_and_review(reading_kwh: int = 1355, timeout: float = 25.0) -> bool`

- [ ] **Step 1: Write test for Screen 3 revalidation & return detection**
Verify camera shutter retries, input field injection with clear-keyevents, confirmation popup handling, and instant BillingManual return detection.
- [ ] **Step 2: Implement balanced review watcher in `smart_engine/screen3_camera.py`**
- Set 300ms pause after shutter tap to allow OCR dialog to stabilize.
- Ensure clear text -> input reading -> dismiss keyboard -> tap Save.
- In multi-dialog watcher: detect any AlertDialog confirmation (`android:id/button1`), execute revalidation override sequence with 250ms step delays.
- Detect return to BillingManual via fast in-memory element check (`PresentStatus1` / `KwhCaptureButton`).
- [ ] **Step 3: Run unit tests**
Run: `python -m unittest tests/test_screen3_camera.py`
Expected: `Ran 4 tests in ... OK`
- [ ] **Step 4: Commit checkpoint**
`git commit -am "feat(screen3): balanced camera review watcher with safe revalidation pacing"`

---

### Task 4: Screen 4 NBPDCL Submission & Real-Time SaaS Sync
**Files:**
- Modify: `smart_engine/screen4_submit.py`
- Modify: `smart_engine/runner.py`
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `do_submit: bool = True`
- Produces: `handle_final_submit(do_submit: bool) -> bool`, immediate SaaS API sync via `client.submit_review()`

- [ ] **Step 1: Write test for immediate per-consumer sync in runner**
Verify `client.submit_review()` is called immediately when `process_consumer` completes with `status == "submitted"`.
- [ ] **Step 2: Implement balanced Screen 4 submit & real-time sync**
- Swipe to bottom of BillingManual -> Tap Submit -> 250ms pause -> Confirm YES on dialog.
- Fast wait for BillPrintOnline1 screen via `printback` element check.
- Tap Back to reset to `ConsumerSearchActivity`.
- In `runner.py`: immediately trigger `client.submit_review()` for the CA.
- [ ] **Step 3: Run full unit test suite**
Run: `python -m unittest discover tests`
Expected: `Ran 31 tests ... OK`
- [ ] **Step 4: Commit checkpoint**
`git commit -am "feat(screen4): balanced submission with real-time per-meter SaaS sync"`

---

### Task 5: Live 1-Consumer Verification & Queue Validation
**Verification Steps:**
- [ ] **Step 1: Run dry-run batch to verify tuned readings**
Run: `python -u smart_engine/runner.py --mru 8 --cycle OCT-2026 --limit 2 --apply-tuning --dry-run`
Verify all consumers reflect minimum 125 kWh floor.
- [ ] **Step 2: Run single live consumer submit**
Run: `python -u smart_engine/runner.py --mru 8 --cycle OCT-2026 --limit 1 --apply-tuning --final-submit`
Verify:
1. Screen 1 searches and settles smoothly.
2. Screen 2 bypasses or fills fields without dropped taps.
3. Screen 3 captures image, enters tuned reading, overrides revalidation.
4. Screen 4 submits bill and immediately syncs to SaaS dashboard.
- [ ] **Step 3: Confirm SaaS database record**
Verify `client.list_bills()` confirms `submitted` status and exact reading.
