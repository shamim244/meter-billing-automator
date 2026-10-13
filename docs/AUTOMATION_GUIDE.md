# Automation Guide & Script Reference

This document covers execution, configuration, and maintenance of [`automate_selections.py`](file:///V:/reading-meter-app/automate_selections.py).

---

## 1. Script Capabilities & Modes

The script [`automate_selections.py`](file:///V:/reading-meter-app/automate_selections.py) is modular and supports four execution modes:

### Mode 1: Interactive Auto-Loop (Clipboard Watcher)
```powershell
python .\automate_selections.py --watch
# or:
python .\automate_selections.py -w
```
- **Behavior:** Runs continuously in the background on your PC.
- **Workflow:**
  1. Open your consumer table / slider tool on PC.
  2. Press `Ctrl+C` on any consumer number.
  3. The script detects the change, awakens the device screen, inputs the number, clicks Search, executes all dropdown selections, clicks the circular icon, clicks the Coral Capture button, and stops on the live camera viewfinder.
  4. When you finish with that consumer, simply press `Ctrl+C` on the next number!

---

### Mode 2: Batch Queue Processing (Unattended)
```powershell
python .\automate_selections.py --file consumers.txt
# or:
python .\automate_selections.py -f consumers.txt
```
- **File Format:** A standard text file with one consumer number per line:
  ```text
  10230047633
  10230047634
  10230047635
  ```
- **Behavior:** Sequentially executes each consumer. Before starting each record, it calls `ensure_search_screen()` to reset state back to the search box.

---

### Mode 3: Single Explicit Run
```powershell
# Run with explicit number:
python .\automate_selections.py 10230047633

# Run using whatever is currently in PC clipboard:
python .\automate_selections.py
```
- Runs one cycle and terminates immediately upon reaching the live camera viewfinder.

---

### Mode 4: Screen State Reset
```powershell
python .\automate_selections.py --reset
```
- Resets the device screen from any state (Camera Viewfinder, Coral Intermediary, Billing Form, or Alert Dialog) back to the clean **CONSUMER SEARCH** screen (`ConsumerSearchActivity`).

---

## 2. PC Clipboard Detection Engine

Clipboard reading is implemented with a two-tier zero-dependency architecture:
1. **Tier 1 (Instant / In-Memory):** Python standard library `tkinter` (`tk.Tk().clipboard_get()`). Takes $\approx 2$ ms.
2. **Tier 2 (Fallback):** PowerShell `Get-Clipboard` via subprocess.
3. **Regex Sanitization:**
   - Extracts matches matching `\b\d{9,12}\b`.
   - Strips non-digits; accepts cleaned numbers $\ge 6$ digits.
   - Ignores irrelevant clipboard content (e.g. general text, URLs, file paths).

---

## 3. Power Management & Screen Wakefulness

Before executing any UI dump or touch event, the script checks:
```python
power_state = adb_command(["shell", "dumpsys", "power"])
if "mWakefulness=Asleep" in power_state or "mWakefulness=Dozing" in power_state:
    adb_command(["shell", "input", "keyevent", "224"]) # WAKEUP
```
This ensures the device screen does not timeout or drop ADB input during prolonged sessions.

---

## 4. Troubleshooting & Connection Notes

- **Wi-Fi Port Changes:**
  Android Wi-Fi Debugging assigns a new random port upon reconnecting to Wi-Fi. If connection drops:
  1. Check Settings $\to$ Developer Options $\to$ Wireless Debugging on the phone.
  2. Run: `adb connect <PHONE_IP>:<PORT>`.
  3. Verify with: `adb devices`.
- **Battery Optimization:**
  Keep the phone plugged into power during high-volume automation runs to prevent Android Doze mode from shutting down the ADB Wi-Fi daemon.
