# Progress (C7Support app)

Branch `c7master` is RustDesk 1.5.3 plus Count7 branding (`branding/apply_branding.py`, `branding/assets/`).
Full project status, chosen values and next steps live in the console repo:
**https://github.com/count7ltd/c7rust-console/blob/main/progress.md**. Read that first.

## 2026-11-16

- Done: servers `rd.count7.net` / `https://remote.count7.net`; app C7Support (`c7support.exe`, `c7support://`),
  Count7 Ltd, count7.co.uk links, bundle id `net.count7.support`; C7 icons and count7 wordmark; build triggers on
  `c7master` and `c7-*` tags; output files `c7support-*`.
- Next:
  1. Set `SERVER_KEY` in `branding/apply_branding.py` to the key from the new server
     (`docker exec rustdesk-hbbr cat /root/id_ed25519.pub`). Until then the build fails on purpose (template-key guard).
  2. Enable GitHub Actions on this repo, push, then tag `c7-1.5.3-1` to publish the release.
  3. Copy the hash from the release's `SHA256SUMS.txt` into the console's `src/brand.ts` (`client.sha256`).
- Notes: never run `apply_branding.py` in a working copy you commit from (it patches the tree; CI runs it).
  PNGs are git-ignored here: `git add -f branding/assets/*`. Keep this repo public (AGPL-3.0).
- Blockers: server key.
