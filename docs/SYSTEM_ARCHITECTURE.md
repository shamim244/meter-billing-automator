# System Architecture & Application Ecosystem

This document describes the multi-application architecture, activity lifecycles, and Inter-Process Communication (IPC) that power the meter reading workflow.

---

## 1. Multi-Application Ecosystem

The automation workflow spans two distinct Android packages communicating via explicit and implicit Android Intents:

```
┌─────────────────────────────────────────────────────────────┐
│                      APP 1: in.phoenix.bpdcl                │
│                 (NBPDCL Ver: 3.5 / North Bihar)             │
│                                                             │
│  1. ConsumerSearchActivity                                  │
│     - Entry point for operator.                             │
│     - Input: Consumer Number / Account Number / CA Number.  │
│                                                             │
│  2. in.phoenix.billing.BillingManual                        │
│     - Consumer profile, previous meter readings.            │
│     - Mandatory selections:                                 │
│       * Meter Reading Status -> NORMAL                      │
│       * Site Observation -> OK (2nd from bottom)            │
│       * Meter Location Type -> Inside                       │
│     - Launches App 2 via Intent.                            │
│     - Receives reading via onActivityResult and generates   │
│       final bill (Submit button).                           │
└──────────────────────────────┬──────────────────────────────┘
                               │
            Intent: action="android.intent.action.SEND"
                    type="bsmr/meter"
                    package="in.coral.bpdcl"
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      APP 2: in.coral.bpdcl                  │
│                (Coral Innovations / Bharat MR BPDCL)        │
│                                                             │
│  1. in.coral.bpdcl.MeterReadingActivity                     │
│     - Intermediary validation screen.                       │
│     - Displays: Abnormalities (Default: Everything is Ok),  │
│       Reading Status (Default: OK).                         │
│     - Button: CAPTURE (capture_readings_btn).               │
│                                                             │
│  2. in.coral.bpdcl.ScanMeterActivity                        │
│     - Display Title: "Bharat MR BPDCL".                     │
│     - Live CameraX Viewfinder (PreviewView / TextureView).  │
│     - Cutout bounding box overlay (CutOutView).             │
│     - Consumer info header (Serial No, Name, Consumer Id).  │
│     - Buttons: SUBMIT (btn_submit_reading),                 │
│                CAPTURE (captureImg).                        │
│     - Integrated ML Kit Text Recognition / OCR Engine.      │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Activity Transition Lifecycle

```
[Start State: CONSUMER SEARCH]
   │
   ├─► 1. adb types consumer number into `bh_AccNo1search`
   ├─► 2. adb clicks `cons_search` (Search button)
   │
[State: BillingManual Loading]
   │
   ├─► 3. App queries SQLite database for consumer record
   ├─► 4. Form renders consumer details & expands dynamic inputs
   │
[State: BillingManual Selections]
   │
   ├─► 5. Select Meter Reading Status: `NORMAL` (drops down below `PresentStatus1`)
   ├─► 6. Select Site Observation: `OK` (drops down from `atMOBS1`, scrolled to 2nd from bottom)
   ├─► 7. Auto-scroll: checks `meterloctypeiv` Y position; swipes up if Y > 1550
   ├─► 8. Select Meter Location Type: `Inside`
   ├─► 9. Verification: validates all 3 fields match expected strings
   │
[State: Transition to Coral]
   │
   ├─► 10. adb clicks circular camera icon `KwhCaptureButton`
   ├─► 11. in.phoenix.bpdcl constructs Intent payload and calls startActivityForResult()
   │
[State: MeterReadingActivity (Coral Intermediary)]
   │
   ├─► 12. adb waits for `capture_readings_btn`
   ├─► 13. adb clicks `capture_readings_btn`
   │
[State: ScanMeterActivity (Bharat MR BPDCL Live Camera)]
   │
   ├─► 14. CameraX initialises camera hardware with PreviewView
   ├─► 15. CutOutView renders meter frame guide
   │
[Target State Reached: Live Camera Viewfinder Ready for Capture]
```

---

## 3. IPC Intent Specification

Extracted directly from decompiled source (`BillingManual.java` lines 14684–14740):

### Intent Configuration:
- **Action:** `android.intent.action.SEND`
- **MIME Type:** `bsmr/meter`
- **Target Package:** `in.coral.bpdcl`
- **Target Activity:** `in.coral.bpdcl.MeterReadingActivity`

### Intent Extras Passed from App 1 to App 2:
| Extra Key | Data Type | Description / Sample Value |
| :--- | :--- | :--- |
| `BOARD_CODE` | String | `"NBPDCL"` or `"SBPDCL"` |
| `ACCESS_KEY` | String | `"5iVFQs34Qm_nbpdcl"` |
| `CONSUMER_NO` | String | `"10230047633"` |
| `ACCOUNT_NO` | String | `"NSC/NISARBHATI/BPL/27"` |
| `CONSUMER_NAME`| String | Consumer full name |
| `METER_NO` | String | `"3805347"` |
| `PHASE` | String | Meter phase (`1` or `3`) |
| `CATEGORY` | String | Tariff category (e.g. `KJ_R`) |
| `BILLING_TYPE` | String | Area / billing route code |
| `MULTIPLICATION_FACTOR` | String | Meter multiplication factor (MF) |
| `CONTRACTED_LOAD` | String | Sanctioned load |
| `PREV_READING_DATE` | String | Date string (`dd-MM-yyyy`) |
| `PREV_READING_VALUES` | String (JSON) | `{"KWH": 123.0}` |
| `REQ_READING_VALUES` | String[] | `["KWH"]` (or `["KWH", "KVAH", "KW", "KVA", "PF"]`) |

### Result Contract (`onActivityResult`):
- **Result Code:** `Activity.RESULT_OK`
- **Returned Extras:** Captured image paths (`meter_uf`, `meter_dept`) and extracted numerical reading string (`KWH_READING`).
- **Signature Verification:** **None**. App 1 does not verify the cryptographic signature of App 2.
