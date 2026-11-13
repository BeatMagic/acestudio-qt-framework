# acestudio-qt-framework

The Qt that [ACE Studio](https://acestudio.ai) builds against and ships, as a patch series on top of the official Qt release sources, with the scripts that build it. The prebuilt archives are served from `https://acestudio-qt-framework-prebuilt.timedomain.dev`, and ACE Studio's bootstrap fetches them by pinned SHA-256.

This repository is the corresponding source for those archives. Qt is licensed under the LGPL, and an application that ships a modified Qt has to make the modified source available. Nothing else in ACE Studio is here.

## What is patched, and why

| Module | Patch | Why |
| --- | --- | --- |
| qtbase | `0001-Keep-macOS-13-working-…` | Qt 6.12 raised its macOS floor to 14, and ACE Studio still supports macOS 13. The patch puts the 6.11 code paths back behind run-time availability checks: the futex falls back to `__ulock_*`, and `QCocoaScreen::grabWindow` returns a null pixmap below 14.4. |
| qtdeclarative | `0001-QQmlJSImporter-don-t-pass-a-reference-…` | `qmlcachegen` crashes intermittently on a large project: `QQmlJSImporter::importHelper` passes a reference into a hash that the callee can rehash. Built on every platform, since the official Windows binaries carry the same bug. |

Each patch's message says what it changes. The full list is `qt/<version>/patches/<module>/`.

## Layout

```
qt/<version>/SHA256SUMS          official source archives, pinned (copied from Qt's .sha256 files)
qt/<version>/patches/<module>/   patch series, applied in name order
scripts/prepare-sources.py       fetch + verify + extract + patch
scripts/build-macos.sh           macOS universal build
scripts/package-macos.sh         macOS archives (libraries + dSYMs)
```

The `Sources` workflow fetches every pinned archive, checks its SHA-256, and applies every patch on each push.

## Reading the source

For upstream Qt, read the [github.com/qt](https://github.com/qt) mirror (for example `github.com/qt/qtbase`, a read-only mirror of `code.qt.io`) at the release tag `v<version>`, or the `Src` component of a Qt installer of the same version. Both match what ACE Studio runs, except in the files the patches touch.

For the exact source of a build, patches included, reproduce it locally:

```sh
python3 scripts/prepare-sources.py --qt 6.12.0 --out ~/Qt/src-acestudio/6.12.0 qtbase qtdeclarative
```

Name the modules you need, or pass `--all`. Modules without patches are byte-identical to upstream. Give it a directory of its own, not an installer's `Src`: a module directory that already exists is left as it is, so it would stay unpatched.

## Builds

A build is named `qt-<version>-<target>-<revision>`. The revision goes up whenever the patch set or the build recipe changes. The tag of that name marks the commit that build was made from.

| Build | Archives | Toolchain |
| --- | --- | --- |
| `qt-6.12.0-macos13-2` | `qt-6.12.0-macos13-2-universal.tar.xz`, `…-universal-dsym.tar.xz` | Xcode 27.2 (SDK 27.2), CMake 4.4.4, Ninja 1.13.2, OpenSSL 3.5.9 headers |

### macOS

On an Apple Silicon Mac with Xcode, CMake and Ninja:

```sh
OPENSSL_ROOT_DIR=/path/to/openssl3 scripts/build-macos.sh 6.12.0 /path/to/work
scripts/package-macos.sh 6.12.0 <revision> /path/to/work
```

This builds universal (x86_64 + arm64) with a macOS 13 deployment target: release with debug info split into dSYMs, and the OpenSSL backend loaded at run time. It takes about 75 minutes on an M-series laptop, and the build tree reaches about 33 GB.

### Windows

The Windows build is the official `msvc2022_64` binaries with qtdeclarative rebuilt from patched source. The recipe and its workflow are coming.

## License

The patches modify Qt and are under the licenses of the files they modify, as Qt offers them: LGPL-3.0-only, GPL-2.0-only or GPL-3.0-only. See [qt.io/licensing](https://www.qt.io/licensing/).
