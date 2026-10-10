# Contributing

**How changes get in:** open an Issue first (what's wrong, screenshot, device). You can send a Pull Request, but
**maintainers review everything and decide** — a PR may be accepted, changed or declined, and only maintainers publish releases.
See [GOVERNANCE.md](GOVERNANCE.md).

AR Termux is **Termux plus one patch** to the terminal renderer. We do not fork Termux: `patches/` is applied to the
exact upstream commit in `BASE_COMMIT`.

- Rendering change → edit the patch (clone upstream at `BASE_COMMIT`, change `terminal-view/.../TerminalRenderer.java`,
  then `git diff > patches/0001-arabic-rtl-shaping.patch`; include new files with `git add -N`).
- Layout logic lives in `RtlRunLayout.java` (pure Java). Add a case to `tests/LayoutTest.java` and run `scripts/test.sh`.
- Rendering bugs: please attach a **screenshot** and the exact text/program.
- Updating Termux: change `BASE_COMMIT`, make sure the patch still applies, rebuild, test on a device.
