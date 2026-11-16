<!--
SPDX-FileCopyrightText: 2026 Timedomain Inc.
SPDX-License-Identifier: MIT
-->

# Working in this repository

This repository is public, and it holds only what Qt's licenses require ACE Studio to publish: the patches and the scripts that build its Qt. Nothing about the infrastructure goes here, in files, comments or commit messages: where archives are hosted, runners, internal paths, build timings, the list of builds and their toolchains. That lives in the team's internal notes.

The README is for a human reading this repository for the first time: one line per patch, no internals. Details belong in the patch messages and the script headers.

## Patches

- A patch is a `git format-patch` of the module's source tree (paths without the module prefix), applied with `git apply` in name order by `scripts/prepare-sources.py`. `.gitattributes` keeps `*.patch` byte-exact (`-text`).
- Its message says what it changes and why, then ends with three lines:
  ```
  SPDX-FileCopyrightText: 2026 Timedomain Inc.
  SPDX-License-Identifier: <the modified Qt files' license, minus LicenseRef-Qt-Commercial>
  (the license of the <module> files this patch modifies)
  ```
  Today that is `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` for qtbase and for QtQuickTemplates2, and `GPL-3.0-only WITH Qt-GPL-exception-1.0` for QtQmlCompiler. Read the header of the file you modify; a license not yet in `LICENSES/` needs its text added there.
- Add the patch's row to the README table.

## Files and checks

- Every file carries an SPDX header (MIT, `Timedomain Inc.`).
- The `Sources` workflow runs on every push and PR: it fetches every pinned archive, checks its SHA-256, and applies every patch.
- The `Windows` workflow is dispatched by hand (Qt version, revision) and returns the archives as artifacts.

## Builds

The revision goes up whenever the patch set or the build recipe changes; a change to docs alone needs no build. The tag `qt-<version>-<target>-<revision>` marks the commit a build was made from.

Commit messages follow Conventional Commits.
