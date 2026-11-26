"""Build a BEE2 package/item index from the info.txt files of a local source checkout."""
import argparse
from collections import Counter
import json
from pathlib import Path

from srctools import Keyvalues

DICTIONARIES = Path(__file__).resolve().parent / "dictionaries"


def build(packages_dir, components):
    # editoritems.txt can itself be replaced by BEE2. Require a stock reference.
    native_items = components["editor_items"]
    if not native_items or any(item["native"] is not True for item in native_items.values()):
        raise ValueError("Supply components.json generated from a clean stock editoritems reference.")
    packages = {}
    items = {}
    for manifest in sorted(packages_dir.rglob("info.txt")):
        source = manifest.relative_to(packages_dir).as_posix()
        tree = Keyvalues.parse(manifest.read_text(encoding="utf-8-sig"), source)
        package = tree["ID"]
        if package in packages:
            raise ValueError(f"Duplicate package ID {package}: {source}")
        packages[package] = {
            "name": tree["Name", package], "manifest": source,
            "requires": [node.value for node in tree.find_children("Prerequisites") if node.name == "package"],
            "declared_objects": dict(Counter(node.real_name for node in tree
                                             if node.has_children() and node.name not in {"desc", "prerequisites", "overrides"})),
        }
        for parent in [tree, *tree.find_all("Overrides")]:
            for item in parent.find_all("Item"):
                name = item["ID"].upper()
                entry = items.setdefault(name, {
                    "origin": "extend", "native": False,
                    "native_editor_item": name if name in native_items else None,
                    "declarations": [],
                })
                versions = []
                for version in item.find_all("Version"):
                    versions.append({
                        "id": version["ID", None],
                        "styles": [style.real_name for style in version.find_children("Styles")],
                    })
                entry["declarations"].append({
                    "package": package, "kind": "item" if parent is tree else "override",
                    "versions": versions,
                })
    if not packages or not items:
        raise ValueError("No BEE2 package items found in this checkout.")
    return {"packages": packages, "items": items}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packages", type=Path, help="BEE2-items/packages source directory")
    parser.add_argument("--revision", required=True, help="Source checkout commit")
    parser.add_argument("--components", type=Path, default=DICTIONARIES / "components.json")
    parser.add_argument("--output", type=Path, default=DICTIONARIES / "bee2.json")
    args = parser.parse_args()
    data = build(args.packages, json.loads(args.components.read_text(encoding="utf8")))
    data["upstream"] = {"repository": "https://github.com/BEEmod/BEE2-items", "revision": args.revision}
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf8")
