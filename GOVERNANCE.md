# Governance

AR Termux is open to read and use, and **maintained by a small team that decides what goes in**.

- **Using it:** download the APK from [Releases](../../releases). Free for everyone.
- **Official builds:** only the Releases of this repository (with `SHA256SUMS.txt`) are official.
- **Changing it:** open an *Issue* describing the problem, or a *Pull Request*. Maintainers review every change and decide
  whether to accept it. Nothing is merged without maintainer approval, and `main` is protected.
- **Releases:** only maintainers tag and publish releases.
- **Forks:** the code is under GPL-3.0 (required by Termux's license), so you may build and modify your own copy. Such
  builds are not official releases and are not supported here.

Maintainer setup (repo Settings → Branches → rule for `main`): require a pull request with 1 approval and Code Owner review,
require the `test` status check, restrict who can push, block force-pushes and deletions; Settings → Actions: require approval for
workflows from outside collaborators.
