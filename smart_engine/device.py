"""
device.py – High-speed device wrapper around uiautomator2 with auto-discovery and ADB fallback.
"""
import os
import time
import subprocess

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import uiautomator2 as u2
except ImportError:
    u2 = None

def get_online_adb_devices():
    """
    Returns a list of device serials/IPs currently connected and online in ADB.
    """
    try:
        res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=3)
        devices = []
        for line in res.stdout.strip().splitlines()[1:]:
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        return devices
    except Exception:
        return []

def resolve_device_serial(explicit_serial=None):
    """
    Smart auto-discovery ladder for ADB device serial / IP:
      1. Explicit argument passed via CLI / code (highest priority).
      2. If not specified, scan ADB for online devices:
         - If exactly 1 device is online, automatically connect to it!
         - If multiple devices are online, prefer ADB_DEVICE_SERIAL from .env if online,
           otherwise select the primary active device.
      3. Fallback to ADB_DEVICE_SERIAL from .env or default '192.168.9.40:5555'.
    """
    if explicit_serial and str(explicit_serial).strip():
        return str(explicit_serial).strip()

    online_devices = get_online_adb_devices()
    env_serial = os.environ.get("ADB_DEVICE_SERIAL", "").strip()

    # If exactly 1 device is active in ADB, use it automatically
    if len(online_devices) == 1:
        detected = online_devices[0]
        print(f"[+] Auto-detected active ADB device: {detected}")
        return detected

    # If multiple devices are active
    if len(online_devices) > 1:
        if env_serial and env_serial in online_devices:
            print(f"[+] Multiple ADB devices found. Using configured device from .env: {env_serial}")
            return env_serial
        chosen = online_devices[0]
        print(f"[!] Multiple ADB devices detected: {online_devices}. Auto-selecting: {chosen}")
        return chosen

    # If no devices are currently reported online by adb, fallback to .env or default
    if env_serial:
        return env_serial
    return "192.168.9.40:5555"

class SmartDevice:
    def __init__(self, serial=None):
        self.serial = resolve_device_serial(serial)
        self.d = None

    def connect(self, timeout=5.0):
        try:
            self.d = u2.connect(self.serial)
            # Ping info to verify active connection
            _ = self.d.info
            return True
        except Exception as e:
            print(f"[!] uiautomator2 connect failed on {self.serial}: {e}")
            self.d = None
            return False

    def is_connected(self):
        return self.d is not None

    def get_compressed_hierarchy(self):
        """
        Dumps the UI hierarchy directly from memory with layout compression.
        """
        if self.d:
            try:
                return self.d.dump_hierarchy(compressed=True)
            except Exception as e:
                print(f"[!] u2 dump_hierarchy error: {e}")
        return ""

    def click_element(self, text=None, resource_id=None, timeout=2.0):
        """
        Clicks element semantically by text or resource ID.
        """
        if not self.d:
            return False

        if text and resource_id:
            el = self.d(text=text, resourceId=resource_id)
        elif text:
            el = self.d(text=text)
        elif resource_id:
            el = self.d(resourceId=resource_id)
        else:
            return False

        if el.exists(timeout=timeout):
            el.click()
            return True
        return False

    def set_text(self, text, resource_id=None, cls=None, timeout=2.0):
        """
        Sets text into input field without keyboard keyevent del loops.
        """
        if not self.d:
            return False

        if resource_id:
            el = self.d(resourceId=resource_id)
        elif cls:
            el = self.d(className=cls)
        else:
            el = self.d(className="android.widget.EditText")

        if el.exists(timeout=timeout):
            el.set_text(text)
            return True
        return False

    def current_activity(self):
        if self.d:
            try:
                cur = self.d.app_current()
                return cur.get("activity", "")
            except Exception:
                pass
        return ""

    def tap_coordinates(self, x, y):
        if self.d:
            self.d.click(x, y)
        else:
            subprocess.run(["adb", "-s", self.serial, "shell", "input", "tap", str(x), str(y)], capture_output=True)

    def go_back(self):
        if self.d:
            self.d.press("back")
        else:
            subprocess.run(["adb", "-s", self.serial, "shell", "input", "keyevent", "4"], capture_output=True)

    def wake_screen(self):
        if self.d:
            self.d.screen_on()
        else:
            subprocess.run(["adb", "-s", self.serial, "shell", "input", "keyevent", "224"], capture_output=True)
