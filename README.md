<!--
SPDX-FileCopyrightText: 2026 Timedomain Inc.
SPDX-License-Identifier: MIT
-->

# acestudio-qt-framework

The Qt that [ACE Studio](https://acestudio.ai) ships, as a patch series on top of the official Qt release sources, with the scripts that build it. Qt's open-source licenses require an application that ships a modified Qt to make the modified source available; this repository is that source.

## What is patched, and why

| Module | Patch | Why |
| --- | --- | --- |
| qtbase | `0001-Keep-macOS-13-working-…` | Qt 6.12 requires macOS 14; ACE Studio still supports macOS 13. |
| qtdeclarative | `0001-QQmlJSImporter-don-t-pass-a-reference-…` | Fixes an intermittent `qmlcachegen` crash. |
| qtdeclarative | `0002-QQuickPopupWindow-close-the-whole-menu-chain-…` | Pressing the title of an open menu bar menu closes it again. |

The patches are in `qt/<version>/patches/<module>/`, and each one's message explains the change.

## Building

`scripts/prepare-sources.py` fetches the official sources, checks them against `qt/<version>/SHA256SUMS`, and applies the patches. The build scripts call it.

macOS (universal, macOS 13 deployment target), with Xcode, CMake and Ninja:

```sh
OPENSSL_ROOT_DIR=/path/to/openssl3 scripts/build-macos.sh 6.12.0 <work>
scripts/package-macos.sh 6.12.0 <revision> <work>
```

Windows (the official MSVC 2022 binaries, with the patched modules rebuilt over them), in an x64 MSVC developer prompt with CMake and Ninja:

```bat
python scripts\build-windows.py --qt 6.12.0 --work C:\qtw
python scripts\package-windows.py --qt 6.12.0 --revision <revision> --work C:\qtw
```

Qt WebEngine (with Qt WebChannel) is built on top of that Qt and packaged on its own, to unpack over the Qt archive. It is built with the proprietary codecs (H.264 and AAC through Chromium's FFmpeg). macOS:

```sh
PYTHON3=/path/to/python-with-html5lib scripts/build-webengine-macos.sh 6.12.0 6.140.0 <work>
scripts/package-webengine-macos.sh 6.12.0 6.140.0 <revision> <work>
```

Windows, after `build-windows.py` with the same work dir, in an x64 MSVC developer prompt with Node.js, gperf and win_flex_bison on PATH, and a Python with html5lib. Both of the Qt's configurations, Debug and RelWithDebInfo, are built. Package the Qt with `package-windows.py` first: WebEngine installs into the same prefix. On a Windows whose display language isn't English, Visual Studio's English language pack must be installed:

```bat
python scripts\build-webengine-windows.py --qt 6.12.0 --webengine 6.140.0 --work C:\qtw
python scripts\package-webengine-windows.py --qt 6.12.0 --webengine 6.140.0 --revision <revision> --work C:\qtw
```

Each build is tagged `qt-<version>-<target>-<revision>` on the commit it was built from, and a Qt WebEngine build `qtwebengine-<version>-<target>-<revision>`.

## License

The scripts are MIT. Each patch is under the license of the Qt files it modifies, as its message states. The license texts are in `LICENSES/`.
