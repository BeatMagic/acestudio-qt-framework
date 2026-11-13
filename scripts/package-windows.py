#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Timedomain Inc.
# SPDX-License-Identifier: MIT
"""Package a scripts/build-windows.py result as the two archives ACE Studio fetches:

    qt-<version>-windows-msvc2022_64-<revision>.tar.xz       the libraries and tools
    qt-<version>-windows-msvc2022_64-<revision>-pdb.tar.xz   the PDBs

    python scripts/package-windows.py --qt 6.12.0 --revision 1 --work C:\\qtw

Each archive holds one top-level directory. The PDB archive mirrors the
prefix's layout, so each PDB unpacks beside the binary it belongs to. Archives
land in <work>/dist, and their SHA-256 sums are printed for the pin. Uses the
system `tar` (bsdtar) for multithreaded xz.
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--qt", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--work", required=True, type=Path)
    args = parser.parse_args()
    work = args.work.resolve()
    name = f"qt-{args.qt}-windows-msvc2022_64-{args.revision}"
    dist = work / "dist"
    dist.mkdir(parents=True, exist_ok=True)

    for tree, archive_dir, level in (("prefix", name, 6), ("pdb", f"{name}-pdb", 3)):
        staged = dist / archive_dir
        if staged.exists():
            shutil.rmtree(staged)
        (work / tree).rename(staged)
        archive = dist / f"{archive_dir}.tar.xz"
        subprocess.run(["tar", "--options", f"xz:compression-level={level},xz:threads=0",
                        "-cJf", archive.name, archive_dir], cwd=dist, check=True)
        staged.rename(work / tree)
        print(f"{sha256(archive)}  {archive.name}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
