# Bravetel Support (branded RustDesk)

This branch (`bravetel`) is RustDesk 1.5.3 plus Bravetel branding. `master` mirrors upstream and is not built.

- `apply_branding.py` patches the source tree in CI (name, compiled-in server and key, hidden settings,
  update checker off, links, icons). Each edit must match exactly once, so upstream drift fails the build.
- `make_icons.py` regenerates `assets/` from the brand exports (`fusionpbx-automation/brand/exports`).
  `.gitignore` excludes `*png`, so add new PNGs with `git add -f`.
- `PLAN.md` has the source references behind every change.
- CI: `.github/workflows/bravetel-windows.yml` (push to `bravetel`, manual run, or tag `bravetel-<ver>-<n>`
  to publish a release). Upstream trigger workflows are removed on this branch.

Outputs (same file, two names):
- `bravetel-support-<ver>-x64.exe`: unattended agent; the console install script runs it with `--silent-install`.
- `bravetel-support-qs-x64.exe`: QuickSupport; runs without install, install disabled.

Signing: Azure Artifact Signing. Add repository secrets `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`,
`AZURE_CLIENT_SECRET` and variables `AZURE_SIGNING_ENDPOINT`, `AZURE_SIGNING_ACCOUNT`, `AZURE_CERT_PROFILE`.
Without them the build is unsigned.

Licence: RustDesk is AGPL-3.0. Keep this fork public and the upstream copyright notice in About.
