<!--
SPDX-FileCopyrightText: 2026 Timedomain Inc.
SPDX-License-Identifier: MIT
-->

# acestudio-qt-framework

The Qt that [ACE Studio](https://acestudio.ai) ships, as a patch series on top of the official Qt release sources, with the scripts that build it. Qt's open-source licenses require an application that ships a modified Qt to make the modified source available; this repository is that source.

## What is patched, and why

| Module | Patch | Why |
| --- | --- | --- |
| qtbase | `0001-Keep-macOS-13-working-…` | Qt 6.12 raised its macOS floor to 14, and ACE Studio still supports macOS 13. The patch puts the 6.11 code paths back behind run-time availability checks: the futex falls back to `__ulock_*`, and `QCocoaScreen::grabWindow` returns a null pixmap below 14.4. |
| qtdeclarative | `0001-QQmlJSImporter-don-t-pass-a-reference-…` | `qmlcachegen` crashes intermittently on a large project: `QQmlJSImporter::importHelper` passes a reference into a hash that the callee can rehash. |
| qtdeclarative | `0002-QQuickPopupWindow-close-the-whole-menu-chain-…` | Pressing the title of an open `MenuBar` menu shown as `Popup.Window` leaves the menu open: the press is swallowed, but the menus are closed through a path that spares a popup while the press lands inside its parent item, which for a menu bar menu is that title. The patch closes the whole chain, as Qt 6.10 did. |

Each patch's message says what it changes.

## Layout

```
qt/<version>/SHA256SUMS          official source archives, pinned (copied from Qt's .sha256 files)
qt/<version>/patches/<module>/   patch series, applied in name order
scripts/prepare-sources.py       fetch + verify + extract + patch
scripts/build-macos.sh           macOS universal build
scripts/package-macos.sh         macOS archives (libraries + dSYMs)
scripts/fetch-qt-binaries.py     official Windows binaries, laid out as a prefix
scripts/build-windows.py         Windows: patched modules rebuilt over them
scripts/package-windows.py       Windows archives (libraries + PDBs)
```

Each script's header says how to run it. The `Sources` workflow fetches every pinned archive, checks its SHA-256, and applies every patch on each push.

## Building

macOS, on an Apple Silicon Mac with Xcode, CMake and Ninja: universal (x86_64 + arm64), macOS 13 deployment target, release with debug info split into dSYMs.

```sh
OPENSSL_ROOT_DIR=/path/to/openssl3 scripts/build-macos.sh 6.12.0 <work>
scripts/package-macos.sh 6.12.0 <revision> <work>
```

Windows: the official `msvc2022_64` binaries, with every patched module except qtbase rebuilt from patched source with the configuration it inherits from the installed qtbase, and installed over them. In an x64 MSVC developer prompt with CMake and Ninja, or through the `Windows` workflow:

```bat
python scripts\build-windows.py --qt 6.12.0 --work C:\qtw
python scripts\package-windows.py --qt 6.12.0 --revision <revision> --work C:\qtw
```

A build is named `qt-<version>-<target>-<revision>`; the revision goes up whenever the patch set or the recipe changes, and the tag of that name marks the commit it was built from.

## License

Every file carries its license as an SPDX identifier, following [REUSE](https://reuse.software); the texts are in `LICENSES/`, and CI runs `reuse lint`.

- The scripts, workflows and this README are MIT.
- A patch carries the license of the Qt files it modifies, minus Qt's commercial option: the qtbase patch and the qtdeclarative `0002` patch (QtQuickTemplates2) are `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`, and the qtdeclarative `0001` patch, which touches QtQmlCompiler (the library behind `qmlcachegen`), is `GPL-3.0-only WITH Qt-GPL-exception-1.0`.
