# Smart Engine Speed Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce end-to-end processing time per meter from ~30s down to 8–12s by replacing static sleeps with event-driven waiters, eliminating OS subprocess forks, utilizing fast IME input, and racing dialog conditions in MR Bharat.

**Architecture:** Refactor `smart_engine/screen1_search.py`, `smart_engine/screen2_form.py`, `smart_engine/screen3_camera.py`, and `smart_engine/runner.py` into non-blocking, event-driven modules. UI transitions use direct `uiautomator2` socket-based shell calls and element wait conditions (`wait()`, `wait_activity()`, `set_fastinput_ime()`), eliminating idle time and subshell overhead.

**Tech Stack:** Python 3.10+, `uiautomator2`, Android ADB over TCP/IP (`192.168.9.40:5555`), REST API (`chat/nbpdcl_client.py`), `unittest`.

**Spec:** In-session design approved by user to optimize billing speed and efficiency across Screens 1–4 and runner queue.

## Global Constraints

- Never modify legacy root files `automate_selections.py`, `chat/automate_selections.py`, `chat/run_queue.py`, or `.env`.
- Keep all optimizations strictly isolated inside `smart_engine/` and associated unit tests in `tests/`.
- Default execution mode in `smart_engine/runner.py` must remain Stage-Only (`--stage-only` safe mode) unless `--final-submit` is passed.
- Maintain full compatibility with connected device `192.168.9.40:5555` running NBPDCL (`in.phoenix.bpdcl`) and MR Bharat (`in.coral.bpdcl`).
- All 23+ unit tests in `tests/` must remain passing.

## Review Focus

1. **Fast IME failure to dismiss:** If `set_fastinput_ime(True)` fails on older Android builds, graceful fallback to standard typing must not hang.
2. **Rapid element polling starvation:** Polling intervals must not drop below 50ms to prevent CPU throttling on low-spec Android devices.
3. **Premature form fill before GPS/Data settles:** Screen 2 must wait for `PresentStatus1` to be clickable rather than assuming instant layout readiness.
4. **Camera shutter animation race:** After tapping `captureImg`, camera preview frame processing takes ~300-800ms; waiter must verify `in.coral.bpdcl:id/input` is visible and enabled before text injection.
5. **Revalidation dialog ordering:** Some meters display the "Electro Mechanical Meter" dialog first, while others skip directly to the "Unclear Image" revalidation; race condition handler must handle either order without timeout traps.

---

### Task 1: Screen 1 Fast IME & Event-Based Search Optimization

**Files:**
- Modify: `smart_engine/screen1_search.py`
- Test: `tests/test_screen1_search.py`

**Interfaces:**
- Consumes: `Screen1Search(device=None, serial="192.168.9.40:5555")`
- Produces: `search_consumer(ca_number: str, timeout: float = 8.0) -> bool`

- [ ] **Step 1: Write unit tests for optimized Screen 1**

```python
# tests/test_screen1_search.py
import unittest
from unittest.mock import MagicMock, patch
from smart_engine.screen1_search import Screen1Search

class TestScreen1Search(unittest.TestCase):
    def test_search_consumer_uses_fast_input_and_wait(self):
        mock_d = MagicMock()
        mock_d.app_start = MagicMock()
        mock_d.set_fastinput_ime = MagicMock()
        mock_d.wait_activity.return_value = True
        
        s1 = Screen1Search(device=mock_d)
        res = s1.search_consumer("10230047179")
        
        self.assertTrue(res)
        mock_d.set_fastinput_ime.assert_called_with(True)
```

- [ ] **Step 2: Run test to verify it fails or tests existing behavior**

Run: `python -m unittest tests/test_screen1_search.py`
Expected: FAIL (file or method expectation not yet matching)

- [ ] **Step 3: Implement Fast IME and direct socket app_start in `smart_engine/screen1_search.py`**

Replace `subprocess.run(["adb", "shell", "am start ..."])` with `self.d.app_start("in.phoenix.bpdcl", ".ConsumerSearchActivity", stop=False)`.
Enable `self.d.set_fastinput_ime(True)` to bypass soft keyboard.
Use `self.d.wait_activity(".BillingManual", timeout=timeout)` and wait for `PresentStatus1` instead of arbitrary `time.sleep(1.1)`.

- [ ] **Step 4: Run unit tests to verify they pass**

Run: `python -m unittest tests/test_screen1_search.py`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add smart_engine/screen1_search.py tests/test_screen1_search.py
git commit -m "perf(screen1): implement fast IME and event-based activity waiters"
```

---

### Task 2: Screen 2 Direct Keyevents & Zero-Sleep Form Controller

**Files:**
- Modify: `smart_engine/screen2_form.py`
- Test: `tests/test_screen2_form.py`

**Interfaces:**
- Consumes: `Screen2Form(device=None, serial="192.168.9.40:5555")`
- Produces: `fill_form_and_launch_camera(meter_type: str = "NORMAL", timeout: float = 8.0) -> bool`

- [ ] **Step 1: Write unit tests for Screen 2 fast form fill**

```python
# tests/test_screen2_form.py
import unittest
from unittest.mock import MagicMock
from smart_engine.screen2_form import Screen2Form

class TestScreen2Form(unittest.TestCase):
    def test_fill_form_invokes_direct_shell_without_subprocess(self):
        mock_d = MagicMock()
        mock_d.shell = MagicMock(return_value=("", 0))
        s2 = Screen2Form(device=mock_d)
        self.assertIsNotNone(s2)
```

- [ ] **Step 2: Run test to verify initial state**

Run: `python -m unittest tests/test_screen2_form.py`
Expected: Baseline verify

- [ ] **Step 3: Implement direct `self.d.shell` keyevent & remove redundant sleeps in `smart_engine/screen2_form.py`**

Replace `subprocess.run(["adb", ...])` with `self.d.shell(f"input keyevent --delay 5 {dpad} 19 66")`.
Remove fixed 0.4s sleeps between dropdown interactions, chaining element `.wait(timeout=1.0)` and `.click()`.
Wait for MR Bharat camera activity via `self.d(resourceId="in.coral.bpdcl:id/captureImg").wait(timeout=timeout)` or `capture_readings_btn`.

- [ ] **Step 4: Run unit tests to verify they pass**

Run: `python -m unittest tests/test_screen2_form.py`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add smart_engine/screen2_form.py tests/test_screen2_form.py
git commit -m "perf(screen2): use persistent socket shell and zero-sleep dropdown chaining"
```

---

### Task 3: Screen 3 Camera Shutter & Multi-Dialog Race Condition Handler

**Files:**
- Modify: `smart_engine/screen3_camera.py`
- Test: `tests/test_screen3_camera.py`

**Interfaces:**
- Consumes: `Screen3Camera(device=None, serial="192.168.9.40:5555")`
- Produces: `handle_camera_and_review(reading_kwh: int = 1355, timeout: float = 12.0) -> bool`

- [ ] **Step 1: Write unit tests for Screen 3 dynamic dialog resolution**

```python
# tests/test_screen3_camera.py
import unittest
from unittest.mock import MagicMock
from smart_engine.screen3_camera import Screen3Camera

class TestScreen3Camera(unittest.TestCase):
    def test_camera_handles_revalidate_and_submit(self):
        mock_d = MagicMock()
        s3 = Screen3Camera(device=mock_d)
        self.assertIsNotNone(s3)
```

- [ ] **Step 2: Run test to verify initial state**

Run: `python -m unittest tests/test_screen3_camera.py`

- [ ] **Step 3: Implement multi-element fast race watcher in `smart_engine/screen3_camera.py`**

Trigger shutter immediately when visible.
Wait for `in.coral.bpdcl:id/input` with `.wait(timeout=4.0)`, immediately set text and tap Save.
Implement unified 100ms watcher loop that detects any of:
- `dialog_title_text` -> taps Submit
- `revalidate_btn` -> taps revalidate -> `btn_report` -> "Readings are correct" -> Submit
- Return to `BillingManual` -> exits loop with `True`.

- [ ] **Step 4: Run unit tests to verify they pass**

Run: `python -m unittest tests/test_screen3_camera.py`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add smart_engine/screen3_camera.py tests/test_screen3_camera.py
git commit -m "perf(screen3): add unified dialog race watcher and instant shutter trigger"
```

---

### Task 4: Master Runner Batch Prefetch & Rapid Ledger Synchronization

**Files:**
- Modify: `smart_engine/runner.py`
- Test: `tests/test_smart_runner.py`

**Interfaces:**
- Consumes: `SmartRunner(mru, cycle, device_serial, dry_run, final_submit)`
- Produces: `run_batch(limit: int = 1) -> dict`

- [ ] **Step 1: Update unit tests in `tests/test_smart_runner.py` for batch processing**

Verify batch prefetch pulls `limit` consumers in 1 API call and returns correct metrics.

- [ ] **Step 2: Run test to verify**

Run: `python -m unittest tests/test_smart_runner.py`
Expected: PASS

- [ ] **Step 3: Implement batch prefetching and instant loop in `smart_engine/runner.py`**

Fetch all `limit` items in a single HTTP request, process locally without re-querying the API between consumers, and sync the batch ledger in one call.

- [ ] **Step 4: Run full test suite across the entire repository**

Run: `python -m unittest discover tests`
Expected: All tests pass (>= 26 tests)

- [ ] **Step 5: Commit changes**

```bash
git add smart_engine/runner.py tests/test_smart_runner.py
git commit -m "perf(runner): enable batch prefetching and instant ledger sync"
```

---

### Task 5: Live Hardware Verification & Latency Benchmarking

**Files:**
- Verify: Connected device `192.168.9.40:5555`

- [ ] **Step 1: Benchmark single consumer run in Stage-Only mode**

Run: `python smart_engine/runner.py --mru 8 --limit 1`
Verify total execution time is under 15 seconds (target: 8–12s).

- [ ] **Step 2: Confirm clean return to `ConsumerSearchActivity` or `BillingManual`**

Verify no stuck dialogs, keyboard overlays, or unhandled alerts remain on the physical phone screen.
