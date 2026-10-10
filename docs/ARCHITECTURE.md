# Architecture

Upstream Termux draws each terminal row in `TerminalRenderer.render()` by splitting it into *runs* of equal style and
drawing every character in its own cell, scaling glyphs whose measured width differs from the cell width. For Arabic
that produces isolated letter forms in left-to-right order.

The patch changes only `terminal-view`:

1. **RTL runs.** Characters in the Hebrew/Arabic/Syriac/Thaana/N'Ko/Arabic-Extended/presentation-form ranges start an
   RTL run. Blanks and punctuation continue it only if more RTL text follows (look-ahead), so trailing spaces never
   join a run. Runs are drawn with `Canvas.drawTextRun(..., isRtl=true)` so Android's text engine shapes the letters.
2. **Row collection.** Runs of a row are collected instead of drawn immediately (`RunInfo`).
3. **Base direction.** If the first strong character of a row is RTL (and the row has no box-drawing characters), the
   row is reordered: consecutive runs of the same direction form groups, groups are placed right-to-left, RTL groups
   are reversed internally (`RtlRunLayout`, pure Java, unit tested in `tests/`).
4. **Neutrals.** Blanks/punctuation at the edge of an LTR run next to an RTL run move into the RTL group (Unicode rule
   for neutrals between runs of different direction → base direction).
5. **Packing.** In reordered rows RTL runs are positioned by their real shaped width (`getRunAdvance`), not by cell count.
6. **Two-pass drawing.** All backgrounds (also over the original cells) first, then all text, so a background can never
   cover moved text and no black gaps appear.

Rows that start with Latin text (shell prompts, commands) keep a left-to-right base direction, as in most terminals.
