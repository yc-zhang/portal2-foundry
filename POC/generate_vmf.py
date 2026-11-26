"""Build a Portal 2 VMF from a JSON chamber description."""
import argparse
import json
from pathlib import Path

from srctools import Vec
from srctools.vmf import Output, VMF


# These defaults are part of our component library, independent of each level.
TYPES = {
    "spawn": ("info_player_start", {"angles": "0 0 0"}),
    "light": ("light", {"_quadratic_attn": "1", "_linear_attn": "0", "_constant_attn": "0"}),
    "cube": ("prop_weighted_cube", {"model": "models/props/metal_box.mdl", "CubeType": "0", "NewSkins": "1", "PaintPower": "4"}),
    "companion_cube": ("prop_weighted_cube", {"model": "models/props/metal_box.mdl", "CubeType": "1", "NewSkins": "1", "skin": "1", "PaintPower": "4"}),
    "portal_gun": ("weapon_portalgun", {"CanFirePortal1": "1", "CanFirePortal2": "1"}),
    "floor_button": ("prop_floor_button", {"model": "models/props/portal_button.mdl"}),
    "lift_door": ("func_door", {"movedir": "-90 0 0", "speed": "160", "wait": "-1", "lip": "0"}),
    "finish_zone": ("trigger_once", {"spawnflags": "1"}),
    "workshop_finish": ("func_instance", {"file": "instances/p2editor/global_pti_ents.vmf"}),
}
OUTPUTS = {("floor_button", "pressed"): "OnPressed", ("floor_button", "released"): "OnUnPressed",
           ("finish_zone", "entered"): "OnStartTouch"}
INPUTS = {("lift_door", "open"): "Open", ("lift_door", "close"): "Close",
          ("workshop_finish", "finish"): "Trigger"}


def position(coords):
    if len(coords) != 3 or not all(type(n) is int for n in coords):
        raise ValueError(f"Expected three integer Hammer coordinates: {coords}")
    return Vec(*coords)


def prism(vmf, spec, material):
    lo, hi = position(spec["min"]), position(spec["max"])
    if any(a >= b for a, b in zip(lo, hi)):
        raise ValueError(f"Empty or inverted brush: {spec}")
    return vmf.make_prism(lo, hi, mat=material).solid


def generate(spec):
    vmf = VMF()
    vmf.spawn["skyname"] = "sky_black_nofog"
    materials = spec["materials"]
    for box in spec["world"]:
        vmf.add_brush(prism(vmf, box, materials[box["material"]]))

    components = {}
    finish_instance = None
    for item in spec["components"]:
        name, kind = item["id"], item["type"]
        if not name.isidentifier() or name.casefold() in components:
            raise ValueError(f"Invalid or duplicate component ID: {name}")
        classname, defaults = TYPES[kind]
        entity = vmf.create_ent(classname, targetname=name, **defaults)
        if kind == "finish_zone":
            entity.solids.append(prism(vmf, item, "tools/toolstrigger"))
        elif kind == "lift_door":
            entity.solids.append(prism(vmf, item, materials[item["material"]]))
        else:
            entity["origin"] = position(item["at"])
        if kind == "light":
            entity["_light"] = item["light"]
        if kind == "workshop_finish":
            if finish_instance is not None:
                raise ValueError("Only one global PTI instance can own the finish relay.")
            finish_instance = entity
            entity.fixup["$disable_pti_audio"] = "1"
        components[name.casefold()] = kind, entity

    for wire in spec["connections"]:
        source_id, output_port = wire["from"].split(".")
        target_id, input_port = wire["to"].split(".")
        source_kind, source = components[source_id.casefold()]
        target_kind, target = components[target_id.casefold()]
        output = OUTPUTS[source_kind, output_port]
        input_name = INPUTS[target_kind, input_port]
        # The PTI instance exposes a global relay when VBSP expands it.
        target_name = "@relay_pti_level_end" if target_kind == "workshop_finish" else target["targetname"]
        source.add_out(Output(output, target_name, input_name, only_once=wire.get("once", False)))
    return vmf


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("description", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.suffix.lower() != ".vmf":
        parser.error("Output must be a .vmf file.")
    try:
        level = generate(json.loads(args.description.read_text(encoding="utf-8")))
    except (KeyError, TypeError, ValueError) as exc:
        parser.exit(1, f"Invalid chamber description: {exc}\n")
    with args.output.open("w", encoding="utf-8") as stream:
        level.export(stream)
