# Claude Code / OpenCode in AR Termux

Claude Code has **no native Android build** (`linux-arm64-android` isn't published), so it can't run directly in Termux.
Run it inside Ubuntu (proot), where it is `linux-arm64`:

```bash
pkg install -y proot-distro
proot-distro install ubuntu
proot-distro login ubuntu
# inside Ubuntu:
apt update && apt install -y nodejs npm
npm i -g --allow-scripts=@anthropic-ai/claude-code @anthropic-ai/claude-code
claude
```

OpenCode (free models available in its model list; read its privacy notes — free models may use your data for training):

```bash
# inside Ubuntu
npm i -g opencode-ai@latest
opencode        # ctrl+p → models → pick one marked "free"
```

Arabic renders correctly in both because drawing happens in the app, not inside Linux.
