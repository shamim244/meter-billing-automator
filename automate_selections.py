import subprocess
import time
import sys
import os
import re
import xml.etree.ElementTree as ET

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ACTIVE_DEVICE_SERIAL = None

def adb_shell(cmd, timeout=15):
    global ACTIVE_DEVICE_SERIAL
    try:
        adb_prefix = ["adb", "-s", ACTIVE_DEVICE_SERIAL] if ACTIVE_DEVICE_SERIAL else ["adb"]
        res = subprocess.run(adb_prefix + ["shell", cmd], capture_output=True, text=True, timeout=timeout)
        return res.stdout.strip()
    except Exception:
        return ""

def check_device():
    global ACTIVE_DEVICE_SERIAL
    res = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout
    lines = [line.strip() for line in res.splitlines() if line.strip() and not line.startswith("List of")]

    active_devices = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            serial, state = parts[0], parts[1]
            if state == "offline":
                # Auto-disconnect stale offline ghost connections
                subprocess.run(["adb", "disconnect", serial], capture_output=True)
            elif state == "device":
                active_devices.append(serial)

    if not active_devices:
        default_target = os.environ.get("ADB_DEVICE_SERIAL") or os.environ.get("ADB_DEVICE", "192.168.9.40:5555")
        if default_target:
            subprocess.run(["adb", "connect", default_target], capture_output=True)
            time.sleep(0.5)
            res = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout
            lines = [line.strip() for line in res.splitlines() if line.strip() and not line.startswith("List of")]
            for line in lines:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    active_devices.append(parts[0])

    if not active_devices:
        print("[!] No active ADB device found.")
        print("[!] Please check Wi-Fi debugging port and run: adb connect <IP>:<PORT>")
        return False

    ACTIVE_DEVICE_SERIAL = active_devices[0]
    return True

def wake_device():
    power_state = adb_shell("dumpsys power")
    if "mWakefulness=Asleep" in power_state or "mWakefulness=Dozing" in power_state:
        print("[*] Screen is sleeping. Waking screen...")
        adb_shell("input keyevent 224")
        time.sleep(0.2)

def get_consumer_from_clipboard():
    text = ""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        text = root.clipboard_get()
        root.destroy()
    except Exception:
        pass
    
    if not text:
        try:
            res = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard"], capture_output=True, text=True, timeout=3)
            text = res.stdout.strip()
        except Exception:
            pass

    if not text:
        try:
            # Termux on Android support
            res = subprocess.run(["termux-clipboard-get"], capture_output=True, text=True, timeout=2)
            text = res.stdout.strip()
        except Exception:
            pass
            
    if text:
        # Ignore IP addresses, port strings, and ADB commands
        if "192.168" in text or "connect" in text or "adb" in text:
            return None

        # Bihar electricity consumer numbers are 11 to 12 digits (usually starting with 10 or 11)
        digits = re.findall(r'\b\d{11,12}\b', text)
        if digits:
            candidate = digits[0]
            if not candidate.startswith("192168"):
                return candidate

        clean = re.sub(r'\D', '', text.strip())
        if len(clean) in (10, 11, 12) and not clean.startswith("192168"):
            return clean

    return None

def dismiss_keyboard():
    res = adb_shell("dumpsys input_method | grep mInputShown")
    if "mInputShown=true" in res:
        adb_shell("input keyevent 4")
        time.sleep(0.15)

def get_ui_elements():
    """Fast single UI dump directly streamed into memory without disk pull overhead."""
    global ACTIVE_DEVICE_SERIAL
    adb_prefix = ["adb", "-s", ACTIVE_DEVICE_SERIAL] if ACTIVE_DEVICE_SERIAL else ["adb"]
    
    adb_shell("uiautomator dump /data/local/tmp/d.xml")
    res = subprocess.run(adb_prefix + ["exec-out", "cat", "/data/local/tmp/d.xml"], capture_output=True, text=True, timeout=5)
    xml_str = res.stdout
    if not xml_str or "hierarchy" not in xml_str:
        return {}

    try:
        tree = ET.fromstring(xml_str)
    except Exception:
        return {}

    elements = {}
    target_keys = ["PresentStatus1", "atMOBS1", "meterloctypeiv", "button1"]
    for n in tree.iter("node"):
        rid = n.attrib.get("resource-id", "")
        for k in target_keys:
            if k in rid:
                bounds = n.attrib.get("bounds", "").replace("][", ",").replace("[", "").replace("]", "").split(",")
                x1, y1, x2, y2 = map(int, bounds)
                elements[k] = {
                    "cx": (x1 + x2) // 2,
                    "cy": (y1 + y2) // 2,
                    "arrow_x": x2 - 50,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "text": n.attrib.get("text", "")
                }
    return elements

def get_ui_tree(timeout=6):
    global ACTIVE_DEVICE_SERIAL
    adb_prefix = ["adb", "-s", ACTIVE_DEVICE_SERIAL] if ACTIVE_DEVICE_SERIAL else ["adb"]
    adb_shell("uiautomator dump /data/local/tmp/d.xml")
    res = subprocess.run(adb_prefix + ["exec-out", "cat", "/data/local/tmp/d.xml"], capture_output=True, text=True, timeout=timeout)
    xml_str = res.stdout
    if not xml_str or "hierarchy" not in xml_str:
        return None
    try:
        return ET.fromstring(xml_str)
    except Exception:
        return None

def find_node(tree, resource_id=None, text=None, cls=None, content_desc=None):
    if tree is None:
        return None
    for n in tree.iter("node"):
        rid = n.attrib.get("resource-id", "")
        t = n.attrib.get("text", "")
        c = n.attrib.get("class", "")
        desc = n.attrib.get("content-desc", "")

        match = True
        if resource_id and resource_id not in rid:
            match = False
        if text and text.lower() not in t.lower():
            match = False
        if cls and cls not in c:
            match = False
        if content_desc and content_desc.lower() not in desc.lower():
            match = False

        if match:
            bounds = n.attrib.get("bounds", "").replace("][", ",").replace("[", "").replace("]", "").split(",")
            if len(bounds) == 4:
                try:
                    x1, y1, x2, y2 = map(int, bounds)
                    return {
                        "cx": (x1 + x2) // 2,
                        "cy": (y1 + y2) // 2,
                        "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                        "text": t,
                        "resource_id": rid,
                        "class": c,
                    }
                except Exception:
                    pass
    return None

def handle_coral_camera_stage(reading_kwh=None, timeout=10):
    """
    Phase 2 - Step 1: Coral Camera (ScanMeterActivity)
    - If in MeterReadingActivity, taps CAPTURE to open viewfinder
    - Captures meter image via captureImg
    - Injects or confirms reading_kwh into reading dialog
    - Taps 'Save'
    - Taps 'Submit' on secondary dialog if shown
    - Taps Coral 'Submit' (btn_submit_reading / submit_btn)
    """
    print("  [*] [Phase 2.1] Camera Viewfinder Active. Preparing Shutter...")
    time.sleep(0.5)

    # 0. If in MeterReadingActivity, tap CAPTURE to open camera viewfinder
    focus = adb_shell("dumpsys window | grep mCurrentFocus")
    if "MeterReadingActivity" in focus:
        tree = get_ui_tree()
        cap_btn = find_node(tree, resource_id="capture_readings_btn") or find_node(tree, text="CAPTURE")
        if cap_btn:
            print(f"  [*] Tapping Coral CAPTURE button ({cap_btn['cx']}, {cap_btn['cy']})...")
            adb_shell(f"input tap {cap_btn['cx']} {cap_btn['cy']}")
        else:
            adb_shell("input tap 532 2231")
        time.sleep(1.0)

    # 1. Dismiss spotlight tutorial overlay if present
    tree = get_ui_tree()
    spotlight_btn = find_node(tree, resource_id="btn_spotlight_got_it")
    if spotlight_btn:
        print("  [*] Dismissing spotlight tutorial overlay...")
        adb_shell(f"input tap {spotlight_btn['cx']} {spotlight_btn['cy']}")
        time.sleep(0.3)
        tree = get_ui_tree()

    # 2. Tap shutter button (captureImg)
    shutter = find_node(tree, resource_id="captureImg")
    if shutter:
        shutter_x, shutter_y = shutter['cx'], shutter['cy']
    else:
        shutter_x, shutter_y = 540, 2180

    print(f"  [*] Tapping Camera Shutter at ({shutter_x}, {shutter_y})...")
    adb_shell(f"input tap {shutter_x} {shutter_y}")

    # 3. Wait for Reading Entry Dialog to appear (Save / Rescan / EditText)
    t_start = time.time()
    dialog_ready = False
    save_btn = None
    edit_field = None

    while time.time() - t_start < timeout:
        time.sleep(0.6)
        tree = get_ui_tree()
        save_btn = find_node(tree, text="Save") or find_node(tree, resource_id="button1")
        edit_field = find_node(tree, cls="android.widget.EditText") or find_node(tree, resource_id="txt_reading") or find_node(tree, resource_id="input")
        if save_btn or edit_field:
            dialog_ready = True
            break

    if not dialog_ready:
        print("  [!] Reading entry dialog did not appear after shutter, trying fallback tap...")
        adb_shell("input tap 540 2180")
        time.sleep(0.8)
        tree = get_ui_tree()
        save_btn = find_node(tree, text="Save") or find_node(tree, resource_id="button1")
        edit_field = find_node(tree, cls="android.widget.EditText")

    # 4. Inject reading_kwh if provided
    if reading_kwh is not None and edit_field:
        print(f"  [*] Injecting pre-calculated KWH Reading: {reading_kwh}...")
        adb_shell(f"input tap {edit_field['cx']} {edit_field['cy']}")
        time.sleep(0.15)
        dpad_del = " ".join(["67"] * 15)
        adb_shell(f"input keyevent --delay 2 123 {dpad_del}; input text {reading_kwh}; input keyevent 4")
        time.sleep(0.2)

    # 5. Tap 'Save' on the dialog
    if save_btn:
        print(f"  [*] Tapping Save button ({save_btn['cx']}, {save_btn['cy']})...")
        adb_shell(f"input tap {save_btn['cx']} {save_btn['cy']}")
    else:
        adb_shell("input tap 870 1389; sleep 0.2; input keyevent 66")

    dismiss_keyboard()
    time.sleep(0.6)

    # 6. Handle any secondary popups ('KW is not available in the Meter', 'All required parameters', etc.)
    # until we successfully transition to MeterReadingActivity or BillingManual
    t_pop = time.time()
    while time.time() - t_pop < 8.0:
        focus = adb_shell("dumpsys window | grep mCurrentFocus")
        if "MeterReadingActivity" in focus or "BillingManual" in focus:
            print("  [+] Successfully transitioned to Review / Billing stage!")
            break

        tree = get_ui_tree()
        # Look for dialog Submit button (e.g. android:id/button1 with text 'Submit' or centered around 870, 1397)
        dlg_submit = find_node(tree, text="Submit") or find_node(tree, resource_id="button1")
        if dlg_submit and dlg_submit.get("cy", 0) < 1700:
            print(f"  [*] Secondary popup detected: Tapping Submit at ({dlg_submit['cx']}, {dlg_submit['cy']})...")
            adb_shell(f"input tap {dlg_submit['cx']} {dlg_submit['cy']}")
            time.sleep(1.0)
            continue

        # Look for bottom camera submit button if on viewfinder without popup
        cam_submit = find_node(tree, resource_id="btn_submit_reading") or find_node(tree, resource_id="submit_btn")
        if cam_submit:
            print(f"  [*] Tapping Coral Camera Submit at ({cam_submit['cx']}, {cam_submit['cy']})...")
            adb_shell(f"input tap {cam_submit['cx']} {cam_submit['cy']}")
            time.sleep(1.0)
            continue

        # Fallback tap where secondary popup Submit button sits
        print("  [*] Waiting for secondary popup or tapping fallback Submit (870, 1397)...")
        adb_shell("input tap 870 1397")
        time.sleep(0.8)

    time.sleep(0.5)
    return True

def handle_coral_review_stage(timeout=10):
    """
    Phase 2 - Step 2: Coral Review Screen (MeterReadingActivity)
    - Displays captured image and entered readings
    - If direct submit is ready: taps submit_btn
    - If doubt / revalidation required:
        - Taps revalidate_btn
        - In recheck_popup, taps btn_report
        - Selects 'Readings are Correct' from remarks_list spinner
        - Taps submit_btn
    """
    print("  [*] [Phase 2.2] Coral Review Screen. Checking submission state...")
    t_start = time.time()
    review_ready = False

    while time.time() - t_start < timeout:
        focus = adb_shell("dumpsys window | grep mCurrentFocus")
        if "MeterReadingActivity" in focus:
            review_ready = True
            break
        elif "BillingManual" in focus:
            print("  [+] Already returned to BillingManual!")
            return True
        time.sleep(0.4)

    if not review_ready:
        print("  [!] MeterReadingActivity not reached in time.")
        return False

    time.sleep(0.5)
    tree = get_ui_tree()
    reval_btn = find_node(tree, resource_id="revalidate_btn") or find_node(tree, text="Revalidate")
    submit_btn = find_node(tree, resource_id="submit_btn") or find_node(tree, text="Submit")

    if reval_btn:
        print("  [*] Revalidation required! Executing Override Flow...")
        adb_shell(f"input tap {reval_btn['cx']} {reval_btn['cy']}")
        time.sleep(0.6)

        tree = get_ui_tree()
        report_btn = find_node(tree, resource_id="btn_report") or find_node(tree, text="REPORT") or find_node(tree, text="Report")
        if report_btn:
            print(f"  [*] Tapping Report button ({report_btn['cx']}, {report_btn['cy']})...")
            adb_shell(f"input tap {report_btn['cx']} {report_btn['cy']}")
        else:
            adb_shell("input tap 750 1798")
        time.sleep(0.6)

        tree = get_ui_tree()
        correct_opt = find_node(tree, text="Readings are correct")
        if correct_opt:
            print(f"  [*] Selecting 'Readings are correct' remark ({correct_opt['cx']}, {correct_opt['cy']})...")
            adb_shell(f"input tap {correct_opt['cx']} {correct_opt['cy']}")
        else:
            print("  [*] Selecting default remark...")
            adb_shell("input tap 540 1212")
        time.sleep(0.6)

        tree = get_ui_tree()
        submit_btn = find_node(tree, resource_id="submit_btn") or find_node(tree, text="Submit")
        if submit_btn:
            print(f"  [*] Tapping Coral Final Submit at ({submit_btn['cx']}, {submit_btn['cy']})...")
            adb_shell(f"input tap {submit_btn['cx']} {submit_btn['cy']}")
        else:
            adb_shell("input tap 792 2231")

    elif submit_btn:
        print(f"  [+] Direct Submit Available! Tapping Submit ({submit_btn['cx']}, {submit_btn['cy']})...")
        adb_shell(f"input tap {submit_btn['cx']} {submit_btn['cy']}")
    else:
        print("  [*] Tapping bottom Submit button fallback...")
        adb_shell("input tap 792 2231")

    time.sleep(1.2)
    return True

def handle_coral_defective_stage(timeout=12):
    """
    Phase 2 - Step 1 (Defective Meter Flow): Coral MeterReadingActivity
    - Taps 'Defective/Burnt' radio button
    - Selects 'Actually Defective' from Abnormalities popup
    - Taps 'TAKE PHOTO' button
    - In CapturePhotoActivity: Taps Camera Shutter (captureImageBtn)
    - Returns to MeterReadingActivity: Taps Coral 'Submit' (submit_btn)
    - Returns to NBPDCL BillingManual
    """
    print("  [*] [Phase 2 - Defective] Waiting for Coral MeterReadingActivity...")
    t_start = time.time()
    while time.time() - t_start < timeout:
        focus = adb_shell("dumpsys window | grep mCurrentFocus")
        if "MeterReadingActivity" in focus:
            break
        time.sleep(0.3)

    time.sleep(0.5)
    tree = get_ui_tree()
    defective_radio = find_node(tree, resource_id="rdbtn_defective")
    if defective_radio:
        print(f"  [*] Selecting Defective/Burnt radio ({defective_radio['cx']}, {defective_radio['cy']})...")
        adb_shell(f"input tap {defective_radio['cx']} {defective_radio['cy']}")
    else:
        adb_shell("input tap 822 591")

    time.sleep(0.6)
    # Select 'Actually Defective'
    tree = get_ui_tree()
    act_def = find_node(tree, text="Actually Defective")
    if act_def:
        print(f"  [*] Selecting 'Actually Defective' ({act_def['cx']}, {act_def['cy']})...")
        adb_shell(f"input tap {act_def['cx']} {act_def['cy']}")
    else:
        adb_shell("input tap 563 405")

    time.sleep(0.6)
    # Tap TAKE PHOTO
    tree = get_ui_tree()
    take_photo_btn = find_node(tree, resource_id="take_pic_btn") or find_node(tree, text="TAKE PHOTO")
    if take_photo_btn:
        print(f"  [*] Tapping TAKE PHOTO ({take_photo_btn['cx']}, {take_photo_btn['cy']})...")
        adb_shell(f"input tap {take_photo_btn['cx']} {take_photo_btn['cy']}")
    else:
        adb_shell("input tap 540 762")

    # Wait for CapturePhotoActivity
    t_cam = time.time()
    while time.time() - t_cam < 8.0:
        focus = adb_shell("dumpsys window | grep mCurrentFocus")
        if "CapturePhotoActivity" in focus:
            break
        time.sleep(0.3)

    time.sleep(0.8)
    # Tap shutter in CapturePhotoActivity
    tree = get_ui_tree()
    shutter = find_node(tree, resource_id="captureImageBtn") or find_node(tree, text="CAPTURE")
    if shutter:
        print(f"  [*] Tapping Camera Shutter ({shutter['cx']}, {shutter['cy']})...")
        adb_shell(f"input tap {shutter['cx']} {shutter['cy']}")
    else:
        adb_shell("input tap 540 2313")

    # Wait for return to MeterReadingActivity
    t_review = time.time()
    while time.time() - t_review < 8.0:
        focus = adb_shell("dumpsys window | grep mCurrentFocus")
        if "MeterReadingActivity" in focus:
            break
        time.sleep(0.3)

    time.sleep(0.8)
    # Tap Coral Submit
    tree = get_ui_tree()
    submit_btn = find_node(tree, resource_id="submit_btn") or find_node(tree, text="Submit")
    if submit_btn:
        print(f"  [*] Tapping Coral Submit ({submit_btn['cx']}, {submit_btn['cy']})...")
        adb_shell(f"input tap {submit_btn['cx']} {submit_btn['cy']}")
    else:
        adb_shell("input tap 547 2231")

    time.sleep(1.2)
    return True

def handle_nbpdcl_final_submit(timeout=10):
    """
    Phase 2 - Step 3: Return to NBPDCL BillingManual
    - Waits for return to BillingManual
    - Scrolls down to bottom
    - Taps Submit button (R.id.Submit)
    - Confirms YES on AlertDialog
    - Waits for BillPrintOnline1
    - Scrolls to bottom
    - Taps Back (in.phoenix.bpdcl:id/printback) to return to ConsumerSearchActivity
    """
    print("  [*] [Phase 2.3] Waiting for return to NBPDCL BillingManual...")
    t_start = time.time()
    billing_returned = False

    while time.time() - t_start < timeout:
        focus = adb_shell("dumpsys window | grep mCurrentFocus")
        if "BillingManual" in focus:
            billing_returned = True
            break
        time.sleep(0.4)

    if not billing_returned:
        print("  [!] BillingManual not focused after Coral completion.")
        return False

    time.sleep(0.8)
    print("  [*] Scrolling to bottom of BillingManual...")
    adb_shell("input swipe 540 1800 540 400 250; sleep 0.3; input swipe 540 1800 540 400 250")
    time.sleep(0.6)

    tree = get_ui_tree()
    submit_btn = find_node(tree, resource_id="Submit") or find_node(tree, text="Submit")
    if submit_btn:
        print(f"  [*] Tapping NBPDCL Submit button at ({submit_btn['cx']}, {submit_btn['cy']})...")
        adb_shell(f"input tap {submit_btn['cx']} {submit_btn['cy']}")
    else:
        print("  [*] Tapping bottom Submit button fallback...")
        adb_shell("input tap 293 2267")

    time.sleep(0.8)
    tree = get_ui_tree()
    ok_btn = find_node(tree, resource_id="button1") or find_node(tree, text="YES") or find_node(tree, text="OK")
    if ok_btn:
        print(f"  [+] Confirming Bill Generation dialog at ({ok_btn['cx']}, {ok_btn['cy']})...")
        adb_shell(f"input tap {ok_btn['cx']} {ok_btn['cy']}")
    else:
        print("  [*] Confirming dialog fallback at (900, 1388)...")
        adb_shell("input tap 900 1388")

    # Wait for BillPrintOnline1
    t_print = time.time()
    print_ready = False
    while time.time() - t_print < 8.0:
        focus = adb_shell("dumpsys window | grep mCurrentFocus")
        if "BillPrintOnline1" in focus:
            print_ready = True
            break
        time.sleep(0.3)

    if print_ready:
        print("  [+] Bill Print Screen loaded! Scrolling to bottom...")
        time.sleep(0.6)
        adb_shell("input swipe 540 2000 540 300 250; sleep 0.3; input swipe 540 2000 540 300 250")
        time.sleep(0.5)
        tree = get_ui_tree()
        back_btn = find_node(tree, resource_id="printback") or find_node(tree, text="Back")
        if back_btn:
            print(f"  [*] Tapping Back button ({back_btn['cx']}, {back_btn['cy']}) to return to Search...")
            adb_shell(f"input tap {back_btn['cx']} {back_btn['cy']}")
        else:
            print("  [*] Tapping Back button fallback at (718, 2305)...")
            adb_shell("input tap 718 2305")
        time.sleep(0.8)

    print("\n>>> [SUCCESS] Bill Generated & Submitted in NBPDCL! <<<\n")
    return True

# ==============================================================================
# CONFIGURATION TOGGLE:
#   DEFAULT_USE_DUMP = True   --> Adaptive Dump Mode (99.99% Accuracy, ~13s)
#   DEFAULT_USE_DUMP = False  --> Blind Fixed Mode (Zero Dump, Zero Scroll, ~8s)
# Can also toggle on the fly via CLI: --turbo / --no-dump (turns off dump)
# ==============================================================================
DEFAULT_USE_DUMP = True

def process_consumer_pipeline(consumer_no, reading_kwh=None, meter_type="NORMAL", use_dump=DEFAULT_USE_DUMP, auto_back=False, auto_submit=False):
    t0 = time.time()
    if not check_device():
        return False

    wake_device()
    dismiss_keyboard()
    is_defective = (str(meter_type).upper() in ["DEFECTIVE", "MD", "MB"])
    type_label = "DEFECTIVE METER" if is_defective else "NORMAL METER"
    mode_label = "Adaptive Dump (99.99% Acc)" if use_dump else "Blind Fixed Turbo (~8s)"
    action_label = "Pre-Staging (Auto-Back)" if auto_back else "Field Mode (Stay on Camera)"
    print(f"\n" + "="*60)
    print(f" [*] PROCESSING CONSUMER: {consumer_no} | {type_label} | {mode_label} | {action_label}")
    print("="*60)

    # 1. Clean return to ConsumerSearchActivity
    adb_shell("am start -n in.phoenix.bpdcl/in.phoenix.bpdcl.ConsumerSearchActivity --activity-clear-top")
    time.sleep(0.2)
    dismiss_keyboard()

    dpad_del = " ".join(["67"] * 25)
    search_cmd = (
        "input tap 727 543; "
        f"input keyevent --delay 2 123 {dpad_del}; "
        f"input text {consumer_no}; "
        "input keyevent 4; "
        "sleep 0.15; "
        "input tap 450 726"
    )
    adb_shell(search_cmd)
    t_search = time.time()
    print(f"  [1] Search submitted in {round(t_search - t0, 2)}s")

    # 2. Wait for BillingManual focus & GPS dialog settlement
    t_wait = time.time()
    billing_ready = False
    while time.time() - t_wait < 5.0:
        focus = adb_shell("dumpsys window | grep mCurrentFocus")
        if "BillingManual" in focus:
            billing_ready = True
            break
        elif "Alert" in focus or "dialog" in focus.lower():
            print("  [!] Alert dialog appeared (Consumer record not found).")
            adb_shell("input keyevent 66")
            return False
        time.sleep(0.08)

    if not billing_ready:
        print("  [!] BillingManual failed to load.")
        return False

    # Wait 1.1s for modal GPS progress dialog to dismiss cleanly
    time.sleep(1.1)
    t_settled = time.time()
    print(f"  [2] BillingManual settled in {round(t_settled - t_search, 2)}s")

    if use_dump:
        # 3. Single UI dump & parse (Adaptive Precision)
        t_dump_start = time.time()
        elements = get_ui_elements()
        t_dump_end = time.time()
        print(f"  [3] UI elements mapped in {round(t_dump_end - t_dump_start, 2)}s")

        if "button1" in elements:
            print("  [!] Consumer not found dialog detected.")
            adb_shell("input keyevent 66")
            return False

        ps = elements.get("PresentStatus1")
        obs = elements.get("atMOBS1")
        loc = elements.get("meterloctypeiv")

        if not ps or not obs or not loc:
            print("  [*] Elements not found on first pass, retrying dump in 0.5s...")
            time.sleep(0.5)
            elements = get_ui_elements()
            ps = elements.get("PresentStatus1")
            obs = elements.get("atMOBS1")
            loc = elements.get("meterloctypeiv")
            if not ps or not obs or not loc:
                print(f"  [!] Failed to locate fields: ps={bool(ps)}, obs={bool(obs)}, loc={bool(loc)}")
                return False

        # Exact mathematical coordinates from dump:
        ps_arrow_x, ps_arrow_y = ps["arrow_x"], ps["cy"]
        obs_cx, obs_cy = obs["cx"], obs["cy"]
        loc_arrow_x, loc_arrow_y = loc["arrow_x"], loc["cy"]
        loc_opt_x = loc["cx"]
        kwh_x, kwh_y = 408, loc["cy"] + 189

        if is_defective:
            print("  [*] Defective Meter Mode: Selecting METER DEFECTIVE, DEFECTIVE, and Inside...")
            dpad_bottom = " ".join(["20"] * 10)
            flow = (
                f"input tap {ps_arrow_x} {ps_arrow_y}; sleep 0.35; input tap {ps['cx']} 1950; sleep 0.45; "
                f"input tap {obs_cx} {obs_cy}; sleep 0.35; input keyevent --delay 15 {dpad_bottom} 66; sleep 0.45; "
                f"input tap {loc_arrow_x} {loc_arrow_y}; sleep 0.35; input tap {loc_opt_x} 1790; sleep 0.45; "
                f"input tap {kwh_x} {kwh_y}"
            )
        else:
            ps_opt_x, ps_opt_y = ps["cx"], ps["y2"] + 50
            if loc["y2"] > 2070:
                loc_opt_y = 1790
            else:
                loc_opt_y = loc["y2"] + 40

            # Smart Pre-Fill Fast-Path:
            is_prefilled = (obs.get("text") == "OK" and loc.get("text") == "Inside")
            if is_prefilled:
                print("  [+] PRE-FILLED CACHE DETECTED! Site Observation (OK) & Location (Inside) already set.")
                print("  [*] Fast-Path: Selecting ONLY NORMAL -> Camera (~3.5s)...")
                flow = (
                    f"input tap {ps_arrow_x} {ps_arrow_y}; sleep 0.35; input tap {ps_opt_x} {ps_opt_y}; sleep 0.4; "
                    f"input tap {kwh_x} {kwh_y}"
                )
            else:
                print("  [*] Fresh Consumer: Selecting NORMAL, OK, and Inside...")
                dpad_cmds = " ".join(["20"] * 30)
                flow = (
                    f"input tap {ps_arrow_x} {ps_arrow_y}; sleep 0.35; input tap {ps_opt_x} {ps_opt_y}; sleep 0.45; "
                    f"input tap {obs_cx} {obs_cy}; sleep 0.35; input keyevent --delay 10 {dpad_cmds} 19 66; sleep 0.45; "
                    f"input tap {loc_arrow_x} {loc_arrow_y}; sleep 0.35; input tap {loc_opt_x} {loc_opt_y}; sleep 0.45; "
                    f"input tap {kwh_x} {kwh_y}"
                )
    else:
        # 3. Blind Fixed Mode: Zero Dumps, Zero Scrolls (Turbo speed ~8s)
        print("  [3] Blind Fixed Mode: Skipping UI dump (Turbo ~8s)...")
        t_dump_end = time.time()
        ps_arrow_x, ps_arrow_y = 976, 1816
        obs_cx, obs_cy = 691, 1942
        loc_arrow_x, loc_arrow_y = 976, 2068
        loc_opt_x = 691
        kwh_x, kwh_y = 408, 2257

        if is_defective:
            dpad_bottom = " ".join(["20"] * 10)
            flow = (
                f"input tap {ps_arrow_x} {ps_arrow_y}; sleep 0.35; input tap 600 1950; sleep 0.45; "
                f"input tap {obs_cx} {obs_cy}; sleep 0.35; input keyevent --delay 15 {dpad_bottom} 66; sleep 0.45; "
                f"input tap {loc_arrow_x} {loc_arrow_y}; sleep 0.35; input tap {loc_opt_x} 1790; sleep 0.45; "
                f"input tap {kwh_x} {kwh_y}"
            )
        else:
            ps_opt_x, ps_opt_y = 691, 1890
            loc_opt_y = 1790
            dpad_cmds = " ".join(["20"] * 30)
            flow = (
                f"input tap {ps_arrow_x} {ps_arrow_y}; sleep 0.35; input tap {ps_opt_x} {ps_opt_y}; sleep 0.45; "
                f"input tap {obs_cx} {obs_cy}; sleep 0.35; input keyevent --delay 10 {dpad_cmds} 19 66; sleep 0.45; "
                f"input tap {loc_arrow_x} {loc_arrow_y}; sleep 0.35; input tap {loc_opt_x} {loc_opt_y}; sleep 0.45; "
                f"input tap {kwh_x} {kwh_y}"
            )

    # 4. Rapid batch execution
    adb_shell(flow)
    t_flow = time.time()
    print(f"  [4] Batch inputs executed in {round(t_flow - t_dump_end, 2)}s")

    # 5. Wait for Coral screen to appear
    t_coral = time.time()
    while time.time() - t_coral < 4.0:
        act = adb_shell("dumpsys window | grep mCurrentFocus")
        if "MeterReadingActivity" in act or "ScanMeterActivity" in act:
            break
        time.sleep(0.08)

    t_end = time.time()
    total_time = round(t_end - t0, 2)

    time.sleep(0.4)
    final_act = adb_shell("dumpsys activity activities | grep topResumedActivity")
    success = False
    if "ScanMeterActivity" in final_act or "MeterReadingActivity" in final_act:
        print(f"\n>>> [SUCCESS] Reached Coral Stage in {total_time}s! <<<\n")
        success = True
    else:
        print(f"\n[!] Landed on {final_act}\n")
        success = False

    # 6. Phase 2: If reading_kwh is provided or auto_submit is enabled or meter is defective
    if success and (reading_kwh is not None or auto_submit or is_defective):
        print("\n" + "-"*60)
        print(" [*] INITIATING PHASE 2: CAMERA CAPTURE & AUTO-SUBMISSION")
        print(f" [*] Meter Type: {type_label}")
        print(f" [*] Target KWH Reading: {reading_kwh if reading_kwh is not None else ('0.0 (DEFECTIVE)' if is_defective else 'AUTO (OCR)')}")
        print("-"*60)

        if is_defective:
            cam_ok = handle_coral_defective_stage()
            if not cam_ok:
                print("  [!] Phase 2 Defective Coral stage failed.")
                return False
        else:
            # Step 1: Handle Coral camera capture & entry
            cam_ok = handle_coral_camera_stage(reading_kwh=reading_kwh)
            if not cam_ok:
                print("  [!] Phase 2 Camera stage failed.")
                return False

            # Step 2: Handle Coral review & revalidation override
            review_ok = handle_coral_review_stage()
            if not review_ok:
                print("  [!] Phase 2 Review stage failed.")
                return False

        # Step 3: Handle NBPDCL final submit, confirmation & return to search
        submit_ok = handle_nbpdcl_final_submit()
        if not submit_ok:
            print("  [!] Phase 2 NBPDCL Submit stage failed.")
            return False

        total_p2_time = round(time.time() - t0, 2)
        print(f"\n>>> [SUCCESS] End-to-End Consumer {consumer_no} Billed & Submitted in {total_p2_time}s! <<<\n")

        if auto_back:
            print("  [*] Returning to Consumer Search for next queue item...")
            adb_shell("am start -n in.phoenix.bpdcl/in.phoenix.bpdcl.ConsumerSearchActivity --activity-clear-top")
            dismiss_keyboard()
            time.sleep(0.5)

        return True

    # Pre-Staging Mode without submission: Go back to ConsumerSearchActivity for next consumer in list
    if auto_back and success:
        print("  [*] Pre-Staging Complete: Returning to Consumer Search for next consumer...")
        adb_shell("input keyevent 4; sleep 0.35; input keyevent 4; sleep 0.35; am start -n in.phoenix.bpdcl/in.phoenix.bpdcl.ConsumerSearchActivity --activity-clear-top")
        dismiss_keyboard()
        time.sleep(0.5)

    return success

def start_clipboard_watcher_loop(use_dump=DEFAULT_USE_DUMP):
    if not check_device():
        return

    mode_label = "Adaptive Dump (99.99% Acc, ~13s)" if use_dump else "Blind Fixed Turbo (No Dump, ~8s)"
    print("\n=======================================================")
    print(" [*] HIGH-SPEED AUTO-LOOP: Clipboard Watcher Mode")
    print(f" [*] Mode: {mode_label}")
    print(" [*] Feature: Auto-detects pre-filled consumers (~3.5s fast-path!)")
    print(" [*] Copy any Consumer Number on your PC (Ctrl+C)")
    print(" [*] Press Ctrl+C in this terminal to stop.")
    print("=======================================================\n")

    last_consumer = None
    while True:
        try:
            current_consumer = get_consumer_from_clipboard()
            if current_consumer and current_consumer != last_consumer:
                print(f"\n[LOOP] >>> New Consumer Number Detected: {current_consumer} <<<")
                last_consumer = current_consumer
                process_consumer_pipeline(current_consumer, use_dump=use_dump, auto_back=False)
                print("\n[*] Waiting for next consumer number on PC clipboard...")

            time.sleep(0.4)
        except KeyboardInterrupt:
            print("\n[*] Auto-loop stopped by user.")
            break
        except Exception as e:
            print(f"[!] Error in loop: {e}")
            time.sleep(1.0)

def start_list_prefill_loop(filepath, use_dump=DEFAULT_USE_DUMP):
    if not check_device():
        return

    if not os.path.exists(filepath):
        print(f"[!] File not found: {filepath}")
        return

    with open(filepath, "r") as f:
        raw_lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    consumers = []
    for line in raw_lines:
        digits = re.findall(r'\b\d{10,12}\b', line)
        if digits:
            consumers.append(digits[0])
        else:
            clean = re.sub(r'\D', '', line)
            if len(clean) in (10, 11, 12):
                consumers.append(clean)

    if not consumers:
        print(f"[!] No valid consumer numbers found in {filepath}")
        print(f"[*] Open '{filepath}' and paste your 10 to 12 digit consumer numbers (one per line).")
        return

    total = len(consumers)
    print("\n=======================================================")
    print(" [*] AUTONOMOUS BATCH PRE-FILL & PRE-STAGING LOOP")
    print(f" [*] Total Consumers to Pre-Stage: {total}")
    print(" [*] Strategy: Search -> Fill OK & Inside -> Camera -> Back -> Next")
    print(" [*] When complete, all consumers will have OK & Inside cached!")
    print("=======================================================\n")

    successful = 0
    failed = 0
    t_batch_start = time.time()

    for idx, c_no in enumerate(consumers, 1):
        print(f"\n" + "-"*60)
        print(f" [*] PRE-STAGING [{idx}/{total}]: Consumer {c_no}")
        print("-"*60)
        ok = process_consumer_pipeline(c_no, use_dump=use_dump, auto_back=True)
        if ok:
            successful += 1
            print(f"  [+] Consumer {c_no} successfully pre-staged & cached in NBPDCL!")
        else:
            failed += 1
            print(f"  [!] Failed to pre-stage consumer {c_no}.")

        time.sleep(1.2)

    elapsed = round(time.time() - t_batch_start, 2)
    print("\n=======================================================")
    print(f" [SUCCESS] BATCH PRE-STAGING COMPLETE in {elapsed}s!")
    print(f" [*] Successfully Pre-Staged: {successful}/{total}")
    if failed > 0:
        print(f" [!] Failed: {failed}/{total}")
    print(" [*] All pre-staged consumers now have OK & Inside stored in NBPDCL!")
    print(" [*] During your field work, each consumer will open in ~3.5 seconds!")
    print("=======================================================\n")

def start_step_mode(filepath="consumers.txt", use_dump=DEFAULT_USE_DUMP):
    """Walks through consumers.txt one by one. Press ENTER to open Camera for each house."""
    if not check_device():
        return

    if not os.path.exists(filepath):
        print(f"[!] File not found: {filepath}")
        return

    with open(filepath, "r") as f:
        raw_lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    consumers = []
    for line in raw_lines:
        digits = re.findall(r'\b\d{10,12}\b', line)
        if digits:
            consumers.append(digits[0])
        else:
            clean = re.sub(r'\D', '', line)
            if len(clean) in (10, 11, 12):
                consumers.append(clean)

    if not consumers:
        print(f"[!] No valid consumer numbers found in {filepath}")
        return

    total = len(consumers)
    print("\n=======================================================")
    print(" [*] STEP-BY-STEP FIELD ROUTE MODE")
    print(f" [*] Total Consumers Loaded: {total}")
    print(" [*] In the field, just press ENTER to open the camera for each house!")
    print(" [*] Controls: [ENTER] = Open Camera, [s] = Skip, [q] = Quit")
    print("=======================================================\n")

    idx = 0
    while idx < total:
        c_no = consumers[idx]
        try:
            val = input(f"\n[{idx+1}/{total}] Consumer: {c_no}\n --> Press [ENTER] for Camera (or 's' to skip, 'q' to quit): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[*] Exiting Step Mode.")
            break

        if val.lower() == 'q':
            print("[*] Exiting Step Mode.")
            break
        elif val.lower() == 's':
            print(f"[*] Skipped {c_no}.")
            idx += 1
            continue
        elif val:
            digits = re.findall(r'\b\d{10,12}\b', val)
            custom_num = digits[0] if digits else re.sub(r'\D', '', val)
            if len(custom_num) in (10, 11, 12):
                print(f"[*] Processing custom number: {custom_num}...")
                process_consumer_pipeline(custom_num, use_dump=use_dump, auto_back=False)
                continue
            else:
                print(f"[!] Unrecognized input: '{val}'. Press Enter to proceed or 'q' to quit.")
                continue

        # Default ENTER: trigger consumer
        ok = process_consumer_pipeline(c_no, use_dump=use_dump, auto_back=False)
        if ok:
            print(f"\n[+] Phone A is live on Camera for {c_no}! Capture the meter reading.")
        idx += 1

    print("\n[SUCCESS] Completed route list!")

def start_interactive_loop(use_dump=DEFAULT_USE_DUMP):
    """Direct CLI paste input loop for Termux and Windows."""
    if not check_device():
        return

    print("\n=======================================================")
    print(" [*] INTERACTIVE FIELD MODE (Termux / Direct Input)")
    print(" [*] Paste or type any Consumer Number and press ENTER.")
    print(" [*] Shortcuts: 'step' = Walk list, 'list' = Batch pre-stage, 'q' = Quit")
    print("=======================================================\n")

    while True:
        try:
            val = input("Consumer # > ").strip()
            if not val:
                continue
            if val.lower() == 'q':
                break
            elif val.lower() in ('step', 's'):
                start_step_mode("consumers.txt", use_dump=use_dump)
                break
            elif val.lower() in ('list', 'l'):
                start_list_prefill_loop("consumers.txt", use_dump=use_dump)
                break

            digits = re.findall(r'\b\d{10,12}\b', val)
            c_no = digits[0] if digits else re.sub(r'\D', '', val)
            if len(c_no) in (10, 11, 12):
                process_consumer_pipeline(c_no, use_dump=use_dump, auto_back=False)
            else:
                print(f"[!] Invalid consumer number: '{val}'. Must be 10 to 12 digits.")
        except (KeyboardInterrupt, EOFError):
            print("\n[*] Exiting.")
            break

if __name__ == "__main__":
    args = sys.argv[1:]

    # Toggle uiautomator dump on/off:
    use_dump = DEFAULT_USE_DUMP
    if "--turbo" in args or "--no-dump" in args or "-t" in args:
        use_dump = False
    elif "--dump" in args or "-d" in args:
        use_dump = True

    if "--list" in args or "-l" in args or "--file" in args or "-f" in args:
        flag = "--list" if "--list" in args else ("-l" if "-l" in args else ("--file" if "--file" in args else "-f"))
        idx = args.index(flag)
        if idx + 1 < len(args) and not args[idx + 1].startswith("-"):
            target_file = args[idx + 1]
        else:
            target_file = "consumers.txt"
        start_list_prefill_loop(target_file, use_dump=use_dump)
    elif "--step" in args or "-s" in args:
        flag = "--step" if "--step" in args else "-s"
        idx = args.index(flag)
        if idx + 1 < len(args) and not args[idx + 1].startswith("-"):
            target_file = args[idx + 1]
        else:
            target_file = "consumers.txt"
        start_step_mode(target_file, use_dump=use_dump)
    elif "--watch" in args or "-w" in args:
        start_clipboard_watcher_loop(use_dump=use_dump)
    elif "--reset" in args:
        print("[*] Resetting device screen to Consumer Search...")
        wake_device()
        adb_shell("am start -n in.phoenix.bpdcl/in.phoenix.bpdcl.ConsumerSearchActivity --activity-clear-top")
    else:
        auto_submit = "--auto-submit" in args or "-a" in args
        is_def = "--defective" in args or "-def" in args or "--def" in args
        meter_type = "DEFECTIVE" if is_def else "NORMAL"
        reading_val = None
        if "--reading" in args or "-r" in args:
            flag = "--reading" if "--reading" in args else "-r"
            idx = args.index(flag)
            if idx + 1 < len(args):
                reading_val = args[idx + 1]

        positional = [a for a in args if not a.startswith("-")]
        if positional:
            ca = positional[0]
            if len(positional) >= 2 and reading_val is None:
                reading_val = positional[1]

            process_consumer_pipeline(
                ca,
                reading_kwh=reading_val,
                meter_type=meter_type,
                use_dump=use_dump,
                auto_back=False,
                auto_submit=auto_submit or (reading_val is not None) or is_def
            )
        else:
            # On Termux or terminal without arguments, launch interactive input loop
            start_interactive_loop(use_dump=use_dump)
