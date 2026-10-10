#!/usr/bin/env bash
# Build AR Termux locally: clone upstream at the pinned commit, apply the patch, build the APK.
# Needs: JDK 17, Android SDK + NDK (see Termux's own build docs), git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${WORK:-$HERE/build/termux-app}"
mkdir -p "$(dirname "$WORK")"
if [ ! -d "$WORK/.git" ]; then git clone https://github.com/termux/termux-app "$WORK"; fi
git -C "$WORK" fetch --all -q
git -C "$WORK" checkout -q -f "$(cat "$HERE/BASE_COMMIT")"
git -C "$WORK" clean -fdq
for p in "$HERE"/patches/*.patch; do git -C "$WORK" apply --verbose "$p"; done
( cd "$WORK" && ./gradlew assembleDebug --no-daemon )
echo "APKs: $WORK/app/build/outputs/apk/debug/"
