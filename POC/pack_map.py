"""Resolve runtime dependencies of a compiled Portal 2 BSP before installation."""
import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import subprocess
import tempfile

from srctools.bsp import BSP
from srctools.filesys import RawFileSystem, VPKFileSystem, ZipFileSystem
from srctools.game import Game
from srctools.packlist import PackList


def pack_map(bsp_path, game_dir, assets):
    bsp = BSP(bsp_path)
    embedded = ZipFileSystem(bsp_path, bsp.pakfile)
    fs = Game(game_dir).get_filesystem()
    fs.add_sys(embedded, priority=True)
    pack = PackList(fs)
    if assets.is_dir():
        fs.add_sys(RawFileSystem(assets), priority=True)
    pack.load_soundscript_manifest()
    pack.load_particle_manifest()
    pack.pack_from_bsp(bsp)
    pack.pack_from_ents(bsp.ents, bsp_path.stem, tags=["P2"])
    if assets.is_dir():
        for file in sorted(assets.rglob("*")):
            if file.is_file():
                pack.pack_file(file.relative_to(assets).as_posix(), source="explicit map asset")
    pack.eval_dependencies()

    # Only stock depot archives are supplied by the target installation.
    # A mounted third-party VPK can contain dependencies we must ship.
    stock = {game_dir.parent / folder / "pak01_dir.vpk"
             for folder in ("portal2", "portal2_dlc1", "portal2_dlc2", "update", "platform")}
    report = {}
    expected = {entry.filename: hashlib.sha256(bsp.pakfile.read(entry)).hexdigest()
                for entry in bsp.pakfile.infolist()}
    missing = []
    with tempfile.TemporaryDirectory(dir=bsp_path.parent) as temp:
        stage = Path(temp)
        lines = []
        for item in sorted(pack, key=lambda item: item.filename):
            name = item.filename
            status = report[name] = {"from": item.source}
            if item.data is None:
                try:
                    file = fs[name]
                except FileNotFoundError:
                    status["resolution"] = "optional-missing" if item.optional else "missing"
                    if not item.optional:
                        missing.append(f"{name} (from {item.source})")
                    continue
                system = fs.get_system(file)
                if system is embedded:
                    status["resolution"] = "already-packed"
                    continue
                if isinstance(system, VPKFileSystem) and Path(system.path) in stock:
                    status["resolution"] = "stock"
                    continue
                with file.open_bin() as stream:
                    data = stream.read()
            else:
                data = item.data
            status["resolution"] = "pack"
            staged = stage / str(len(lines))
            staged.write_bytes(data)
            lines.extend([name, str(staged)])
            expected[name] = hashlib.sha256(data).hexdigest()

        report_path = bsp_path.with_suffix(".dependencies.json")
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf8")
        print(f"Dependency report: {report_path}", flush=True)
        if missing:
            raise ValueError("Missing required files:\n" + "\n".join(missing))
        if lines:
            listing = stage / "packlist.txt"
            listing.write_text("\n".join(lines) + "\n", encoding="utf8")
            output = stage / bsp_path.name
            subprocess.run([str(game_dir.parent / "bin/bspzip.exe"), "-addorupdatelist",
                            str(bsp_path), str(listing), str(output)],
                           env={**os.environ, "VPROJECT": str(game_dir)}, check=True)
        else:
            output = bsp_path
        archive = BSP(output).pakfile
        contents = {entry.filename.casefold(): hashlib.sha256(archive.read(entry)).hexdigest()
                    for entry in archive.infolist()}
        for name, digest in expected.items():
            if contents.get(name.casefold()) != digest:
                raise ValueError(f"BSP packing verification failed: {name}")
        if output != bsp_path:
            output.replace(bsp_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bsp", type=Path)
    parser.add_argument("game", type=Path)
    parser.add_argument("assets", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    pack_map(args.bsp.resolve(), args.game.resolve(), args.assets.resolve())
