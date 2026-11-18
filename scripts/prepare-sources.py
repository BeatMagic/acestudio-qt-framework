#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Timedomain Inc.
# SPDX-License-Identifier: MIT
"""Fetch the official Qt source archives, verify them, and apply our patches.

The sources a build uses are the official release archives from download.qt.io,
pinned by the SHA-256 sums in qt/<version>/SHA256SUMS (copied from the .sha256
files Qt publishes beside each archive), plus the patch series in
qt/<version>/patches/<module>/. Nothing else goes into a build.

Qt WebEngine is released apart from Qt, with its own version: its archive is
pinned in qtwebengine/<version>/SHA256SUMS and its patches are in
qtwebengine/<version>/patches/.

    python3 scripts/prepare-sources.py --qt 6.12.0 --out src qtbase qtdeclarative
    python3 scripts/prepare-sources.py --qt 6.12.0 --out src --all
    python3 scripts/prepare-sources.py --qt 6.12.0 --out src qtwebchannel --qtwebengine 6.140.0

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
WEBENGINE_MIRROR = "https://download.qt.io/official_releases/qtwebengine"


def read_sums(pins: Path) -> dict:
    sums = {}
    for line in (pins / "SHA256SUMS").read_text().splitlines():
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


def prepare(module: str, version: str, pins: Path, patches: Path, url_dir: str, out: Path) -> None:
    """Fetch <module>-everywhere-src-<version> from url_dir, check it against the sum
    pinned in pins/SHA256SUMS, and apply patches/*.patch to it."""
    dest = out / module
    if dest.exists():
        print(f"have  {module}: {dest}")
        return
    name = archive_name(module, version)
    sums = read_sums(pins)
    if name not in sums:
        raise SystemExit(f"{name} is not pinned in {pins.relative_to(ROOT)}/SHA256SUMS")
    url = f"{url_dir}/{name}"
    with tempfile.TemporaryDirectory(dir=out, prefix=".prepare-") as work:
        archive = Path(work) / name
        print(f"fetch {url}")
        actual = download(url, archive)
        if actual != sums[name]:
            raise SystemExit(f"SHA-256 mismatch for {name}: got {actual}, pinned {sums[name]}")
        with tarfile.open(archive, mode="r:xz") as tf:
            tf.extractall(work, filter="tar") if sys.version_info >= (3, 12) else tf.extractall(work)
        tree = Path(work) / name.removesuffix(".tar.xz")
        for patch in sorted(patches.glob("*.patch")):
            print(f"patch {module}: {patch.name}")
            subprocess.run(["git", "apply", "--whitespace=nowarn", str(patch)], cwd=tree, check=True)
        shutil.move(str(tree), dest)
    print(f"ready {module}: {dest}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--qt", help="Qt version, e.g. 6.12.0; needed for Qt's own modules.")
    parser.add_argument("--out", required=True, type=Path, help="Directory the modules land in.")
    parser.add_argument("--all", action="store_true", help="Every module pinned for this version.")
    parser.add_argument("--mirror", default=os.environ.get("QT_SOURCE_MIRROR", DEFAULT_MIRROR),
                        help="Base of the official_releases/qt tree (env QT_SOURCE_MIRROR).")
    parser.add_argument("--qtwebengine", metavar="VERSION",
                        help="Also Qt WebEngine at this version, e.g. 6.140.0.")
    parser.add_argument("--webengine-mirror",
                        default=os.environ.get("QTWEBENGINE_SOURCE_MIRROR", WEBENGINE_MIRROR),
                        help="Base of the official_releases/qtwebengine tree (env QTWEBENGINE_SOURCE_MIRROR).")
    parser.add_argument("modules", nargs="*")
    args = parser.parse_args()

    if (args.all or args.modules) and not args.qt:
        parser.error("Qt's modules need --qt")
    if not (args.all or args.modules or args.qtwebengine):
        parser.error("name the modules, or pass --all or --qtwebengine")
    args.out.mkdir(parents=True, exist_ok=True)
    if args.qt:
        pins = ROOT / "qt" / args.qt
        suffix = f"-everywhere-src-{args.qt}.tar.xz"
        modules = sorted(n.removesuffix(suffix) for n in read_sums(pins)) if args.all else args.modules
        minor = ".".join(args.qt.split(".")[:2])
        url_dir = f"{args.mirror.rstrip('/')}/{minor}/{args.qt}/submodules"
        for module in modules:
            prepare(module, args.qt, pins, pins / "patches" / module, url_dir, args.out)
    if args.qtwebengine:
        v = args.qtwebengine
        webengine = ROOT / "qtwebengine" / v
        minor = ".".join(v.split(".")[:2])
        url_dir = f"{args.webengine_mirror.rstrip('/')}/{minor}/{v}/src"
        prepare("qtwebengine", v, webengine, webengine / "patches", url_dir, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
