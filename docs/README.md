# Meter Reading Automation - Agent Knowledge Base & Memory Index

This directory contains the complete technical architecture, reverse-engineering findings, UI element mappings, and automation blueprints for the **NBPDCL Meter Reading Automation Project**.

---

## Documentation Index

1. [**SYSTEM_ARCHITECTURE.md**](file:///V:/reading-meter-app/.agents/SYSTEM_ARCHITECTURE.md)
   - Dual-app ecosystem (`in.phoenix.bpdcl` and `in.coral.bpdcl`).
   - Complete end-to-end lifecycle and activity transition graph.
   - Inter-Process Communication (IPC) Intent specifications and payload structure.

2. [**UI_ELEMENTS_MAP.md**](file:///V:/reading-meter-app/.agents/UI_ELEMENTS_MAP.md)
   - Exhaustive dictionary of all UI Resource IDs, bounds, center coordinates, and classes.
   - Screen geometry rules ($1080 \times 2400$).
   - Solved layout quirks (unscrolled geometry issue, atomic DPAD dropdown navigation).

3. [**AUTOMATION_GUIDE.md**](file:///V:/reading-meter-app/.agents/AUTOMATION_GUIDE.md)
   - Operational guide for [`automate_selections.py`](file:///V:/reading-meter-app/automate_selections.py).
   - Single-run, Clipboard Watcher loop (`--watch`), Batch queue (`--file`), and Screen Reset (`--reset`).
   - Windows clipboard detection pipeline.

4. [**REVERSE_ENGINEERING_NOTES.md**](file:///V:/reading-meter-app/.agents/REVERSE_ENGINEERING_NOTES.md)
   - Deep-dive source analysis from decompiled `BillingManual.java` and `ScanMeterActivity.java`.
   - CameraX / ML Kit implementation in `in.coral.bpdcl`.
   - Architectural assessment of static image camera injection.

---

## Quick Reference Summary

- **App 1 (Consumer Search & Billing):** `in.phoenix.bpdcl` (`NBPDCL Ver : 3.5`)
- **App 2 (Camera & OCR Engine):** `in.coral.bpdcl` (`Bharat MR BPDCL` / Coral Innovations)
- **Target Resolution:** $1080 \times 2400$ (OPPO CPH2637, Android 16)
- **Primary Script:** `V:\reading-meter-app\automate_selections.py`
- **Core Pipeline:**
  ```
  PC Clipboard (Ctrl+C)
         │
         ▼
  ConsumerSearchActivity (Type & Search)
         │
         ▼
  BillingManual (NORMAL -> OK [2nd from bottom] -> Inside [auto-scrolled])
         │
         ▼
  Tap KwhCaptureButton
         │
         ▼
  in.coral.bpdcl.MeterReadingActivity (Tap CAPTURE button)
         │
         ▼
  in.coral.bpdcl.ScanMeterActivity (Bharat MR BPDCL Live Camera Viewfinder)
  ```
