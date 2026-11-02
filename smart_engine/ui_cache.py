"""
ui_cache.py – Universal Resolution-Aware Dynamic UI Coordinate Cache for Android Automation.

Features:
  - Dynamic Self-Calibration: Elements are located once via semantic selectors and their
    coordinates and normalized ratios (rx, ry) are cached.
  - Universal Multi-Device Compatibility: Caches by device resolution (width, height) and
    calculates proportional screen ratios so automation adapts to any screen aspect ratio or display size.
  - Resilient Self-Healing: If a cached action fails or a screen transition misses, the cache
    is invalidated and falls back to semantic selector discovery.
  - Fast Activity Detection: Bypasses heavy dumpsys parsing with targeted grep checks.
"""
import os
import re
import json

class UniversalUICache:
    _instance = None

    def __init__(self, cache_file=None):
        self._cache = {}  # Format: { resolution_key: { element_key: {"x": int, "y": int, "rx": float, "ry": float} } }
        self._ratio_cache = {}  # Format: { element_key: {"rx": float, "ry": float} }
        self.cache_file = cache_file or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ui_cache.json")
        self.load_cache()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_resolution(self, d):
        """
        Retrieves device screen resolution (width, height).
        """
        if not d:
            return (1080, 2400)
        try:
            ws = d.window_size()
            if isinstance(ws, (tuple, list)) and len(ws) >= 2:
                # Ensure width is smaller dimension for portrait
                w, h = int(ws[0]), int(ws[1])
                return (min(w, h), max(w, h))
        except Exception:
            pass
        return (1080, 2400)

    def get_resolution_key(self, d):
        w, h = self.get_resolution(d)
        return f"{w}x{h}"

    def get_coordinates(self, key, d):
        """
        Returns (x, y) pixel coordinates for the element on the active device.
        If cached for exact resolution, returns exact pixels.
        If cached on a different resolution, calculates proportional pixels from universal ratios.
        Returns None if element has never been seen.
        """
        res_key = self.get_resolution_key(d)
        w, h = self.get_resolution(d)

        # 1. Exact resolution match
        if res_key in self._cache and key in self._cache[res_key]:
            entry = self._cache[res_key][key]
            return entry["x"], entry["y"]

        # 2. Universal ratio scaling
        if key in self._ratio_cache:
            entry = self._ratio_cache[key]
            calc_x = int(round(entry["rx"] * w))
            calc_y = int(round(entry["ry"] * h))
            return calc_x, calc_y

        return None

    def cache_element_bounds(self, key, d, bounds):
        """
        Caches element bounds dictionary {'left': l, 'top': t, 'right': r, 'bottom': b}.
        Computes center (cx, cy) and normalized ratios (rx, ry).
        """
        if not bounds:
            return None
        w, h = self.get_resolution(d)
        res_key = self.get_resolution_key(d)

        cx = (bounds.get("left", 0) + bounds.get("right", 0)) // 2
        cy = (bounds.get("top", 0) + bounds.get("bottom", 0)) // 2

        if w <= 0 or h <= 0 or cx <= 0 or cy <= 0:
            return None

        rx = round(cx / float(w), 4)
        ry = round(cy / float(h), 4)

        if res_key not in self._cache:
            self._cache[res_key] = {}

        self._cache[res_key][key] = {"x": cx, "y": cy, "rx": rx, "ry": ry}
        self._ratio_cache[key] = {"rx": rx, "ry": ry}
        return cx, cy

    def resolve_and_cache(self, key, d, selector_obj):
        """
        Attempts to read bounds from selector_obj.info and caches them.
        Returns (cx, cy) if successful, None otherwise.
        """
        if not selector_obj or not d:
            return None
        try:
            info = selector_obj.info
            bounds = info.get("bounds")
            if bounds:
                return self.cache_element_bounds(key, d, bounds)
        except Exception:
            pass
        return None

    def tap(self, key, d, selector_obj=None, fallback_coords=None):
        """
        Fast Tap:
          1. Uses cached coordinates directly if available.
          2. Otherwise uses selector_obj to find, cache, and click.
          3. Otherwise falls back to provided fallback_coords (scaled to resolution).
        """
        if not d:
            return False

        # Tier 1: Cached coordinates
        coords = self.get_coordinates(key, d)
        if coords:
            try:
                d.click(coords[0], coords[1])
                return True
            except Exception:
                self.invalidate(key, d)

        # Tier 2: Semantic Selector
        if selector_obj:
            try:
                resolved = self.resolve_and_cache(key, d, selector_obj)
                if resolved:
                    d.click(resolved[0], resolved[1])
                    return True
                elif selector_obj.exists(timeout=0.2):
                    selector_obj.click()
                    return True
            except Exception:
                pass

        # Tier 3: Scaled Fallback Coords
        if fallback_coords:
            try:
                w, h = self.get_resolution(d)
                # Default baseline is 1080x2400
                bx, by = fallback_coords
                scale_x = int(round(bx * (w / 1080.0)))
                scale_y = int(round(by * (h / 2400.0)))
                d.click(scale_x, scale_y)
                return True
            except Exception:
                pass

        return False

    def invalidate(self, key=None, d=None):
        """
        Invalidates cached coordinates for a given key (or all keys).
        """
        if key is None:
            self._cache.clear()
            self._ratio_cache.clear()
            return

        if d:
            res_key = self.get_resolution_key(d)
            if res_key in self._cache and key in self._cache[res_key]:
                del self._cache[res_key][key]

        if key in self._ratio_cache:
            del self._ratio_cache[key]

    def load_cache(self):
        if self.cache_file and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._cache = data.get("resolutions", {})
                    self._ratio_cache = data.get("ratios", {})
            except Exception:
                self._cache = {}
                self._ratio_cache = {}

    def save_cache(self):
        if not self.cache_file:
            return
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump({"resolutions": self._cache, "ratios": self._ratio_cache}, f, indent=2)
        except Exception:
            pass


def fast_get_current_activity(d):
    """
    Lightweight activity detection (~110-140ms) vs heavy d.app_current() (750-2100ms).
    """
    if not d:
        return "", ""
    try:
        out = d.shell("dumpsys window windows | grep mCurrentFocus").output or ""
        m = re.search(r"mCurrentFocus=Window\{[^\}]*\s+([^\s/\}]+)/([^\s/\}]+)", out)
        if m:
            return m.group(1), m.group(2)
        out2 = d.shell("dumpsys activity activities | grep mResumedActivity").output or ""
        m2 = re.search(r"mResumedActivity:[^\}]*\s+([^\s/\}]+)/([^\s/\}]+)", out2)
        if m2:
            return m2.group(1), m2.group(2)
    except Exception:
        pass

    try:
        cur = d.app_current()
        return cur.get("package", ""), cur.get("activity", "")
    except Exception:
        return "", ""
