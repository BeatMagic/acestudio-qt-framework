#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Timedomain Inc.
# SPDX-License-Identifier: MIT
"""Build Qt WebEngine, with Qt WebChannel, for the Windows Qt that
scripts/build-windows.py built. Same configuration as that Qt, plus the
proprietary codecs (Chromium's FFmpeg with H.264 and AAC); Qt PDF and the
Widgets API are left out.

    python scripts/build-webengine-windows.py --qt 6.12.0 --webengine 6.140.0 --work C:\\qtw

Run it in an x64 MSVC developer environment (vcvars64) with CMake and Ninja on
PATH, after build-windows.py with the same --work: it builds against
<work>/prefix and installs into it. Chromium's build also needs Node.js 18 or
later, gperf, win_flex/win_bison (or flex/bison) on PATH, and a Python 3 with
html5lib; run this script with that Python. Keep the work dir short: Chromium's
paths run deep.

Both configurations are built, as the installed Qt's (debug-and-release,
which the build inherits): Chromium is built once for each, and Qt WebEngine
links its libraries only once both are. Each configuration's install manifest
is kept as install_manifest-<config>.txt in each build tree for
scripts/package-webengine-windows.py.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def run(cmd, cwd=None):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], cwd=cwd, check=True)


def require_tools() -> None:
    try:
        import html5lib  # noqa: F401
    except ImportError:
        raise SystemExit(f"{sys.executable} has no html5lib")
    missing = [" or ".join(names) for names in (("node",), ("gperf",), ("win_flex", "flex"),
                                                ("win_bison", "bison"), ("cl",), ("ninja",))
               if not any(shutil.which(n) for n in names)]
    if missing:
        raise SystemExit("not on PATH: " + ", ".join(missing))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--qt", required=True, help="Qt version, e.g. 6.12.0")
    parser.add_argument("--webengine", required=True, help="Qt WebEngine version, e.g. 6.140.0")
    parser.add_argument("--work", required=True, type=Path)
    args = parser.parse_args()
    work = args.work.resolve()
    prefix = work / "prefix"
    if not (prefix / "bin" / "qt-configure-module.bat").exists():
        raise SystemExit(f"no Qt in {prefix}; run scripts/build-windows.py first")
    require_tools()
    # Chromium's build assumes an English, UTF-8 toolchain; on a localized Windows
    # (e.g. Chinese, GBK) it breaks three ways. Its Python scripts open UTF-8 sources
    # without naming the encoding: UTF-8 mode. With UTF-8 mode they decode tool
    # output (icacls) as UTF-8 too: a UTF-8 console code page, which the tools
    # inherit. And ninja only recognizes cl's English /showIncludes prefix: VSLANG,
    # which takes effect only with Visual Studio's English language pack installed.
    os.environ["PYTHONUTF8"] = "1"
    os.environ["VSLANG"] = "1033"
    import atexit
    import ctypes
    kernel32 = ctypes.windll.kernel32
    # The code page belongs to the console this shares with its caller: put it back.
    atexit.register(kernel32.SetConsoleOutputCP, kernel32.GetConsoleOutputCP())
    atexit.register(kernel32.SetConsoleCP, kernel32.GetConsoleCP())
    kernel32.SetConsoleCP(65001)
    kernel32.SetConsoleOutputCP(65001)

    run([sys.executable, "-I", ROOT / "scripts" / "prepare-sources.py", "--qt", args.qt,
         "--out", work / "src", "qtwebchannel", "--qtwebengine", args.webengine])

    # build-windows.py's Vulkan headers: the installed qtbase's QRhi headers need vulkan.h.
    from importlib import import_module
    vulkan = import_module("build-windows").vulkan_include_dir(work)

    common = ["-G", "Ninja Multi-Config", "-DQT_BUILD_TESTS=OFF", "-DQT_BUILD_EXAMPLES=OFF",
              f"-DVulkan_INCLUDE_DIR={vulkan}"]
    modules = (
        ("qtwebchannel", [], common),
        ("qtwebengine", ["-webengine-proprietary-codecs"],
         common + ["-DFEATURE_qtpdf_build=OFF", "-DFEATURE_qtwebengine_widgets_build=OFF",
                   f"-DPython3_EXECUTABLE={sys.executable}"]),
    )
    for module, options, cmake_args in modules:
        build = work / "build" / module
        build.mkdir(parents=True, exist_ok=True)
        if not (build / "build.ninja").exists():
            run([prefix / "bin" / "qt-configure-module.bat", work / "src" / module, *options,
                 "--", *cmake_args], cwd=build)
        else:
            # An existing tree may predate a configuration installed into the prefix
            # since (qtwebchannel's Debug, say). A Qt targets file globs its per-config
            # files, which CMake doesn't track, so re-run it, or the missing config's
            # links fall back to another config's import library.
            run(["cmake", "."], cwd=build)
        run(["cmake", "--build", "."], cwd=build)
        for config in ("RelWithDebInfo", "Debug"):
            run(["cmake", "--install", ".", "--config", config], cwd=build)
            shutil.copyfile(build / "install_manifest.txt", build / f"install_manifest-{config}.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
