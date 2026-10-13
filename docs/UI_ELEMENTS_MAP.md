# UI Elements Map & Screen Geometry Guide

This document catalogues every critical UI element, resource ID, bounds, center coordinates, and interaction rule across all screens.

Target Display Profile: **$1080 \times 2400$ px (OPPO CPH2637, 408 DPI)**

---

## Screen 1: CONSUMER SEARCH (`in.phoenix.bpdcl.ConsumerSearchActivity`)

| Element | Resource ID | Class | Bounds | Center $(X, Y)$ | Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Search Input Box** | `in.phoenix.bpdcl:id/bh_AccNo1search` | `AutoCompleteTextView` | `[454, 493][1000, 593]` | `(727, 543)` | Tap, clear text (DEL x 25), type consumer number |
| **Search Button** | `in.phoenix.bpdcl:id/cons_search` | `Button` (text="Search") | `[369, 665][532, 787]` | `(450, 726)` | Tap to initiate search query |
| **Back Button** | `in.phoenix.bpdcl:id/bill_backsearch` | `Button` (text="Back") | `[548, 665][711, 787]` | `(629, 726)` | Returns to Homepage |
| **Screen Title** | `in.phoenix.bpdcl:id/textView1` | `TextView` | `[41, 270][1039, 390]` | `(540, 330)` | Header check |

---

## Screen 2: BILLING MANUAL (`in.phoenix.billing.BillingManual`)

### 1. Dropdown Form Controls

| Element | Resource ID | Bounds (Unscrolled) | Center $(X, Y)$ | Target Selection | Selection Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Meter Reading Status** | `in.phoenix.bpdcl:id/PresentStatus1` | `[357, 1148][1026, 1248]` | `(691, 1198)` | `NORMAL` | Tap right arrow $\to$ Tap first option at $Y + 50$ px |
| **Site Observation** | `in.phoenix.bpdcl:id/atMOBS1` | `[357, 1274][1026, 1374]` | `(691, 1324)` | `OK` (2nd from bottom) | Tap center $\to$ DPAD atomic sequence: `30 DOWN + 1 UP + 1 ENTER` |
| **Meter Location Type** | `in.phoenix.bpdcl:id/meterloctypeiv` | `[357, 2045][1026, 2145]` (Unscrolled) <br> `[357, 1400][1026, 1500]` (Scrolled) | `(691, 1450)` | `Inside` | **Must auto-scroll if $Y > 1550$** $\to$ Tap arrow $\to$ Tap first option at $Y + 45$ px |

### 2. Capture & Action Buttons

| Element | Resource ID | Class | Bounds | Center $(X, Y)$ | Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Present Reading Circle Icon** | `in.phoenix.bpdcl:id/KwhCaptureButton` | `ImageView` | `[357, 1578][524, 1700]` | `(440, 1639)` | Tap to launch Coral app |
| **KVAH Capture Icon** | `in.phoenix.bpdcl:id/KvahCaptureButton` | `ImageView` | Variable | Variable | Used for commercial meters |
| **Submit Bill Button** | `in.phoenix.bpdcl:id/Submit` | `Button` | Bottom of scroll | Variable | Final bill calculation & commit |
| **Alert Dialog OK** | `android:id/button1` | `Button` | Variable modal | Center | Dismiss alerts (e.g. record not found) |

---

## Screen 3: CORAL INTERMEDIARY (`in.coral.bpdcl.MeterReadingActivity`)

| Element | Resource ID | Class | Bounds | Center $(X, Y)$ | Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CAPTURE Button** | `in.coral.bpdcl:id/capture_readings_btn` | `Button` (text="CAPTURE") | `[51, 2155][1014, 2308]` | `(532, 2231)` | Tap to open live camera viewfinder |
| **Abnormalities Spinner** | `in.coral.bpdcl:id/select_abnormalities` | `Spinner` | `[51, 344][1029, 456]` | `(540, 400)` | Default: "Everything is Ok" |
| **Reading Status OK** | `in.coral.bpdcl:id/rdbtn_ok` | `RadioButton` | `[51, 550][281, 632]` | `(166, 591)` | Default: Checked |

---

## Screen 4: LIVE CAMERA VIEWFINDER (`in.coral.bpdcl.ScanMeterActivity`)
Header Title: **"Bharat MR BPDCL"**

| Element | Resource ID | Class | Bounds | Center $(X, Y)$ | Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Preview View** | `in.coral.bpdcl:id/previewView` | `PreviewView` / `TextureView` | `[0, 250][1080, 2184]` | `(540, 1217)` | CameraX hardware stream |
| **CutOut Guide** | `in.coral.bpdcl:id/cutout_view` | `CutOutView` | `[0, 250][1080, 2400]` | `(540, 1325)` | Framing boundary for meter LCD |
| **CAPTURE Button (Orange)** | `in.coral.bpdcl:id/captureImg` | `Button` (text="CAPTURE") | `[560, 2184][1029, 2329]` | `(794, 2256)` | Snaps frame & runs OCR |
| **SUBMIT Button (Green)** | `in.coral.bpdcl:id/btn_submit_reading` | `Button` (text="SUBMIT") | `[51, 2184][520, 2329]` | `(285, 2256)` | Accepts OCR & returns to App 1 |
| **Flash Switch** | `in.coral.bpdcl:id/flash_switch` | `Switch` | `[960, 301][1080, 370]` | `(1020, 335)` | Toggles flashlight LED |
| **Zoom Slider** | `in.coral.bpdcl:id/zoom_seekbar` | `SeekBar` | `[221, 1535][986, 1581]` | `(603, 1558)` | Optical/digital camera zoom |

---

## Critical Geometry Quirks & Solutions

### 1. The Unscrolled Page Trap (`meterloctypeiv`)
- **Problem:** When `BillingManual` first loads without manual user scrolling, `meterloctypeiv` sits at $Y \approx 2045-2145$. On a $2400$ px screen, the navigation bar starts at $Y = 2150$. Because Android's `ListPopupWindow` requires vertical room below the anchor to display, it fails to open or renders zero items when tapped at the bottom edge.
- **Solution:** `ensure_in_view("meterloctypeiv", elements, max_y=1550)` inspects the anchor's lower bound. If $Y > 1550$, it dispatches a smooth swipe on `ScrollView01` (`input swipe 500 1800 500 1000 300`), pulling `meterloctypeiv` to the middle third ($Y \approx 1100-1400$) where dropdown popups open reliably downwards.

### 2. Site Observation 23-Item Navigation (`atMOBS1`)
- **Problem:** `atMOBS1` contains 23 items. Pixel coordinates vary across devices and dynamic view heights. The desired option `OK` is always **second from the bottom** (just above `NOT ACCESSIBLE`).
- **Solution:** Native atomic DPAD keyevents:
  ```powershell
  input keyevent --delay 40 20 20 ... (30 DPAD_DOWNs) 19 (1 DPAD_UP) 66 (ENTER)
  ```
  This guarantees hitting the bottom boundary and moving up exactly 1 step to `OK` regardless of screen DPI, font size, or item height.
