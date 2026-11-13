#!/bin/sh
# SPDX-FileCopyrightText: 2026 Timedomain Inc.
# SPDX-License-Identifier: MIT
# Packages a scripts/build-macos.sh install as the two archives ACE Studio fetches:
#
#   qt-<version>-macos13-<revision>-universal.tar.xz        the libraries and tools
#   qt-<version>-macos13-<revision>-universal-dsym.tar.xz   the dSYM bundles
#
#   scripts/package-macos.sh <version> <revision> <work dir>
#
# Each archive holds one top-level directory. The dSYM archive mirrors the
# install's layout, so its bundles unpack beside the libraries they belong to.
# Archives land in <work>/dist; print their SHA-256 sums for the pin.
set -eu
VERSION=$1
REV=$2
W=$(cd "$3" && pwd)
N=qt-$VERSION-macos13-$REV-universal
S=$W/dist/stage

rm -rf "$S"
mkdir -p "$S/$N-dsym"
cp -Rc "$W/install" "$S/$N" 2>/dev/null || cp -R "$W/install" "$S/$N"
cd "$S/$N"
find . -name '*.dSYM' -prune -print | while read -r d; do
    mkdir -p "../$N-dsym/$(dirname "$d")"
    mv "$d" "../$N-dsym/$d"
done
cd "$S"
tar -cf - "$N" | xz -T0 -6 > "../$N.tar.xz"
tar -cf - "$N-dsym" | xz -T0 -3 > "../$N-dsym.tar.xz"
cd ..
rm -rf "$S"
shasum -a 256 "$N.tar.xz" "$N-dsym.tar.xz"
