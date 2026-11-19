#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Timedomain Inc.
# SPDX-License-Identifier: MIT
"""Package what scripts/build-webengine-windows.py installed as two archives
that unpack over the Qt archive of the same Qt version:

    qtwebengine-<version>-qt<qt version>-windows-msvc2022_64-<revision>.tar.xz
    qtwebengine-<version>-qt<qt version>-windows-msvc2022_64-<revision>-pdb.tar.xz

    python scripts/package-webengine-windows.py --qt 6.12.0 --webengine 6.140.0 --revision 1 --work C:\\qtw

The files are those the qtwebchannel and qtwebengine builds installed, every
configuration (their install_manifest-<config>.txt), laid out as in the Qt
prefix under one top-level directory; the PDBs go to the -pdb archive the same
way, as in scripts/package-windows.py. Archives land in <work>/dist, and their
SHA-256 sums are printed for the pin. Uses tar and 7-Zip, as package-windows.py.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from importlib import import_module  # noqa: E402

sha256 = import_module("package-windows").sha256

DEBUG_CRT = {"vcruntime140d.dll", "ucrtbased.dll", "msvcp140d.dll"}


def check_qt_imports(stage: Path, bin_dir: Path) -> None:
    """Fail when a debug binary imports a release Qt DLL, or a release binary a debug
    one: the process would load two Qts. A binary is debug when it imports the debug
    CRT; a Qt import is debug when it is Qt6<x>d.dll and Qt6<x>.dll exists too."""
    if not shutil.which("dumpbin"):
        raise SystemExit("dumpbin is not on PATH; run in an x64 MSVC developer environment")
    names = {p.name.lower() for p in bin_dir.glob("Qt6*.dll")}
    bad = []
    for path in sorted(p for p in stage.rglob("*") if p.suffix.lower() in (".dll", ".exe")):
        out = subprocess.run(["dumpbin", "/nologo", "/dependents", str(path)],
                             capture_output=True, text=True, check=True).stdout
        imports = [w.lower() for w in out.split() if w.lower().endswith(".dll")]
        debug = bool(DEBUG_CRT & set(imports))
        for dll in imports:
            if not dll.startswith("qt6"):
                continue
            dll_debug = dll.endswith("d.dll") and dll[:-5] + ".dll" in names
            if dll_debug != debug:
                bad.append(f"{path.relative_to(stage)} ({'debug' if debug else 'release'}) imports {dll}")
    if bad:
        raise SystemExit("mixed debug and release Qt imports:\n  " + "\n  ".join(bad))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--qt", required=True)
    parser.add_argument("--webengine", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--work", required=True, type=Path)
    args = parser.parse_args()
    work = args.work.resolve()
    prefix = (work / "prefix").resolve()
    name = f"qtwebengine-{args.webengine}-qt{args.qt}-windows-msvc2022_64-{args.revision}"

    files = set()
    for module in ("qtwebchannel", "qtwebengine"):
        for config in ("RelWithDebInfo", "Debug"):
            manifest = work / "build" / module / f"install_manifest-{config}.txt"
            if not manifest.is_file():
                raise SystemExit(f"{manifest} is missing; run build-webengine-windows.py to the end")
            for line in manifest.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                # CMake writes the paths without a drive letter; they are on the prefix's.
                path = Path(line.strip())
                if not path.drive:
                    path = Path(prefix.drive + str(path))
                if not path.is_file():
                    raise SystemExit(f"{manifest} lists {path}, which is missing")
                files.add(path.resolve().relative_to(prefix))

    dist = work / "dist"
    stage = dist / "stage"
    if stage.exists():
        shutil.rmtree(stage)
    for rel in sorted(files):
        out, top = rel, name
        if rel.suffix.lower() == ".pdb":
            top = f"{name}-pdb"
            # Qt installs an executable's PDB for every configuration but the first
            # into bin/<config>/, where a debugger doesn't look; ours carry a d suffix,
            # so the PDB goes beside its executable.
            beside = rel.parent.parent / rel.name
            if (rel.parent.name in ("RelWithDebInfo", "Debug")
                    and (prefix / beside.with_suffix(".exe")).is_file()):
                if beside in files:
                    raise SystemExit(f"{rel} and {beside} would collide")
                out = beside
        dest = stage / top / out
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(prefix / rel, dest)

    check_qt_imports(stage / name, prefix / "bin")

    for archive_dir, level in ((name, 6), (f"{name}-pdb", 3)):
        archive = dist / f"{archive_dir}.tar.xz"
        plain = dist / f"{archive_dir}.tar"
        archive.unlink(missing_ok=True)
        subprocess.run(["tar", "-cf", str(plain), archive_dir], cwd=stage, check=True)
        subprocess.run(["7z", "a", "-txz", f"-mx={level}", "-mmt=on", "-bd",
                        archive.name, plain.name], cwd=dist, check=True)
        plain.unlink()
        print(f"{sha256(archive)}  {archive.name}", flush=True)
    shutil.rmtree(stage)
    return 0


if __name__ == "__main__":
    sys.exit(main())
