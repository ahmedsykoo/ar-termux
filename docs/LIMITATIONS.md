# Known limitations

- **Beta, one test device.** Please report your device + Android version.
- Rows that start with Latin text (e.g. `echo "…"`) use a left-to-right base direction, so the Arabic parts inside are
  each correct but their order between Latin words is not "Arabic-natural".
- In long wrapped rows that mix code and Arabic, a word can occasionally be cut at the left edge or punctuation can land on the
  wrong side of a word.
- Text selection and touch positions are not remapped for reordered rows.
- The cursor position while typing Arabic can look off (the terminal tracks one column per character).
- Replaces Termux (same package name `com.termux`); can't coexist with it. Uninstall Termux and its add-ons first.
- Release APKs use Termux's public test key — see [SECURITY.md](../SECURITY.md).
