#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 The acestudio-qt-framework contributors
# SPDX-License-Identifier: MIT
"""Fetch the official Qt source archives, verify them, and apply our patches.

The sources a build uses are the official release archives from download.qt.io,
pinned by the SHA-256 sums in qt/<version>/SHA256SUMS (copied from the .sha256
files Qt publishes beside each archive), plus the patch series in
qt/<version>/patches/<module>/. Nothing else goes into a build.

    python3 scripts/prepare-sources.py --qt 6.12.0 --out src qtbase qtdeclarative
    python3 scripts/prepare-sources.py --qt 6.12.0 --out src --all

Each module lands in <out>/<module> with its patches applied. A module already
there is left alone, so delete <out> to start over. Stdlib only; honors
HTTPS_PROXY. Needs `git` on PATH (for `git apply`).
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MIRROR = "https://download.qt.io/official_releases/qt"


def read_sums(version: str) -> dict:
    sums = {}
    for line in (ROOT / "qt" / version / "SHA256SUMS").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            sha, name = line.split()
            sums[name] = sha
    return sums


def archive_name(module: str, version: str) -> str:
    return f"{module}-everywhere-src-{version}.tar.xz"


def download(url: str, dest: Path) -> str:
    digest = hashlib.sha256()
    request = urllib.request.Request(url, headers={"User-Agent": "acestudio-qt-framework"})
    with urllib.request.urlopen(request, timeout=300) as response, open(dest, "wb") as out:
        while chunk := response.read(1 << 20):
            digest.update(chunk)
            out.write(chunk)
    return digest.hexdigest()


def prepare(module: str, version: str, sums: dict, out: Path, mirror: str) -> None:
    dest = out / module
    if dest.exists():
        print(f"have  {module}: {dest}")
        return
    name = archive_name(module, version)
    if name not in sums:
        raise SystemExit(f"{name} is not pinned in qt/{version}/SHA256SUMS")
    minor = ".".join(version.split(".")[:2])
    url = f"{mirror}/{minor}/{version}/submodules/{name}"
    with tempfile.TemporaryDirectory(dir=out, prefix=".prepare-") as work:
        archive = Path(work) / name
        print(f"fetch {url}")
        actual = download(url, archive)
        if actual != sums[name]:
            raise SystemExit(f"SHA-256 mismatch for {name}: got {actual}, pinned {sums[name]}")
        with tarfile.open(archive, mode="r:xz") as tf:
            tf.extractall(work, filter="tar") if sys.version_info >= (3, 12) else tf.extractall(work)
        tree = Path(work) / name.removesuffix(".tar.xz")
        for patch in sorted((ROOT / "qt" / version / "patches" / module).glob("*.patch")):
            print(f"patch {module}: {patch.name}")
            subprocess.run(["git", "apply", "--whitespace=nowarn", str(patch)], cwd=tree, check=True)
        shutil.move(str(tree), dest)
    print(f"ready {module}: {dest}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--qt", required=True, help="Qt version, e.g. 6.12.0")
    parser.add_argument("--out", required=True, type=Path, help="Directory the modules land in.")
    parser.add_argument("--all", action="store_true", help="Every module pinned for this version.")
    parser.add_argument("--mirror", default=os.environ.get("QT_SOURCE_MIRROR", DEFAULT_MIRROR),
                        help="Base of the official_releases/qt tree (env QT_SOURCE_MIRROR).")
    parser.add_argument("modules", nargs="*")
    args = parser.parse_args()

    sums = read_sums(args.qt)
    suffix = f"-everywhere-src-{args.qt}.tar.xz"
    modules = sorted(n.removesuffix(suffix) for n in sums) if args.all else args.modules
    if not modules:
        parser.error("name the modules, or pass --all")
    args.out.mkdir(parents=True, exist_ok=True)
    for module in modules:
        prepare(module, args.qt, sums, args.out, args.mirror.rstrip("/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
