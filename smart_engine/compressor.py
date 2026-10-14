"""
compressor.py – Prunes raw Android UI hierarchy down to a compact ~150-token state for Jev / System 1 models.
"""
import re
import xml.etree.ElementTree as ET

class ContextCompressor:
    def __init__(self):
        pass

    @staticmethod
    def _parse_bounds(bounds_str):
        if not bounds_str:
            return 0, 0, 0, 0, 0, 0
        matches = re.findall(r'\d+', bounds_str)
        if len(matches) >= 4:
            x1, y1, x2, y2 = map(int, matches[:4])
            return x1, y1, x2, y2, (x1 + x2) // 2, (y1 + y2) // 2
        return 0, 0, 0, 0, 0, 0

    def compress_xml(self, xml_string, screen=""):
        if not xml_string:
            return {"screen": screen, "options": []}

        try:
            root = ET.fromstring(xml_string)
        except Exception:
            return {"screen": screen, "options": []}

        alert = None
        options = []

        alert_title = ""
        alert_msg = ""

        for node in root.iter("node"):
            res_id = node.attrib.get("resource-id", "")
            text = node.attrib.get("text", "").strip()
            content_desc = node.attrib.get("content-desc", "").strip()
            clickable = node.attrib.get("clickable", "false") == "true"
            cls = node.attrib.get("class", "")
            bounds = node.attrib.get("bounds", "")

            # Detect dialog title / message
            if "alertTitle" in res_id or "title" in res_id.lower():
                if text:
                    alert_title = text
            elif "message" in res_id.lower() or "alert_message" in res_id.lower():
                if text:
                    alert_msg = text

            # Clean display label
            label = text or content_desc
            clean_id = res_id.split("/")[-1] if "/" in res_id else res_id

            # Keep actionable / interactive nodes
            is_input = "EditText" in cls
            is_btn = "Button" in cls or clickable or is_input
            if is_btn and (label or clean_id):
                x1, y1, x2, y2, cx, cy = self._parse_bounds(bounds)
                options.append({
                    "id": clean_id,
                    "text": label,
                    "type": "input" if is_input else ("button" if "Button" in cls else "option"),
                    "bounds": [x1, y1, x2, y2],
                    "center": [cx, cy]
                })

        result = {"screen": screen, "options": options}
        if alert_title or alert_msg:
            result["alert"] = {
                "title": alert_title,
                "message": alert_msg
            }

        return result

    def to_jev_state(self, compressed_dict, goal="Advance to next step"):
        options = compressed_dict.get("options", [])
        visible = [
            f"[{opt.get('type')}] {opt.get('text') or opt.get('id')}"
            for opt in options if opt.get("text") or opt.get("id")
        ]

        state = {
            "screen": compressed_dict.get("screen", ""),
            "goal": goal,
            "visible_options": visible
        }

        if "alert" in compressed_dict:
            state["alert"] = compressed_dict["alert"]

        return state
