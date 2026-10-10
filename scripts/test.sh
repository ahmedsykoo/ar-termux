#!/usr/bin/env bash
# Run the layout unit test against the patched RtlRunLayout.java (no Android SDK needed).
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
git init -q "$TMP/s"; mkdir -p "$TMP/s/terminal-view/src/main/java/com/termux/view"
# The patch creates RtlRunLayout.java as a new file; apply only that hunk onto an empty tree.
git -C "$TMP/s" apply --include='terminal-view/src/main/java/com/termux/view/RtlRunLayout.java' "$HERE"/patches/0001-*.patch
javac -d "$TMP/out" "$TMP/s/terminal-view/src/main/java/com/termux/view/RtlRunLayout.java" "$HERE/tests/LayoutTest.java"
java -cp "$TMP/out" com.termux.view.LayoutTest
