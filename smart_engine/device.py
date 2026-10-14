"""
device.py – High-speed device wrapper around uiautomator2 with fallback to ADB.
"""
import time
import subprocess
import uiautomator2 as u2

class SmartDevice:
    def __init__(self, serial="192.168.9.40:5555"):
        self.serial = serial
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
