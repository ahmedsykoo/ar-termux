# Security

**Release APKs are signed with Termux's public *test* key** (`testkey_untrusted.jks`, the debug key in upstream).
That key is public, so anyone can produce an APK that Android treats as an "update" to AR Termux. Only install APKs
from this repository's Releases and verify the `SHA256SUMS.txt` attached to each release.

AR Termux changes only how text is drawn; it ships Termux's own bootstrap packages unchanged.

Report vulnerabilities privately through GitHub's "Report a vulnerability" (Security tab).
