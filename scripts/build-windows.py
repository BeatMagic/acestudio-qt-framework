#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Timedomain Inc.
# SPDX-License-Identifier: MIT
"""Build the Windows Qt that ACE Studio ships: the official MSVC 2022 x86_64
binaries, with each patched module rebuilt from patched source and installed
over them.

    python scripts/build-windows.py --qt 6.12.0 --work C:\\qtw

Run it in an x64 MSVC developer environment (vcvars64) with CMake and Ninja on
PATH. Keep the work dir short: Qt's paths run deep. It ends with:

    <work>/prefix   the Qt, PDBs moved out
    <work>/pdb      every PDB, in the prefix's layout

The rebuild matches the official configuration, which qt-configure-module
inherits from the installed qtbase (debug-and-release as RelWithDebInfo and
Debug, debug info forced on); the generator is Ninja Multi-Config, as Qt's.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd, cwd=None):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], cwd=cwd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--qt", required=True, help="Qt version, e.g. 6.12.0")
    parser.add_argument("--work", required=True, type=Path)
    args = parser.parse_args()
    work = args.work.resolve()
    prefix, pdb = work / "prefix", work / "pdb"

    if not (prefix / "bin").exists():
        run([sys.executable, "-I", ROOT / "scripts" / "fetch-qt-binaries.py", "--qt", args.qt, "--out", work])

    modules = sorted(p.name for p in (ROOT / "qt" / args.qt / "patches").iterdir()
                     if p.is_dir() and p.name != "qtbase")
    run([sys.executable, "-I", ROOT / "scripts" / "prepare-sources.py", "--qt", args.qt,
         "--out", work / "src", *modules])

    for module in modules:
        build = work / "build" / module
        build.mkdir(parents=True, exist_ok=True)
        run([prefix / "bin" / "qt-configure-module.bat", work / "src" / module, "--",
             "-G", "Ninja Multi-Config", "-DQT_BUILD_TESTS=OFF", "-DQT_BUILD_EXAMPLES=OFF",
             "-DFEATURE_clangcpp=OFF"], cwd=build)
        run(["cmake", "--build", "."], cwd=build)
        for config in ("RelWithDebInfo", "Debug"):
            run(["cmake", "--install", ".", "--config", config], cwd=build)

    # The rebuilt PDBs replace the official ones in the symbols tree.
    moved = 0
    for path in prefix.rglob("*.pdb"):
        dest = pdb / path.relative_to(prefix)
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.replace(path, dest)
        moved += 1
    print(f"moved {moved} PDBs from the prefix into {pdb}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
