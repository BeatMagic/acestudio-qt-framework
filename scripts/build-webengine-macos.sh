#!/bin/sh
# SPDX-FileCopyrightText: 2026 Timedomain Inc.
# SPDX-License-Identifier: MIT
# Builds Qt WebEngine for the macOS Qt that scripts/build-macos.sh built, together
# with Qt WebChannel, which carries the page bridge. Same configuration as that Qt
# (universal, macOS 13 deployment target, separate debug info), plus the proprietary
# codecs: Chromium's FFmpeg with H.264 and AAC. Qt PDF and the Widgets API are left out.
#
#   scripts/build-webengine-macos.sh <qt version> <webengine version> <work dir>
#
# Needs scripts/build-macos.sh's install in <work>/install, and installs into it.
# Sources go to <work>/src, build trees to <work>/build. Besides Xcode (with its Metal
# Toolchain component), CMake and Ninja, Chromium's build needs Node.js 18 or later,
# gperf, and a Python 3 with html5lib: point PYTHON3 at it (default: python3).
set -eu
QT_VERSION=$1
WEBENGINE_VERSION=$2
W=$(cd "$3" && pwd)
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PY=${PYTHON3:-python3}
P=$W/install
B=$W/build

"$PY" -c 'import html5lib' 2>/dev/null || { echo "$PY has no html5lib" >&2; exit 1; }
python3 -I "$ROOT/scripts/prepare-sources.py" --qt "$QT_VERSION" --out "$W/src" qtwebchannel \
    --qtwebengine "$WEBENGINE_VERSION"

mkdir -p "$B/qtwebchannel"
cd "$B/qtwebchannel"
"$P/bin/qt-configure-module" "$W/src/qtwebchannel" -- -G Ninja -DQT_BUILD_TESTS=OFF -DQT_BUILD_EXAMPLES=OFF
cmake --build .
cmake --install .

mkdir -p "$B/qtwebengine"
cd "$B/qtwebengine"
"$P/bin/qt-configure-module" "$W/src/qtwebengine" -webengine-proprietary-codecs -- -G Ninja \
    -DQT_BUILD_TESTS=OFF -DQT_BUILD_EXAMPLES=OFF \
    -DFEATURE_qtpdf_build=OFF -DFEATURE_qtwebengine_widgets_build=OFF \
    "-DPython3_EXECUTABLE=$(command -v "$PY")"
cmake --build .
cmake --install .
