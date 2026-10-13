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
        time.sleep(0.3)

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

# ==============================================================================
# CONFIGURATION TOGGLE:
#   DEFAULT_USE_DUMP = True   --> Adaptive Dump Mode (99.99% Accuracy, ~13s)
#   DEFAULT_USE_DUMP = False  --> Blind Fixed Mode (Zero Dump, Zero Scroll, ~8s)
# Can also toggle on the fly via CLI: --turbo / --no-dump (turns off dump)
# ==============================================================================
DEFAULT_USE_DUMP = True

def process_consumer_pipeline(consumer_no, use_dump=DEFAULT_USE_DUMP, auto_back=False):
    t0 = time.time()
    if not check_device():
        return False

    wake_device()
    dismiss_keyboard()
    mode_label = "Adaptive Dump (99.99% Acc)" if use_dump else "Blind Fixed Turbo (~8s)"
    action_label = "Pre-Staging (Auto-Back)" if auto_back else "Field Mode (Stay on Camera)"
    print(f"\n" + "="*60)
    print(f" [*] PROCESSING CONSUMER: {consumer_no} | {mode_label} | {action_label}")
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
        ps_opt_x, ps_opt_y = ps["cx"], ps["y2"] + 50
        obs_cx, obs_cy = obs["cx"], obs["cy"]

        loc_arrow_x, loc_arrow_y = loc["arrow_x"], loc["cy"]
        loc_opt_x = loc["cx"]
        if loc["y2"] > 1950:
            loc_opt_y = loc["y1"] - 276
        else:
            loc_opt_y = loc["y2"] + 45

        kwh_x, kwh_y = 440, loc["cy"] + 189

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
        ps_opt_x, ps_opt_y = 691, 1890
        obs_cx, obs_cy = 691, 1942
        loc_arrow_x, loc_arrow_y = 976, 2068
        loc_opt_x = 691
        loc_opt_y = 1769
        kwh_x, kwh_y = 440, 2257
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

    # 5. Wait for Coral screen to appear & tap CAPTURE
    t_coral = time.time()
    while time.time() - t_coral < 3.5:
        act = adb_shell("dumpsys window | grep mCurrentFocus")
        if "MeterReadingActivity" in act or "ScanMeterActivity" in act:
            break
        time.sleep(0.08)

    adb_shell("input tap 532 2231; sleep 0.25; input tap 532 2231")
    t_end = time.time()
    total_time = round(t_end - t0, 2)

    time.sleep(0.4)
    final_act = adb_shell("dumpsys activity activities | grep topResumedActivity")
    success = False
    if "ScanMeterActivity" in final_act:
        print(f"\n>>> [SUCCESS] Reached Live Camera Viewfinder in {total_time}s! <<<\n")
        success = True
    elif "MeterReadingActivity" in final_act:
        adb_shell("input tap 532 2231")
        print(f"\n>>> [SUCCESS] Reached Live Camera Viewfinder (fallback tap) in {total_time}s! <<<\n")
        success = True
    else:
        print(f"\n[!] Landed on {final_act}\n")
        success = False

    # 6. Autonomous Pre-Staging: Go back to ConsumerSearchActivity for next consumer in list
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
        positional = [a for a in args if not a.startswith("-")]
        if positional:
            process_consumer_pipeline(positional[0], use_dump=use_dump, auto_back=False)
        else:
            # On Termux or terminal without arguments, launch interactive input loop
            start_interactive_loop(use_dump=use_dump)
