# Dynamic uiautomator2 Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate automation breakages across all batch pipeline screens by replacing hardcoded blind coordinate taps with fully dynamic `uiautomator2` node finding, verified text entry, scroll-into-view handling, and adaptive camera retry recovery.

**Architecture:** 
- In Screen 1 (`screen1_search.py`), ensure input sanitization and verify CA string in the input field prior to search execution to prevent "input data is invalid" errors.
- In Screen 2 (`screen2_form.py`), dynamically trigger dropdown popups and click target option text nodes (`NORMAL`, `OK`, `Inside`) directly. Wait for `PresentStatus1` expansion, dynamically locate `KwhCaptureButton`, scroll it into view if below the fold, and click the node.
- In Screen 3 (`screen3_camera.py`), increase camera attempts to 5, dismiss angle/clear-image alerts cleanly, allow a 1.2s stabilization buffer for camera ML sensor reset before retrying shutter, and safely inject readings.
- In Runner & SaaS sync (`runner.py`), preserve immediate per-consumer submission sync.

**Tech Stack:** Python 3.13, `uiautomator2`, Android ADB, `unittest`.

**Spec:** User directive: "may i think you are not using properly uiautomatror2. we have think as not be 100% same step there some are dinimic as per the flow now we have to prepare for every uncertainity".

## Global Constraints
- Do not use hardcoded blind coordinates where dynamic `uiautomator2` element nodes are available.
- Retain moderate, balanced speed: maintain 150-350ms UI settlement buffers; no 0ms drops.
- Always verify text fields match the expected value before proceeding.
- All unit tests must pass (`python -m unittest discover tests`).

## Review Focus
1. Screen 1 search input concatenation: previous digits leaking into subsequent consumer CA input.
2. Screen 2 `KwhCaptureButton` off-screen: button hidden or scrolled below fold on varying screen heights.
3. Screen 2 Site Observation dropdown: `OK` option position differing or requiring scrolling.
4. Screen 3 Camera angle alert loop: rapid retries within 0.3s re-triggering ML angle rejection.
5. `uiautomator2` connection stability: handling camera launch without unhandled exceptions.

---

### Task 1: Sanitize and Verify Search Input in Screen 1

**Files:**
- Modify: `smart_engine/screen1_search.py`
- Test: `tests/test_screen1_search.py`

**Interfaces:**
- Consumes: `Screen1Search.search_consumer(ca_number: str, timeout: float = 8.0) -> bool`
- Produces: Reliable transition to `BillingManual` with zero invalid CA input alerts.

- [ ] **Step 1: Write unit test verifying input sanitation and validation**
  Ensure test checks that `search_consumer` clears field, verifies entered text matches `ca_number`, and handles alert dialogs.

- [ ] **Step 2: Run test to observe baseline**
  Run: `python -m unittest tests/test_screen1_search.py`

- [ ] **Step 3: Implement input sanitization and verification in `screen1_search.py`**
  - Clear field with both `clear_text()` and explicit backspace sequence.
  - Set text and verify `input_field.get_text() == str(ca_number)`.
  - If mismatch, re-clear and inject via shell input.
  - Check and dismiss any pre-existing or post-search alerts cleanly.

- [ ] **Step 4: Run test to verify it passes**
  Run: `python -m unittest tests/test_screen1_search.py`

- [ ] **Step 5: Commit**
  ```bash
  git add smart_engine/screen1_search.py tests/test_screen1_search.py
  git commit -m "fix(screen1): sanitize search input and verify CA before submission"
  ```

---

### Task 2: Dynamic Element Lookup & Robust Selection in Screen 2

**Files:**
- Modify: `smart_engine/screen2_form.py`
- Test: `tests/test_screen2_form.py`

**Interfaces:**
- Consumes: `Screen2Form.fill_form_and_launch_camera(meter_type: str = "NORMAL", timeout: float = 8.0) -> bool`
- Produces: Reliable selection of `NORMAL`/`METER DEFECTIVE`, `OK`, and `Inside`, followed by dynamic scroll & click of `KwhCaptureButton`.

- [ ] **Step 1: Write unit test for dynamic form filling and button click**
  Verify selection flow clicks text nodes directly and scrolls `KwhCaptureButton` into view if needed.

- [ ] **Step 2: Run test to verify test structure**
  Run: `python -m unittest tests/test_screen2_form.py`

- [ ] **Step 3: Implement dynamic selections and scroll-to-button in `screen2_form.py`**
  - Click `PresentStatus1` dropdown arrow; wait for `d(text="NORMAL")` (or defective option) to appear; click the text node directly.
  - Verify `PresentStatus1` text equals target status.
  - Check `atMOBS1`: if not "OK", click dropdown arrow, swipe/scroll ListView to locate `d(text="OK")`, click it, and verify `atMOBS1.get_text() == "OK"`.
  - Check `meterloctypeiv`: if not "Inside", click dropdown arrow, click `d(text="Inside")`, verify `meterloctypeiv.get_text() == "Inside"`.
  - Locate `KwhCaptureButton`: if not visible or bounds `top > 2250`, scroll down `ScrollView01` until button is clearly visible.
  - Click `KwhCaptureButton` directly via `d(resourceId="in.phoenix.bpdcl:id/KwhCaptureButton").click()`.
  - Wait for MR Bharat (`MeterReadingActivity` or `ScanMeterActivity`) to focus.

- [ ] **Step 4: Run test to verify it passes**
  Run: `python -m unittest tests/test_screen2_form.py`

- [ ] **Step 5: Commit**
  ```bash
  git add smart_engine/screen2_form.py tests/test_screen2_form.py
  git commit -m "fix(screen2): implement dynamic dropdown node selection and scroll-to-capture"
  ```

---

### Task 3: Resilient Camera Retry Loop & Sensor Stabilization in Screen 3

**Files:**
- Modify: `smart_engine/screen3_camera.py`
- Test: `tests/test_screen3_camera.py`

**Interfaces:**
- Consumes: `Screen3Camera.handle_camera_and_review(reading_kwh: int = 1355, timeout: float = 25.0) -> bool`
- Produces: Successful capture, reading entry, doubt override, and return to `BillingManual`.

- [ ] **Step 1: Write unit test for resilient camera retries and alert recovery**
  Verify camera retry loop dismisses angle alerts and waits before re-triggering shutter.

- [ ] **Step 2: Run test to observe baseline**
  Run: `python -m unittest tests/test_screen3_camera.py`

- [ ] **Step 3: Implement sensor stabilization and retry loop in `screen3_camera.py`**
  - Increase retry attempts from 3 to 5.
  - When alert appears (`Please move RIGHT from meter to capture!`, `Please capture clear meter image!`, etc.): dismiss it via `d(resourceId="android:id/button1")` or `d(text="OK")`.
  - Wait 1.0 - 1.2s after alert dismissal so camera sensor/autofocus re-arms before clicking shutter again.
  - Once reading dialog appears, clear input field, set reading, verify reading entered, and tap `Save`.
  - Watch for secondary confirmation dialogs and revalidation/doubt overrides.

- [ ] **Step 4: Run test to verify it passes**
  Run: `python -m unittest tests/test_screen3_camera.py`

- [ ] **Step 5: Commit**
  ```bash
  git add smart_engine/screen3_camera.py tests/test_screen3_camera.py
  git commit -m "fix(screen3): harden camera retry loop with sensor stabilization buffer"
  ```

---

### Task 4: Full Suite Verification & Live Dry-Run

**Files:**
- Run: `python -m unittest discover tests`
- Live Test: `python -u smart_engine/runner.py --mru 8 --cycle OCT-2026 --limit 2 --apply-tuning` (Safe mode without `--final-submit` first)

- [ ] **Step 1: Run all unit tests**
  Verify 100% of tests pass cleanly.

- [ ] **Step 2: Execute live test on connected device**
  Verify 2 consecutive consumers process smoothly through Screen 1 -> Screen 2 -> Screen 3 without any timeout or selection error.

- [ ] **Step 3: Final Commit and Tag**
  ```bash
  git commit -am "feat: fully dynamic uiautomator2 automation engine verified"
  git tag -a "dynamic-u2-v1" -m "Verified dynamic uiautomator2 pipeline"
  ```
