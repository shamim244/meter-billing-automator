# Smart Engine V2 (uiautomator2 + TypeSafe Jev) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an autonomous, dynamic decision engine in a new isolated directory (`smart_engine/`) using `uiautomator2` and `typesafe-sdk` (Jev System 1) that eliminates the 50% doubtful failure rate by dynamically selecting dropdowns, resolving secondary popups, and executing doubt overrides without hardcoded coordinates.

**Architecture:** A 4-stage pipeline: (1) `uiautomator2` captures native compressed UI trees in ~40ms; (2) `ContextCompressor` prunes empty nodes to a ~150-token payload; (3) `TypeSafeClient` evaluates `Choice`/`Noul` primitives in ~70ms; (4) Dynamic dispatcher clicks/types directly by semantic element identity.

**Tech Stack:** Python 3.10+, `uiautomator2`, `typesafe-sdk`, `requests` (for SaaS API).

**Spec:** Zero modification of existing root files (`automate_selections.py`, `chat/run_queue.py`). All new logic resides in `smart_engine/`.

## Global Constraints

- **Isolation Constraint:** Never touch or modify `automate_selections.py`, `chat/run_queue.py`, or root configs.
- **Directory Scope:** All new code and modules must be placed under `v:\reading-meter-app\smart_engine/`.
- **Reusable Assets:** Read/reuse existing configurations from `.env` and `chat/nbpdcl_client.py` for API sync.
- **Latency Budget:** UI extraction + compression + Jev decision must execute in under 250ms total per gate.
- **Token Efficiency:** Compressed UI context sent to Jev must remain between 100 and 250 tokens per call.

## Review Focus

1. **Device Reconnect Stability:** If Wi-Fi ADB drops momentarily, `uiautomator2` must reconnect gracefully without crashing the runner.
2. **Hidden Viewfinder Overlays:** In `ScanMeterActivity`, if camera popups appear as standard Android dialogs, match them by `AlertDialog` attributes; fallback to geometric center if text is missing.
3. **Dropdown Focus Settlement:** Spinners must settle for 200ms before taking hierarchy snapshots to avoid capturing intermediate animations.
4. **Offline / Fallback Resilience:** If Jev API fails or times out, fallback to local deterministic rules (e.g. matching button with text "Submit" or "OK").
5. **Dry-Run Safety:** Ensure a `--dry-run` flag is supported so the queue can be verified end-to-end without mutating production bills.

---

### Task 1: Environment & Dependencies Scaffolding

**Files:**
- Create: `smart_engine/__init__.py`
- Create: `smart_engine/requirements.txt`
- Test: Verify package installation in shell

- [ ] Write `smart_engine/requirements.txt` listing `uiautomator2>=3.0.0` and `typesafe-sdk>=0.1.0`.
- [ ] Install dependencies via `pip install -r smart_engine/requirements.txt`.
- [ ] Test `uiautomator2` connection to `192.168.9.40:5555` via a quick one-line script (`u2.connect('192.168.9.40:5555').info`).
- [ ] Commit initial scaffolding (`git commit -m "feat(smart_engine): initial dependencies and package scaffold"`).

---

### Task 2: High-Speed Device Wrapper (`smart_engine/device.py`)

**Files:**
- Create: `smart_engine/device.py`
- Test: `tests/test_device_wrapper.py`

- [ ] Write failing test in `tests/test_device_wrapper.py` for connection initialization, activity detection, and compressed hierarchy dump.
- [ ] Implement `SmartDevice` class in `smart_engine/device.py`:
  - `connect(device_ip="192.168.9.40:5555")`: Initializes `uiautomator2` instance.
  - `get_compressed_hierarchy()`: Calls `d.dump_hierarchy(compressed=True)`.
  - `click_element(selector)`: Semantic click by text or resource ID.
  - `type_text(selector, text)`: Direct text entry.
- [ ] Run tests and verify device connection and hierarchy extraction speed (<60ms).
- [ ] Commit `smart_engine/device.py`.

---

### Task 3: The Context Compressor (`smart_engine/compressor.py`)

**Files:**
- Create: `smart_engine/compressor.py`
- Test: `tests/test_compressor.py`

- [ ] Write unit test in `tests/test_compressor.py` testing that raw XML dump with 50+ nodes prunes to <10 actionable items.
- [ ] Implement `ContextCompressor` in `smart_engine/compressor.py`:
  - `extract_actionable_nodes(xml_or_tree)`: Extracts only clickable, focusable, or text-bearing nodes.
  - `detect_modal_dialog(tree)`: Finds active `AlertDialog` title, message, and positive/negative buttons.
  - `to_jev_state(screen_name, goal)`: Returns a compact JSON object (100–200 tokens) ready for Jev.
- [ ] Verify test passes with 100% token budget compliance.
- [ ] Commit `smart_engine/compressor.py`.

---

### Task 4: TypeSafe Jev Decision Engine (`smart_engine/decision_agent.py`)

**Files:**
- Create: `smart_engine/decision_agent.py`
- Test: `tests/test_decision_agent.py`

- [ ] Write unit test mocking Jev `TypeSafeClient` response for:
  - Form dropdown selection (`NORMAL`, `OK`, `Inside`).
  - Secondary dialog handling ("KW is not available in the Meter" -> `Submit`).
  - Revalidation Doubt Override ("Tolerance exceeded" -> `Readings are correct`).
- [ ] Implement `JevDecisionAgent` in `smart_engine/decision_agent.py`:
  - Uses `typesafe_sdk.Choice` for multi-option selection.
  - Uses `typesafe_sdk.Noul` for boolean alerts (e.g. `is_doubt_screen_present`).
  - Fallback logic if API key is unconfigured or request times out.
- [ ] Verify unit tests pass.
- [ ] Commit `smart_engine/decision_agent.py`.

---

### Task 5: End-to-End Smart Queue Runner (`smart_engine/runner.py`)

**Files:**
- Create: `smart_engine/runner.py`
- Test: `tests/test_smart_runner.py`

- [ ] Write test in `tests/test_smart_runner.py` for queue fetching, consumer parameter parsing, and dry-run execution.
- [ ] Implement `smart_engine/runner.py`:
  - Reuses `chat/nbpdcl_client.py` for SaaS API queue fetching (`/automation/queue`) and batch sync.
  - Orchestrates the 3 gates:
    - **Gate 1 (BillingManual):** Dynamic dropdown selection of Status, Observation, and Location via `SmartDevice` + `JevDecisionAgent`.
    - **Gate 2 (MR Bharat Shutter & Reading):** Takes photo, types `working_reading`, dismisses secondary submit popups.
    - **Gate 3 (Review & Doubt Resolver):** Detects if marked Doubt; dynamically executes "Readings are correct" override.
  - Returns cleanly to `ConsumerSearchActivity` and syncs ledger to SaaS.
  - Supports `--dry-run`, `--limit`, `--mru`, and `--cycle` CLI flags.
- [ ] Run dry-run verification: `python smart_engine/runner.py --dry-run --mru 8 --limit 3`.
- [ ] Commit `smart_engine/runner.py`.

---

### Task 6: Live Single-Consumer Field Verification

**Files:**
- Target: Run on connected physical device (`192.168.9.40:5555`)

- [ ] Run single live consumer: `python smart_engine/runner.py --mru 8 --limit 1`.
- [ ] Observe and verify that:
  - Dropdown options are dynamically clicked without random mis-selections.
  - Photo is captured and `working_reading` is injected into the input box.
  - Secondary confirmation dialog is automatically dismissed.
  - Result flips from `Doubtful` to `Submitted`.
  - SaaS ledger updates successfully on the dashboard.
- [ ] Commit final verified state.
