#!/bin/sh
# SPDX-FileCopyrightText: 2026 Timedomain Inc.
# SPDX-License-Identifier: MIT
# Builds the macOS Qt that ACE Studio ships: universal (x86_64 + arm64), macOS 13
# deployment target, release with debug info split into dSYMs, and the OpenSSL TLS
# backend loaded at run time (as the official build has it; the app ships its own
# OpenSSL 3).
#
#   scripts/build-macos.sh <version> <work dir>
#
# Sources go to <work>/src (scripts/prepare-sources.py), build trees to
# <work>/build, the install to <work>/install. Needs Xcode, CMake, Ninja, and
# OPENSSL_ROOT_DIR pointing at OpenSSL 3 headers (headers only: with
# -openssl-runtime Qt dlopens libssl). The build tree reaches about 33 GB.
set -eu
VERSION=$1
W=$(cd "$2" && pwd)
: "${OPENSSL_ROOT_DIR:?point OPENSSL_ROOT_DIR at OpenSSL 3 headers}"
ROOT=$(cd "$(dirname "$0")/.." && pwd)
MODULES="qtshadertools qtsvg qtimageformats qtdeclarative qtwebsockets qttools qttranslations"
P=$W/install
B=$W/build

python3 -I "$ROOT/scripts/prepare-sources.py" --qt "$VERSION" --out "$W/src" qtbase $MODULES

mkdir -p "$B/qtbase"
cd "$B/qtbase"
"$W/src/qtbase/configure" -prefix "$P" -release -force-debug-info -separate-debug-info \
    -nomake tests -nomake examples -openssl-runtime -- \
    -G Ninja "-DCMAKE_OSX_ARCHITECTURES=x86_64;arm64" -DCMAKE_OSX_DEPLOYMENT_TARGET=13.0 \
    "-DOPENSSL_ROOT_DIR=$OPENSSL_ROOT_DIR"
cmake --build .
cmake --install .

for m in $MODULES; do
    mkdir -p "$B/$m"
    cd "$B/$m"
    "$P/bin/qt-configure-module" "$W/src/$m" -- -G Ninja -DQT_BUILD_TESTS=OFF -DQT_BUILD_EXAMPLES=OFF
    cmake --build .
    cmake --install .
done
