#!/bin/sh
# SPDX-FileCopyrightText: 2026 Timedomain Inc.
# SPDX-License-Identifier: MIT
# Packages what scripts/build-webengine-macos.sh installed as two archives that
# unpack over the Qt archive of the same Qt version:
#
#   qtwebengine-<webengine version>-qt<qt version>-macos13-<revision>-universal.tar.xz
#   qtwebengine-<webengine version>-qt<qt version>-macos13-<revision>-universal-dsym.tar.xz
#
#   scripts/package-webengine-macos.sh <qt version> <webengine version> <revision> <work dir>
#
# The files are those the qtwebchannel and qtwebengine builds installed (their
# install_manifest.txt), laid out as in the Qt install, under one top-level directory.
# The dSYM archive holds the dSYM bundles the same way. Archives land in <work>/dist;
# print their SHA-256 sums for the pin.
set -eu
QT_VERSION=$1
WEBENGINE_VERSION=$2
REV=$3
W=$(cd "$4" && pwd)
N=qtwebengine-$WEBENGINE_VERSION-qt$QT_VERSION-macos13-$REV-universal
P=$W/install
S=$W/dist/stage

rm -rf "$S"
mkdir -p "$S/$N" "$S/$N-dsym"
# A manifest does not end in a newline: awk 1 ends each with one, where cat would
# join one's last path to the next one's first. It runs on its own so that set -e
# stops on a missing manifest, which a pipeline's status would hide.
awk 1 "$W/build/qtwebchannel/install_manifest.txt" "$W/build/qtwebengine/install_manifest.txt" > "$S/manifest"
sed -n "s|^$P/||p" "$S/manifest" | sort -u | while read -r f; do
    case $f in
    *.dSYM/*) d=$S/$N-dsym ;;
    *) d=$S/$N ;;
    esac
    mkdir -p "$d/$(dirname "$f")"
    cp -Pc "$P/$f" "$d/$f" 2>/dev/null || cp -P "$P/$f" "$d/$f"
done
cd "$S"
tar -cf - "$N" | xz -T0 -6 > "../$N.tar.xz"
tar -cf - "$N-dsym" | xz -T0 -3 > "../$N-dsym.tar.xz"
cd ..
rm -rf "$S"
shasum -a 256 "$N.tar.xz" "$N-dsym.tar.xz"
