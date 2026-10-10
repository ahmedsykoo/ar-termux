# Changelog

## Unreleased
- Shaped right-to-left runs (connected Arabic letters) instead of one glyph per cell.
- Row-level right-to-left ordering for rows that start with RTL text (mixed Arabic/Latin reads naturally).
- Neutral characters (spaces, punctuation) between RTL and LTR text follow the RTL base direction.
- Rows with box-drawing characters (tables/frames) keep their column layout.
- Backgrounds are painted before text, over the original cells, so reordering never leaves black gaps.
