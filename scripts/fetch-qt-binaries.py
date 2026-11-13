#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Timedomain Inc.
# SPDX-License-Identifier: MIT
"""Fetch the official Qt binaries for Windows and lay them out as a Qt prefix.

The archives come from Qt's online installer repository on download.qt.io, each
verified against the SHA-1 Qt publishes beside it: the modules ACE Studio
ships, built with MSVC 2022 for x86_64, in two trees.

    python3 scripts/fetch-qt-binaries.py --qt 6.12.0 --out work

    work/prefix   the libraries and tools, as the installer lays them out
    work/pdb      the debug symbols (PDBs), in the same layout

Unpacks the installer's .7z archives with `cmake -E tar`, so needs CMake on
PATH. Stdlib otherwise; honors HTTPS_PROXY.
"""

import argparse
import hashlib
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = "https://download.qt.io/online/qtsdkrepository/windows_x86/desktop"
ARCH = "win64_msvc2022_64"
# The base package carries qtbase, qtdeclarative, qtsvg, qttools and
# qttranslations; the add-ons ACE Studio ships have packages of their own.
ADDONS = ("qtshadertools", "qtimageformats", "qtwebsockets", "qtcanvaspainter")
# DLLs the base package unpacks at the prefix root; the installer moves them
# into bin, beside the Qt DLLs that load them.
ROOT_DLLS = ("d3dcompiler_47.dll", "opengl32sw.dll")


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "acestudio-qt-framework"})
    with urllib.request.urlopen(request, timeout=600) as response:
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--qt", required=True, help="Qt version, e.g. 6.12.0")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    tag = args.qt.replace(".", "")
    base = f"{REPO}/qt6_{tag}/qt6_{tag}_msvc2022_64"
    trees = {
        "prefix": [f"qt.qt6.{tag}.{ARCH}"] + [f"qt.qt6.{tag}.addons.{m}.{ARCH}" for m in ADDONS],
        "pdb": [f"qt.qt6.{tag}.debug_info.{ARCH}"]
        + [f"qt.qt6.{tag}.addons.{m}.debug_information.{ARCH}" for m in ADDONS],
    }
    root = ET.fromstring(fetch(f"{base}/Updates.xml"))
    updates = {p.findtext("Name"): p for p in root.findall("PackageUpdate")}
    downloads = args.out / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)

    for tree, packages in trees.items():
        dest = (args.out / tree).resolve()
        dest.mkdir(parents=True, exist_ok=True)
        for package in packages:
            update = updates[package]
            version = update.findtext("Version")
            for archive in [a.strip() for a in update.findtext("DownloadableArchives").split(",") if a.strip()]:
                if archive.startswith("qtdoc-"):
                    continue
                url = f"{base}/{package}/{version}{archive}"
                expected = fetch(url + ".sha1").decode().split()[0]
                data = fetch(url)
                if hashlib.sha1(data).hexdigest() != expected:
                    raise SystemExit(f"SHA-1 mismatch for {url}")
                path = downloads / archive
                path.write_bytes(data)
                subprocess.run(["cmake", "-E", "tar", "xf", str(path.resolve())], cwd=dest, check=True)
                path.unlink()
                print(f"ok   {tree}: {package} {archive}")

    prefix = args.out / "prefix"
    for dll in ROOT_DLLS:
        if (prefix / dll).exists():
            (prefix / dll).replace(prefix / "bin" / dll)
    return 0


if __name__ == "__main__":
    sys.exit(main())
