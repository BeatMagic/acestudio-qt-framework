#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 The acestudio-qt-framework contributors
# SPDX-License-Identifier: MIT
"""Package the official Qt documentation (.qch) as one archive ACE Studio fetches.

The .qch files come from the documentation packages of Qt's online installer
repository on download.qt.io, each verified against the SHA-1 Qt publishes
beside it. They are unmodified: our patches change no API. The archive holds
one top-level directory with the files under doc/, the place Qt's own prefix
keeps them (QLibraryInfo::DocumentationPath), so they unpack into the prefix.

    python3 -I scripts/package-docs.py --qt 6.12.0 --out dist

Writes <out>/qt-<version>-docs.tar.xz and prints its SHA-256. Stdlib only;
honors HTTPS_PROXY.
"""

import argparse
import hashlib
import io
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = "https://download.qt.io/online/qtsdkrepository/all_os/qt"
# The base documentation package covers qtbase, qtdeclarative, qtsvg, qttools and
# the other essentials; add-on modules ACE Studio ships have packages of their own.
ADDONS = ("qtshadertools", "qtimageformats", "qtwebsockets")
# Qt's copy of the documentation license, at the release tag.
GFDL_URL = "https://raw.githubusercontent.com/qt/qtbase/v{version}/LICENSES"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "acestudio-qt-framework"})
    with urllib.request.urlopen(request, timeout=300) as response:
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--qt", required=True, help="Qt version, e.g. 6.12.0")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    tag = args.qt.replace(".", "")
    base = f"{REPO}/qt6_{tag}_unix_line_endings_src"
    packages = [f"qt.qt6.{tag}.doc"] + [f"qt.qt6.{tag}.doc.{m}" for m in ADDONS]
    root = ET.fromstring(fetch(f"{base}/Updates.xml"))
    updates = {p.findtext("Name"): p for p in root.findall("PackageUpdate")}

    name = f"qt-{args.qt}-docs"
    args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        doc = Path(work) / name / "doc"
        doc.mkdir(parents=True)
        for package in packages:
            update = updates[package]
            version = update.findtext("Version")
            archives = [a.strip() for a in update.findtext("DownloadableArchives").split(",") if a.strip()]
            for archive in archives:
                url = f"{base}/{package}/{version}{archive}"
                expected = fetch(url + ".sha1").decode().split()[0]
                data = fetch(url)
                if hashlib.sha1(data).hexdigest() != expected:
                    raise SystemExit(f"SHA-1 mismatch for {url}")
                with tarfile.open(fileobj=io.BytesIO(data), mode="r:xz") as tf:
                    for member in tf.getmembers():
                        if member.isfile() and member.name.endswith(".qch"):
                            with tf.extractfile(member) as src, open(doc / Path(member.name).name, "wb") as dst:
                                shutil.copyfileobj(src, dst)
                print(f"ok   {package} {archive}")
        # The documentation's license travels with it.
        gfdl = "GFDL-1.3-no-invariants-only.txt"
        (Path(work) / name / "LICENSES").mkdir()
        (Path(work) / name / "LICENSES" / gfdl).write_bytes(fetch(GFDL_URL.format(version=args.qt) + "/" + gfdl))
        out = args.out / f"{name}.tar.xz"
        with tarfile.open(out, "w:xz", preset=6) as tf:
            tf.add(Path(work) / name, arcname=name, )
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"{digest}  {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
