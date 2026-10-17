# Zero-Sleep Speed Optimizations and SaaS API Tuning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate post-typing search delays in Screen 1, eliminate dropdown waiting delays in Screen 2, align `chat/nbpdcl_client.py` and `smart_engine/runner.py` with the updated SaaS REST API (dual-layer smart averages, `apply_tuning`, and `average-tuning` endpoints), and maintain safe git rollback checkpoints.

**Architecture:** 
1. `chat/nbpdcl_client.py`: Upgrade `get_automation_queue` to pass `apply_tuning` flag, add `update_consumer_average_tuning`, fix `batch_sync` signature handling in `runner.py`.
2. `smart_engine/screen1_search.py`: Eliminate XML hierarchy dump latency between CA input and search tap by using non-blocking `click_exists(0.1)` with immediate keyevent 4 + coordinate fallback tap `input tap 450 726`.
3. `smart_engine/screen2_form.py`: Add smart pre-fill bypass (if `atMOBS1` == "OK" and `meterloctypeiv` == "Inside") and replace chained `.wait(1.5)` calls with micro-timeout `click_exists` taps directly into MR Bharat camera.
4. `smart_engine/runner.py`: Add `--apply-tuning` CLI argument and fix batch sync payload formatting.

**Tech Stack:** Python 3.10+, `uiautomator2`, Android ADB over TCP/IP (`192.168.9.40:5555`), REST API (`requests`), `unittest`, Git.

**Spec:** Direct operator feedback on Screen 1 search pause, Screen 2 dropdown wait, and updated SaaS API documentation at `http://localhost:8000/docs/api`.

## Global Constraints

- Never modify legacy root files `automate_selections.py`, `chat/run_queue.py`, or `.env`.
- Keep all optimizations strictly isolated inside `smart_engine/`, `chat/nbpdcl_client.py`, and `tests/`.
- Default execution mode in `smart_engine/runner.py` must remain Stage-Only (`--stage-only` safe mode) unless `--final-submit` is passed.
- Maintain full compatibility with connected device `192.168.9.40:5555` running NBPDCL (`in.phoenix.bpdcl`) and MR Bharat (`in.coral.bpdcl`).
- All unit tests in `tests/` must remain passing.

## Review Focus

1. **IME soft keyboard race:** Typing CA number might trigger soft keyboard; tapping search must dismiss keyboard immediately without freezing UI.
2. **Pre-filled state detection failure:** If UI text reading fails or element is not immediately accessible, fallback must execute full standard dropdown selection rather than hanging.
3. **API response compatibility:** Both baseline `smart_average_kwh` and dual-layer companion fields (`base_avg_units`, `tuned_avg_units`) must parse correctly without key errors.
4. **Batch sync signature parity:** Calling `submit_batch_sync` or `batch_sync` in `runner.py` must reliably pass `billing_month`, `billing_year`, and `reviews` array.
5. **Git rollback cleanliness:** Every functional increment must be committed with clean status so `git reset --hard` or `git checkout` can revert cleanly.

---

### Task 1: SaaS API Client & Runner Tuning Alignment

**Files:**
- Modify: `chat/nbpdcl_client.py`
- Modify: `smart_engine/runner.py`
- Create: `tests/test_nbpdcl_client_api.py`

**Interfaces:**
- Consumes: OpenAPI `/automation/queue`, `/consumers/{ca}/average-tuning`, `/bills/batch-sync`
- Produces: `client.get_automation_queue(mru_id, cycle, limit, apply_tuning)`, `client.update_consumer_average_tuning(...)`, `client.batch_sync(...)` / `client.submit_batch_sync(...)`

- [ ] **Step 1: Write unit tests for updated API client methods**
- [ ] **Step 2: Run test to verify it fails before implementation**
- [ ] **Step 3: Implement `apply_tuning` and `update_consumer_average_tuning` in `chat/nbpdcl_client.py` and update `runner.py`**
- [ ] **Step 4: Run unit tests to verify they pass**
- [ ] **Step 5: Commit changes**

---

### Task 2: Screen 1 Zero-Sleep Consumer Search Optimization

**Files:**
- Modify: `smart_engine/screen1_search.py`
- Modify: `tests/test_screen1_search.py`

**Interfaces:**
- Consumes: `Screen1Search(device=d, serial=serial)`
- Produces: `search_consumer(ca_number: str, timeout: float = 8.0) -> bool`

- [ ] **Step 1: Write/update unit test for non-blocking search button tap and rapid BillingManual entry**
- [ ] **Step 2: Run test to verify behavior**
- [ ] **Step 3: Implement zero-sleep search tap in `smart_engine/screen1_search.py`**
- [ ] **Step 4: Run unit tests to verify they pass**
- [ ] **Step 5: Commit changes**

---

### Task 3: Screen 2 Zero-Sleep BillingManual Form Controller

**Files:**
- Modify: `smart_engine/screen2_form.py`
- Modify: `tests/test_screen2_form.py`

**Interfaces:**
- Consumes: `Screen2Form(device=d, serial=serial)`
- Produces: `fill_form_and_launch_camera(meter_type: str = "NORMAL", timeout: float = 8.0) -> bool`

- [ ] **Step 1: Write/update unit tests for smart pre-fill bypass and rapid dropdown chaining**
- [ ] **Step 2: Run test to verify behavior**
- [ ] **Step 3: Implement smart pre-fill check and micro-timeout chaining in `smart_engine/screen2_form.py`**
- [ ] **Step 4: Run unit tests to verify they pass**
- [ ] **Step 5: Commit changes**

---

### Task 4: Complete Test Suite Verification & Live Benchmark

**Files:**
- Test: `tests/`
- Run: `smart_engine/runner.py`

- [ ] **Step 1: Run complete test suite (`python -m unittest discover tests`)**
- [ ] **Step 2: Run live benchmark consumer test on device (`python -u smart_engine/runner.py --mru 8 --limit 1`)**
- [ ] **Step 3: Verify cycle speed and output logs**
- [ ] **Step 4: Commit changes and verify git status is 100% clean**
