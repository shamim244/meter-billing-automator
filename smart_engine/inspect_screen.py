import os
import sys
import json
import time
import argparse
import uiautomator2 as u2

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from smart_engine.compressor import ContextCompressor

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--click", help="Resource ID or text of element to click before dumping")
    parser.add_argument("--all-text", action="store_true", help="Dump all visible text nodes on screen")
    args = parser.parse_args()

    d = u2.connect("192.168.9.40:5555")
    if args.click:
        print(f"[*] Clicking: {args.click}")
        if "/" in args.click or ":" in args.click:
            d(resourceId=args.click).click()
        else:
            d(text=args.click).click()
        time.sleep(0.6)

    cur = d.app_current()
    print("=" * 60)
    print(f"Active Screen: Package={cur.get('package')} | Activity={cur.get('activity')}")
    print("=" * 60)

    if args.all_text:
        nodes = []
        for n in d.xpath('//*[@text!=""]').all():
            text = n.attrib.get("text", "").strip()
            if text:
                nodes.append({
                    "id": n.attrib.get("resource-id", "").split("/")[-1],
                    "text": text,
                    "class": n.attrib.get("class", "").split(".")[-1],
                    "bounds": n.attrib.get("bounds", "")
                })
        print(json.dumps(nodes, indent=2))
    else:
        xml = d.dump_hierarchy(compressed=True)
        compressor = ContextCompressor()
        compressed = compressor.compress_xml(xml, screen=cur.get('activity', ''))
        print(json.dumps(compressed, indent=2))

if __name__ == "__main__":
    main()
