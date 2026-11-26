"""Index the installed Portal 2 map-authoring resources. Run from any directory."""
import argparse
from collections import Counter, defaultdict
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

from srctools import Keyvalues
from srctools.vpk import VPK

from generate_vmf import INPUTS, OUTPUTS, TYPES
from vmf_sections import SECTIONS

HERE = Path(__file__).resolve().parent


class Provenance:
    """Compare definitions against a versioned Steam depot inventory."""

    def __init__(self, root):
        self.root = root
        self.baseline = json.loads((HERE / "stock-resource-hashes.json").read_text())

    @lru_cache(maxsize=None)
    def source(self, path):
        expected = self.baseline["files"].get(path.lower())
        if expected is None:
            return "extend"
        digest = hashlib.sha1((self.root / path).read_bytes()).hexdigest()
        return "native" if digest == expected else "unverified"

    def classify(self, paths):
        sources = {path: self.source(path) for path in paths}
        origins = set(sources.values())
        if not sources:
            return {"native": None, "origin": "unverified", "sources": {}}
        origin = next(iter(origins)) if len(origins) == 1 else "mixed"
        return {"native": {"native": True, "extend": False}.get(origin),
                "origin": origin, "sources": sources}


def materials(root):
    found = defaultdict(list)
    folders = ["portal2", "update", "platform"]
    folders += sorted(p.name for p in root.glob("portal2_dlc*") if re.fullmatch(r"portal2_dlc\d+", p.name))
    for folder in folders:
        directory = root / folder
        for archive in sorted(directory.glob("*_dir.vpk")):
            for name in VPK(archive).filenames(ext="vmt"):
                name = name.lower().replace("\\", "/")
                if name.startswith("materials/"):
                    found[name[10:-4]].append(archive.relative_to(root).as_posix())
        for file in sorted((directory / "materials").rglob("*.vmt")):
            name = file.relative_to(directory / "materials").with_suffix("").as_posix().lower()
            found[name].append(file.relative_to(root).as_posix())
    return found


def fgd_catalogs(root, provenance):
    # Index class headers only. Some shipped FGD property descriptions contain
    # dangling '+' tokens, which prevent parsing the entire file with srctools.
    entities = defaultdict(list)
    io_classes = defaultdict(list)
    visited = set()

    def visit(file):
        if file in visited:
            return
        visited.add(file)
        source = file.relative_to(root).as_posix()
        content = file.read_text(encoding="cp1252")
        for match in re.finditer(r'(?im)^\s*@include\s+"([^"]+)"', content):
            visit(file.parent / match[1])
        for block in re.split(r"(?m)^\s*(?=@)", content):
            kind = re.match(r"@(\w+Class)\b", block, re.I)
            if not kind:
                continue
            block = re.sub(r"//[^\n]*", "", block)
            header = re.search(r"=\s*([\w]+)", block)
            if not header:
                raise ValueError(f"Missing classname in {source}: {block[:100]}")
            definition = {"kind": kind[1], "source": source}
            if kind[1].lower() not in {"baseclass", "extendclass"}:
                entities[header[1]].append(definition)
            base = re.search(r"\bbase\s*\(([^)]*)\)", block[:header.start()], re.I)
            entry = {**definition, **provenance.classify([source]),
                     "bases": [s.strip() for s in base[1].split(",") if s.strip()] if base else [],
                     "inputs": {}, "outputs": {}}
            for direction, name, param in re.findall(
                r"^\s*(input|output)\s+(\w+)\s*\(\s*(\w+)\s*\)", block, re.I | re.M
            ):
                entry[direction.lower() + "s"][name] = param
            io_classes[header[1]].append(entry)
    visit(root / "bin/portal2.fgd")
    return entities, io_classes


def editor_items(root):
    file = root / "portal2_dlc2/scripts/editoritems.txt"
    tree = Keyvalues.parse(file.read_text(encoding="utf-8-sig"), allow_escapes=False)
    items = {}
    for item in tree.find_children("ItemData"):
        if item.name != "item":
            continue
        refs = [node.value.replace("\\", "/") for node in item.iter_tree()
                if not node.has_children() and node.value.lower().endswith(".vmf")]
        items[item["Type"]] = {"item_class": item["ItemClass", ""], "instances": sorted(set(refs))}
    return items


def component_catalog(root, prov, entities):
    maps = root / "sdk_content/maps"
    instances = sorted(p.relative_to(maps).as_posix() for p in (maps / "instances").rglob("*.vmf"))
    poc_types = {}
    for kind, (classname, defaults) in TYPES.items():
        poc_types[kind] = {
            "classname": classname, "defaults": defaults,
            "inputs": {port: value for (typ, port), value in INPUTS.items() if typ == kind},
            "outputs": {port: value for (typ, port), value in OUTPUTS.items() if typ == kind},
        }
    editor_source = "portal2_dlc2/scripts/editoritems.txt"
    instances = {path: prov.classify(["sdk_content/maps/" + path]) for path in instances}
    items = {}
    for name, item in editor_items(root).items():
        sources = [editor_source] + ["sdk_content/maps/" + s for s in item["instances"]
                                      if (root / "sdk_content/maps" / s).is_file()]
        items[name] = {**prov.classify(sources), **item}
        items[name]["missing_instances"] = [s for s in item["instances"] if s not in instances]
        if items[name]["missing_instances"]:
            items[name].update(native=None, origin="unverified")

    # These specific recipes use stock behaviour and assets; future recipes need review.
    reviewed = {"spawn", "light", "cube", "companion_cube", "portal_gun", "floor_button",
                "lift_door", "finish_zone", "workshop_finish"}
    recipes = {}
    for name, recipe in poc_types.items():
        paths = [d["source"] for d in entities.get(recipe["classname"], [])]
        if "file" in recipe["defaults"]:
            paths.append("sdk_content/maps/" + recipe["defaults"]["file"])
        if "model" in recipe["defaults"]:
            model = recipe["defaults"]["model"]
            archive = root / "portal2/pak01_dir.vpk"
            if model in VPK(archive):
                paths.append(archive.relative_to(root).as_posix())
            else:
                paths = []
        entry = {**prov.classify([p for p in paths if (root / p).is_file()]), **recipe}
        if name not in reviewed or not paths or any(not (root / p).is_file() for p in paths):
            entry.update(native=None, origin="unverified")
        recipes[name] = entry
    return {
        "reference_depots": prov.baseline["depots"],
        "chamber_types": recipes, "editor_items": items, "instances": instances,
        "hammer_entities": {k: {**prov.classify([d["source"] for d in defs]), "definitions": defs}
                           for k, defs in entities.items()},
    }


def section_catalogs():
    catalogs = {name: {"section": name, **spec, "examples": {}} for name, spec in SECTIONS.items()}
    for filename in ("foundry_srctools.vmf", "foundry_button.vmf"):
        tree = Keyvalues.parse((HERE / filename).read_text(encoding="utf8"), allow_escapes=False)
        for section, catalog in catalogs.items():
            blocks = list(tree.find_all(section))
            example = {"count": len(blocks)}
            if section == "entity":
                example["classnames"] = dict(Counter(block["classname"] for block in blocks))
            elif len(blocks) == 1:
                example["values"] = {child.real_name: child.value for child in blocks[0] if not child.has_children()}
                example["child_counts"] = dict(Counter(child.name for child in blocks[0] if child.has_children()))
            catalog["examples"][filename] = example
    return catalogs


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf8")


def export_catalogs(root, directory, material_path):
    prov = Provenance(root)
    chamber = json.loads((HERE / "chamber.json").read_text(encoding="utf8"))
    entries = {name: prov.classify(paths) for name, paths in materials(root).items()}
    write_json(material_path, {"materials": entries, "material_aliases": chamber["materials"]})
    listing = ["# material | origin | sources (relative to Portal 2)"]
    for name, entry in sorted(entries.items()):
        listing.append(f"{name} | {entry['origin']} | {', '.join(entry['sources'])}")
    (directory / "materials.txt").write_text("\n".join(listing) + "\n", encoding="utf8")

    entities, ports = fgd_catalogs(root, prov)
    components = component_catalog(root, prov, entities)
    write_json(directory / "components.json", components)
    endpoints = {name: {k: recipe[k] for k in ("classname", "inputs", "outputs", "native", "origin")}
                 for name, recipe in components["chamber_types"].items() if recipe["inputs"] or recipe["outputs"]}
    write_json(directory / "connections.json", {
        "location": "entity.connections",
        "chamber_fields": {"from": "组件 ID.输出端口", "to": "组件 ID.输入端口", "once": "可选布尔值，默认 false"},
        "vmf_output_value": ["target", "input", "parameter", "delay_seconds", "max_fires"],
        "defaults": {"parameter": "", "delay_seconds": 0, "max_fires": -1, "max_fires_if_once": 1},
        "instance_targets": {"workshop_finish.finish": "@relay_pti_level_end"},
        "chamber_ports": endpoints, "examples": chamber["connections"], "fgd_declarations": ports,
    })
    for section, data in section_catalogs().items():
        write_json(directory / "vmf" / (section + ".json"), data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game_root", type=Path, help="Steam common/Portal 2 directory")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--output-dir", type=Path, default=HERE / "dictionaries")
    group.add_argument("--output", type=Path, help="Custom materials JSON path; sibling dictionaries share its directory.")
    args = parser.parse_args()
    material_path = args.output or args.output_dir / "materials.json"
    export_catalogs(args.game_root, material_path.parent, material_path)
