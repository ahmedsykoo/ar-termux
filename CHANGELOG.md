# Changelog

## v0.1.0-beta.2 — 2026-10-10
- Fixed release asset naming for the x86_64 build (was `..._64.apk`, now `..._x86_64.apk`). No code changes.

## v0.1.0-beta.1 — 2026-10-10
First public beta. Based on Termux commit in `BASE_COMMIT`.
- Shaped right-to-left runs (connected Arabic letters) instead of one glyph per cell.
- Row-level right-to-left ordering for rows that start with RTL text (mixed Arabic/Latin reads naturally).
- Neutral characters (spaces, punctuation) between RTL and LTR text follow the RTL base direction.
- Rows with box-drawing characters (tables/frames) keep their column layout.
- Backgrounds are painted before text, over the original cells, so reordering never leaves black gaps.
