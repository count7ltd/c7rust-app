# Bravetel Support: branded macOS client, build plan

As of 2026-11-14. Source read: branch `bravetel` (`dac3e8a`, upstream tag `1.5.3` + 2 cherry-picks + branding),
submodule `libs/hbb_common` at `fae47e0`. All `file:line` refs are to that tree **before** `apply_branding.py`
runs. `UNVERIFIED` marks anything not confirmed from source or by a run. Companion to `branding/PLAN.md` (Windows).

---

## 0. Summary of decisions

| Item | Value | Why (section) |
|---|---|---|
| `APP_NAME` (runtime) | `Bravetel-Support` (unchanged from Windows) | 1.1 |
| Xcode `PRODUCT_NAME` | `Bravetel-Support`, **must equal `APP_NAME`** | 1.2 |
| Bundle id | `com.bravetel.support` (proposed; must not contain `rustdesk`; never change after rollout) | 1.3, 6 |
| URL scheme | `bravetel-support` | 1.4 |
| `ORG` (`com.carriez`) | **keep** | 1.5 |
| Bundle on disk | `/Applications/Bravetel-Support.app/Contents/MacOS/{Bravetel-Support,service}` | 1.2 |
| `hide-help-cards` | Windows only. On macOS it hides the permission cards | 3.3 |
| Tray | new monochrome template glyph; upstream would render our colour icon as a solid blob | 2.3 |
| QuickSupport (QS) | Phase 1: run the app from the DMG without copying to /Applications. Phase 2 (optional): QS DMG with a renamed bundle | 3.4 |
| CI | arm64 (`macos-15`, Flutter 3.44.9) + x86_64 (`macos-15-intel`, Flutter 3.24.5), ad hoc signed DMG per arch | 4 |

---

## 1. Name and bundle

### 1.1 Everything on macOS derives from runtime `APP_NAME`

Runtime `APP_NAME` is set by our hook in `load_custom_client()`, and every macOS process goes through it:
- GUI: `MainFlutterWindow.swift:59` `rustdesk_core_main()` -> `src/flutter.rs:114-126` -> `core_main.rs:49`. Dart init passes an empty custom config (`flutter/lib/models/native_model.dart:239`), so it also calls `load_custom_client()` (`src/flutter_ffi.rs:50-52`).
- LaunchAgent `--server`: same exe -> `core_main.rs:49`, then `core_main.rs:384-409` (server + tray).
- Root LaunchDaemon `service` binary: `src/service.rs:9` calls `load_custom_client()` before `--write-plists` or `start_os_service()` (`service.rs:10-18`).

Paths and names derived from it (all automatic, no edits needed):

| Thing | Value with `APP_NAME=Bravetel-Support` | Source |
|---|---|---|
| Config dir | `~/Library/Preferences/com.carriez.Bravetel-Support/` (root: `/var/root/...`) | `ProjectDirs::from("", ORG, APP_NAME)` `libs/hbb_common/src/config.rs:929-938`, `ORG="com.carriez"` `config.rs:57`; matches the template in `install.scpt:3` |
| Config files | `Bravetel-Support.toml`, `Bravetel-Support2.toml` | `config.rs:879`; `install.scpt:4-5` |
| Logs | `~/Library/Logs/Bravetel-Support/` | `config.rs:953-956` |
| IPC | `/tmp/Bravetel-Support-service/ipc_service`, `/tmp/Bravetel-Support-<uid>/ipc` | `config.rs:136-145`, `981-1024` |
| LaunchDaemon | `/Library/LaunchDaemons/com.carriez.Bravetel-Support_service.plist`, label `com.carriez.Bravetel-Support_service` | `src/platform/macos.rs:397-401`, `1230`, `1362`; `get_full_name()` `src/common.rs:1240-1247`; `is_installed_daemon()` `macos.rs:226-238` |
| LaunchAgent | `/Library/LaunchAgents/com.carriez.Bravetel-Support_server.plist` | `macos.rs:402-405`, `1229`, `1363` |
| Plist bodies | `agent.plist`/`daemon.plist`/`*.scpt` are templates; `correct_app_name()` replaces `com.carriez.rustdesk` with the running bundle id, then `rustdesk` with lowercase `APP_NAME`, then `RustDesk` with `APP_NAME` | `macos.rs:365-373`; used at `macos.rs:244-260`, `321`, `409-416`, `433` |
| Agent program | `/Applications/Bravetel-Support.app/Contents/MacOS/Bravetel-Support --server` | `privileges_scripts/agent.plist:29-33` after `correct_app_name` |
| Daemon program | `/Applications/Bravetel-Support.app/Contents/MacOS/service` | `daemon.plist:17` |
| Daemon logs | `/var/log/bravetel-support_service.{err,out}` | `daemon.plist:23-26` |
| admin prompt text | "Bravetel-Support wants to install daemon and agent" | `install.scpt:19` |
| "installed" test | exe path starts with `/Applications/Bravetel-Support.app` | `macos.rs:933-941` |
| IPC peer check | server must be `/Applications/Bravetel-Support.app/Contents/MacOS/Bravetel-Support` | `src/ipc/auth.rs:595-619` |
| Root updater | checks `Contents/MacOS/{APP_NAME}` and `service` in the staged bundle | `macos.rs:1754-1758` |
| URI prefix | `bravetel-support://` | `src/common.rs:1235-1238` |
| Name validation | `Bravetel-Support` passes. macOS rejects only a leading hyphen | `src/platform/mod.rs:41-63` |

So **yes, runtime `APP_NAME` matters on macOS**: it decides the install path, the launchd labels, the config dir and IPC.
The config dir is `com.carriez.Bravetel-Support` (from `ORG`), not the bundle id.

### 1.2 `PRODUCT_NAME` must equal `APP_NAME` (hard requirement)

- `PRODUCT_NAME = RustDesk` (`flutter/macos/Runner/Configs/AppInfo.xcconfig:8`) sets the bundle name and executable: `CFBundleExecutable=$(EXECUTABLE_NAME)`, `CFBundleName=$(PRODUCT_NAME)` (`Info.plist:7-8`, `15-16`). The Runner target does not override it. `PRODUCT_NAME = "$(TARGET_NAME)"` at `project.pbxproj:459`, `642`, `650` sits in configs with no AppInfo base (the aggregate target).
- Flutter finds the app through `$PRODUCT_NAME.app` (`project.pbxproj:280`).
- The launchd plists, `is_installed()`, IPC auth and the updater all expect `/Applications/{APP_NAME}.app/Contents/MacOS/{APP_NAME}` (table above). If they differ, the agent plist points to a missing exe, the daemon card never clears, and IPC auth rejects the server.
- **Change:** `PRODUCT_NAME = Bravetel-Support`.
- `build.py:949` hard-codes `RustDesk.app` when it copies the `service` binary into the bundle. It must be edited (5.1 M6), otherwise the build fails or the bundle has no `service`.
- Module name: Swift `PRODUCT_MODULE_NAME` defaults from `PRODUCT_NAME` (it would become `Bravetel_Support`). `MainMenu.xib:16` and `:333` bind `AppDelegate`/`MainFlutterWindow` with `customModule="RustDesk" customModuleProvider="target"`. With "inherit from target", ibtool should use the target module. UNVERIFIED, so pin `PRODUCT_MODULE_NAME = RustDesk` in `AppInfo.xcconfig` to remove the risk. Nothing else references the module (no `-Swift.h` imports, grep).
- Leave: `project.pbxproj:63`/`122`/`203` product reference `RustDesk.app` (Xcode file-reference label, UNVERIFIED that it is purely cosmetic, low risk); `librustdesk.dylib` (`build.py:942-943`, `project.pbxproj:29-30`, `77`); `service` binary name (`Cargo.toml:19-21`; plists and scripts use it).
- Display: menu bar, About and Dock show `Bravetel-Support` (hyphen), same as Windows R1. `LSUIElement=1` hides the Dock icon (`Info.plist:48-49`). Optional `CFBundleDisplayName "Bravetel Support"`: effect on Finder and launchd UI is UNVERIFIED, so skip it in phase 1.

### 1.3 Bundle id

- Effective id today is `com.carriez.rustdesk`: Runner target settings `project.pbxproj:448` (Profile), `593` (Debug), `630` (Release) override the xcconfig base value `com.carriez.flutterHbb` (`AppInfo.xcconfig:11`; base ref `project.pbxproj:428`, `574`, `604`).
- Uses: `AssociatedBundleIdentifiers` in both launchd plists (`agent.plist:8-9`, `daemon.plist:8-9`, filled by `get_bundle_id()` `macos.rs:2116-2137` via `correct_app_name`); TCC privacy grants; update bundle id checks (`macos.rs:74`, `1200-1205`; `update.scpt:22`); `manual_update.rs:46-57` (custom clients use their own bundle id).
- **Change all three pbxproj lines and the xcconfig** to `com.bravetel.support`.
- It must **not contain `rustdesk`**: `correct_app_name` substitutes the bundle id first and then rewrites every `rustdesk` (`macos.rs:367-370`), which would mangle it.

### 1.4 URL scheme

`Info.plist:21-35` registers `rustdesk` (`CFBundleURLName com.carriez.rustdesk`). Rust expects `bravetel-support://` (`common.rs:1235-1238`).
If left as is, `rustdesk://` links would open our app and then be ignored, and `bravetel-support://` would open nothing.
**Change** the scheme to `bravetel-support` and the URL name to the bundle id.

### 1.5 Keep `ORG = com.carriez`

`ORG` feeds `get_full_name()` (`common.rs:1240-1247`) and the config dir. The plist paths are hard-coded `com.carriez.{}`
(`macos.rs:399`, `403`, `1229-1230`, `1362-1363`), and so is `install.scpt:3` (rewritten only for the `RustDesk` part).
Changing `ORG` would make `is_installed_daemon()` look for `com.bravetel.*` plists while `write_plists()` writes `com.carriez.*`,
so the daemon would never count as installed. The `com.carriez.` prefix is visible only in `launchctl list` and the file names.

### 1.6 Not used by the Flutter macOS build

- `Cargo.toml:281-285` `[package.metadata.bundle]`: only for `cargo bundle` (sciter path, `build.py:1108-1114`). Skip.
- `res/osx-dist.sh` and `build.py:1110-1145`: sciter or manual flows. Skip.
- The `create-dmg` call inside `build.py:950-953` is inside a `'''` string (dead). CI runs create-dmg itself (`flutter-build.yml:1133-1139`).

---

## 2. Icons

### 2.1 Files

| Target | Current | Action | Used by |
|---|---|---|---|
| `flutter/macos/Runner/AppIcon.icns` | `ic13`, `ic11`, `ic04`, `ic07` (parsed) | **Regenerate** | `CFBundleIconFile` (`Info.plist:9-10`), bundled as a resource (`project.pbxproj:28`, `76`, `257`) |
| `flutter/assets/icon.png` | already branded (Windows step) | keep | in-app icon (`flutter/lib/common.dart:3864-3871`); **also the macOS tray override**, see 2.3 |
| `res/mac-tray-dark-x2.png` | 60x60 template | **Replace** with a branded template | compiled-in tray icon (`src/tray.rs:44-47`) |
| `flutter/assets/mac-tray.png` (new) | absent | **Add** (same bytes as above) | tray asset after edit M7 (`src/tray.rs:306-307`) |
| `Assets.xcassets/AppIcon.appiconset` | does not exist (`ls`) | none | `ASSETCATALOG_COMPILER_APPICON_NAME` is set (`project.pbxproj:430`, `576`, `606`) but no catalog ships |
| `res/mac-tray-light-x2.png`, `res/mac-icon.png` | | skip | no code reference (grep) |
| `res/32x32.png`, `128x128*.png` | | skip | `cargo bundle` only (`Cargo.toml:284`) |
| DMG volume icon | create-dmg default | optional `--volicon` with `AppIcon.icns` | |

### 2.2 `.icns` from Pillow (works on Windows, no `iconutil` needed)

Tested locally with Pillow 13.0.0: `Image.save("AppIcon.icns")` from a 1024 RGBA writes a TOC plus `ic07`-`ic14` (16 to 1024, retina pairs) and reopens cleanly.
The brand icon is full bleed: alpha bbox `(0,0,1024,1024)`, 92.6% opaque.
Apple's macOS icon grid draws the shape at about 824/1024 with transparent margin (secondary source, Apple HIG; not source-verified). Without that margin the icon looks oversized in Finder and the Dock. Add to `branding/make_icons.py`:

```python
from PIL import Image, ImageChops
# macOS app icon: pad to the ~824px icon grid, Pillow writes ic07..ic14
canvas = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
body = icon.resize((824, 824), Image.LANCZOS)
canvas.paste(body, (100, 100), body)
canvas.save(out / "AppIcon.icns")

# macOS tray: template image (alpha only). Use the white "B" glyph of the icon, not the blue square.
r, g, b, a = icon.split()
mask = ImageChops.multiply(ImageChops.darker(ImageChops.darker(r, g), b).point(lambda v: 255 if v > 200 else 0), a)
glyph = Image.new("RGBA", icon.size, (0, 0, 0, 0)); glyph.putalpha(mask)
glyph = glyph.crop(mask.getbbox())
side = max(glyph.size); sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
sq.paste(glyph, ((side - glyph.width) // 2, (side - glyph.height) // 2))
sq.resize((44, 44), Image.LANCZOS).save(out / "mac-tray.png")  # 22pt @2x
```

Tested: the glyph mask is 26.8% of the canvas (the "B") and the preview reads clearly. `bravetel-mark.svg` exists in the brand folder but Pillow cannot rasterise SVG.
Optional CI check on the runner: `iconutil -c iconset flutter/macos/Runner/AppIcon.icns -o /tmp/x.iconset` must succeed. Generating the `.icns` on the runner with `iconutil -c icns` is an alternative, but it is not required.

### 2.3 Tray icon gotcha (must fix)

On macOS the tray uses `load_icon_from_asset()` first and falls back to the compiled-in `res/mac-tray-dark-x2.png` (`tray.rs:53-56`).
The asset path is `.../flutter_assets/assets/icon.png` (`tray.rs:306-307`), which our Windows branding fills with the colour icon.
The icon is set as a template (`tray.rs:161-164`), so macOS draws only its alpha channel, and our opaque rounded square would show as a solid blob.
Fix: edit M7 points the macOS asset path at `assets/mac-tray.png`. Copy the glyph to that file and to `res/mac-tray-dark-x2.png`.

---

## 3. Unattended agent vs QuickSupport on macOS

### 3.1 How "install" works on macOS

- There is no installer and no CLI install. "Installed" means the bundle sits at `/Applications/Bravetel-Support.app` (`macos.rs:933-941`), normally dragged there from the DMG.
- `--install-service` on macOS only **checks**: `install_service()` returns `is_installed_daemon(false)` (`core_main.rs:373-376`, `macos.rs:219-221`). It installs nothing.
- The daemon and agent are installed from the GUI card "install_daemon_tip". It shows only when the app is installed, the service is not stopped, and the daemon is missing (`flutter/lib/desktop/pages/desktop_home_page.dart:501-507`). The card calls `is_installed_daemon(true)`, which runs `install.scpt` through `osascript` with an admin prompt (`macos.rs:243-288`). That writes the LaunchDaemon (`service`, root, KeepAlive) and the LaunchAgent (`--server`, `LimitLoadToSessionType` LoginWindow + Aqua), copies the user's toml files to `/var/root`, and bootstraps the daemon (`install.scpt:3-19`; `daemon.plist`; `agent.plist:11-15`).
- Login window access: the agent runs in the LoginWindow session (`agent.plist:13`), and the Release link flags embed `__CGPreLoginApp` (`project.pbxproj:624-627`).
- Uninstall: `uninstall.scpt:1-6` via `uninstall_service()` (`macos.rs:424-486`), triggered by "Stop service" (`ui_interface.rs:470-475`; hidden for us by `hide-stop-service`).
- Password: `sudo /Applications/Bravetel-Support.app/Contents/MacOS/Bravetel-Support --password <pw>` needs installed + root (`core_main.rs:425-444`, `macos.rs:834-836`). It is routed to the user's `--server` IPC (`core_main.rs:221-233`, `868-880`), so the agent must be running (a user logged in). End to end UNVERIFIED.
- Scripted or MDM alternative (UNVERIFIED end to end): copy the bundle to /Applications, run `sudo .../Contents/MacOS/service --write-plists` (`service.rs:10-15` -> `macos.rs:397-422`), then `launchctl bootstrap system /Library/LaunchDaemons/com.carriez.Bravetel-Support_service.plist` and `launchctl bootstrap gui/<uid> /Library/LaunchAgents/com.carriez.Bravetel-Support_server.plist` (same commands as `install.scpt:15`, `update.scpt:50`). Unlike `install.scpt:11-13` this skips the prefs copy to `/var/root`; whether the daemon needs it is UNVERIFIED.

### 3.2 Permissions (TCC)

The home page asks in this order (`desktop_home_page.dart:477-507`):
1. Screen Recording (`config_screen`; `IsCanScreenRecording`/CGWindowList check `macos.rs:152-217`; opens the System Settings pane, `:483-486`).
2. Accessibility (`config_acc`; `AXIsProcessTrustedWithOptions` `macos.rs:128-143`).
3. Input Monitoring (`config_input`; `macos.rs:145-150`).
4. Then the daemon install card.

The microphone is requested on demand (`Info.plist:44-45`; entitlement `Release.entitlements` `audio-input`).
Grants attach to the code identity of the process doing the work. Here that is the main exe running as the `--server` agent: capture and input run in the server (`core_main.rs:403-408`).

### 3.3 `hide-help-cards` must be Windows only

`buildInstallCard()` returns nothing when builtin `hide-help-cards=Y` unless the card is `install_daemon_tip` (`desktop_home_page.dart:585-588`).
On macOS that **hides all three permission cards**, so users get no prompt to grant Screen Recording, Accessibility or Input Monitoring.
Our Windows hook sets it (`apply_branding.py:81`). Make it `#[cfg(not(target_os = "macos"))]` (5.2).

### 3.4 QuickSupport on macOS

- `is_bravetel_quick_support()` is `#[cfg(windows)]` (`apply_branding.py:87-109`). It matches the Windows exe or packer name (`RUSTDESK_APPNAME`, `common.rs:54`). On macOS there is no packer and no portable service: `core_main.rs:161-169` and `192-203` are Windows only.
- Native QS behaviour already exists on macOS: if the bundle is not at `/Applications/Bravetel-Support.app`, it is not installed. The daemon card never shows (`desktop_home_page.dart:503`), and the GUI starts the server in process when no agent is running (`core_main.rs:208-219`; `src/server.rs:774-781`). That gives user-session support while the app is open: no login window, no reboot persistence.
- HARD `disable-installation` has no effect on macOS UI. The macOS card branch ignores it (`desktop_home_page.dart:461` checks it only for Windows), and it only filters `--install` (`core_main.rs:138-150`).
- **Phase 1 (recommended):** one DMG per arch. Agent: drag to Applications, grant permissions, click Install. QS: open the DMG and run the app from the DMG window. Gatekeeper App Translocation runs it read-only, which is fine for QS. No Rust change.
- **Phase 2 (optional):** a second DMG per arch from the **same build**, with the bundle folder renamed `Bravetel-Support-QS.app`. The folder name is not part of the code seal (UNVERIFIED for the ad hoc case; check `codesign --verify` after the rename). It is never "installed" because the `starts_with` test needs `/Applications/Bravetel-Support.app` (`macos.rs:938`). Detect it on macOS and add HARD `conn-type=incoming` for the compact window (`config.rs:2869-2875` per PLAN.md 2.6; visual result UNVERIFIED). Code in 5.2.
- Running QS on a Mac that also has the agent installed shares the IPC path (`/tmp/Bravetel-Support-<uid>`). The mac IPC executable checks (`ipc/auth.rs:470-493`, `575-593`) may reject the QS exe. UNVERIFIED; advise not to mix them.

---

## 4. CI: `.github/workflows/bravetel-macos.yml` (unsigned, ad hoc)

Versions from `flutter-build.yml`:
- Rust: `MAC_RUST_VERSION 1.81` (`:26`, used `:1050`).
- Flutter: x86_64 `FLUTTER_VERSION 3.24.5` (`:31`), arm64 `FLUTTER_MACOS_ARM_VERSION 3.44.9` (`:42`, chosen at `:1013`).
- Bridge: Flutter `3.22.3` -> `bridge-artifact`, and `3.44.8` -> `bridge-artifact-flutter-3.44` (`bridge.yml:20-35`).
- `VCPKG_COMMIT_ID 9e593bb...` (`:53`). Triplets are auto-detected: `x64-osx` / `arm64-osx` (`:932`, `:940`; the install step passes no `--triplet`, `:1077-1091`).
- LLVM from `brew install llvm create-dmg` (`:990`); `LLVM_VERSION` is not used on mac. NASM 2.16.03 (`:998-1007`).
- Minimum macOS: arm64 12.3 via sed (`:1105-1111`), x86_64 10.14 (`build.py:936-938`). arm64 adds `--screencapturekit` (`:937-938`).

```yaml
name: Bravetel macOS (unsigned)
on: { workflow_dispatch: {} }        # macOS minutes: dispatch only at first; add bravetel-* tags later
concurrency: { group: bravetel-macos-${{ github.ref }}, cancel-in-progress: true }
permissions: { contents: read }
env:
  MAC_RUST_VERSION: "1.81"
  FLUTTER_VERSION: "3.24.5"
  FLUTTER_MACOS_ARM_VERSION: "3.44.9"
  VCPKG_BINARY_SOURCES: "clear;x-gha,readwrite"
  VCPKG_COMMIT_ID: "9e593bb18ea69cc5095e012465dcd675a822ed0d"
  VERSION: "1.5.3"
  APP: "Bravetel-Support"
jobs:
  generate-bridge:
    uses: ./.github/workflows/bridge.yml          # unbranded is fine: branding does not touch src/flutter_ffi.rs
  build-macos:
    needs: [generate-bridge]
    runs-on: ${{ matrix.job.os }}
    strategy: { fail-fast: false, matrix: { job: [
      { target: x86_64-apple-darwin,  os: macos-15-intel, arch: x86_64,  extra-build-args: "" },
      { target: aarch64-apple-darwin, os: macos-15,       arch: aarch64, extra-build-args: "--screencapturekit" } ] } }
    steps:
      - Export ACTIONS_CACHE_URL/RUNTIME_TOKEN          # :943-948
      - Checkout, submodules: recursive                 # :950-953
      - Apply branding: python3 branding/apply_branding.py   # NEW, before any build step
      - brew install llvm create-dmg (+pkg-config)      # :988-996
      - Install NASM 2.16.03                            # :998-1007
      - Install flutter (arch-dependent version)        # :1009-1013
      - if arm64: flutter config --no-enable-swift-package-manager   # :1015-1019
      - if x86_64: Patch flutter (dropdown diff)        # :1021-1028
      - Workaround for flutter issue (sed binding.dart) # :1030-1036
      - if arm64: gnu-sed + .github/patches/apply_flutter_3.44_source_patches.sh   # :1038-1045
      - Rust ${{ env.MAC_RUST_VERSION }} + target, rustfmt; Swatinem/rust-cache   # :1047-1056
      - Restore bridge (3.44 artifact on arm64)         # :1058-1063
      - lukka/run-vcpkg + vcpkg install                 # :1071-1091
      - Build: arm64 min-version seds, then ./build.py --flutter --hwcodec --unix-file-copy-paste ${{ matrix.job.extra-build-args }}   # :1103-1113
      - Ad hoc re-sign + verify + smoke (NEW):
          APPDIR=./flutter/build/macos/Build/Products/Release/$APP.app
          bash ./.github/scripts/sign-macos-app.sh "$APPDIR" - ./flutter/macos/Runner/Release.entitlements
          test "$("$APPDIR/Contents/MacOS/$APP" --version)" = "$VERSION"
          test "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$APPDIR/Contents/Info.plist")" = com.bravetel.support
          test -x "$APPDIR/Contents/MacOS/service"
      - create-dmg (patched unmount retries, :1136-1138):
          create-dmg --volname "Bravetel Support" --volicon flutter/macos/Runner/AppIcon.icns \
            --icon "$APP.app" 200 190 --hide-extension "$APP.app" --window-size 800 400 \
            --app-drop-link 600 185 bravetel-support-$VERSION-${{ matrix.job.arch }}.dmg "$APPDIR"
      - upload-artifact bravetel-support-macos-${{ matrix.job.arch }} (the .dmg only; a zipped .app breaks symlinks, :1146)
```

Why re-sign: Xcode ad hoc signs the bundle (`CODE_SIGN_IDENTITY "-"`, `project.pbxproj:609`). Then `build.py:949` copies `service` into `Contents/MacOS`, which breaks the seal.
`sign-macos-app.sh` accepts `-` (`:9-12`), signs the frameworks, `service` and then the app with entitlements, and verifies `--deep --strict` (`:14-34`).
Apple Silicon refuses to run unsigned arm64 code, so ad hoc signing is the floor (Apple platform rule, secondary source).
Ad hoc + hardened runtime (`--options runtime`, `:9`; `ENABLE_HARDENED_RUNTIME` `project.pbxproj:613`) matches upstream's own unsigned DMG. That it launches on a clean Mac is UNVERIFIED for our build.

Dropped upstream steps:

| Upstream | Lines | Secret / reason |
|---|---|---|
| Import the codesign cert, Check sign key | 955-967 | `MACOS_P12_BASE64`, `MACOS_P12_PASSWORD` (`apple-actions/import-codesign-certs`, keychain `rustdesk`) |
| Import notarize key | 969-976 | `MACOS_NOTARIZE_JSON` (base64 rcodesign App Store Connect API key JSON -> `rustdesk.json`) |
| Install rcodesign 0.22.0 | 978-986 | signing only |
| Run the Dart tests / Rust tests / Test verified updates | 1065-1069, 1115-1131 | time; update metadata only |
| Codesign app and create signed dmg | 1148-1175 | `MACOS_P12_PASSWORD`, `MACOS_CODESIGN_IDENTITY` (value carries its own shell quoting, `:1160`), notarize with `rcodesign notary-submit --staple` (`:1175`) |
| Upload signed DMG, Publish DMG (`nightly`), `publish-signed-update-metadata`, `publish_unsigned` | 1189-1205, 1206+, 1341+ | upstream release flow |

Signing later (phase 2), keeping upstream secret names. Gate every step on `env.MACOS_P12_BASE64 != ''`, as upstream gates on `!= null` (`:956`):
- `MACOS_P12_BASE64`: base64 of the "Developer ID Application" certificate + private key (.p12).
- `MACOS_P12_PASSWORD`: .p12 password (also unlocks the keychain, `:1157`).
- `MACOS_CODESIGN_IDENTITY`: e.g. `"Developer ID Application: <Bravetel legal entity> (<TEAMID>)"`, quotes included.
- `MACOS_NOTARIZE_JSON`: base64 of the JSON from `rcodesign encode-app-store-connect-api-key` (issuer id, key id, .p8). rcodesign docs, secondary source.
- Replace the ad hoc step with `sign-macos-app.sh "$APPDIR" ${{ secrets.MACOS_CODESIGN_IDENTITY }} ...` (it adds `--timestamp`, `:10-12`), then create-dmg, `codesign` the DMG and `rcodesign notary-submit --staple` (`:1161-1175`).
- Bravetel needs an Apple Developer Program membership (organisation enrolment), a Developer ID Application certificate, and an App Store Connect API key. Enrolment prerequisites and cost: check with Apple (not verified here).
- Optional: set `DEVELOPMENT_TEAM` (`project.pbxproj:436`, `582`, `612`, RustDesk's `HZF9JMC8YN`) to Bravetel's team. Not needed while CI re-signs with an explicit identity (UNVERIFIED).

Runtime estimate (UNVERIFIED, no run yet): bridge 10-20 min in parallel; each mac job first run 60-100 min (vcpkg builds ffmpeg/aom/libvpx from source); warm cache 30-50 min. Jobs run in parallel, so expect about 1.5-2 h wall clock on the first run.
`macos-15-intel` availability over time follows GitHub's runner image lifecycle (UNVERIFIED). Drop x86_64 if Intel Macs are not in the fleet.
Free macOS minutes assume the fork is public (UNVERIFIED).

---

## 5. `apply_branding.py` changes

The script is shared by both workflows. All edits below are inert on Windows: those files are not compiled there, or the line is `#[cfg(target_os = "macos")]`.
`read_text()` normalises CRLF, so the anchors work on both runners.

### 5.1 New `edit()` / `copy()` calls

```python
BUNDLE_ID = "com.bravetel.support"   # never change after rollout; must not contain "rustdesk" (macos.rs:367-370)
URI_SCHEME = APP_NAME.lower()        # "bravetel-support", must match get_uri_prefix (common.rs:1235-1238)

# M1/M2 bundle name = APP_NAME (hard requirement), keep the Swift module name the xib binds to
xc = "flutter/macos/Runner/Configs/AppInfo.xcconfig"
edit(xc, "PRODUCT_NAME = RustDesk", f"PRODUCT_NAME = {APP_NAME}\nPRODUCT_MODULE_NAME = RustDesk")
edit(xc, "PRODUCT_BUNDLE_IDENTIFIER = com.carriez.flutterHbb", f"PRODUCT_BUNDLE_IDENTIFIER = {BUNDLE_ID}")
# M3 effective bundle id (Profile, Debug, Release target overrides)
edit("flutter/macos/Runner.xcodeproj/project.pbxproj",
     "PRODUCT_BUNDLE_IDENTIFIER = com.carriez.rustdesk;", f"PRODUCT_BUNDLE_IDENTIFIER = {BUNDLE_ID};", count=3)
# M4/M5 URL type
pl = "flutter/macos/Runner/Info.plist"
edit(pl, "<string>com.carriez.rustdesk</string>", f"<string>{BUNDLE_ID}</string>")
edit(pl, "<string>rustdesk</string>", f"<string>{URI_SCHEME}</string>")
# M6 build.py copies the service binary into the bundle by name
edit("build.py", "./build/macos/Build/Products/Release/RustDesk.app/Contents/MacOS/",
     f"./build/macos/Build/Products/Release/{APP_NAME}.app/Contents/MacOS/")
# M7 macOS tray: template glyph, not the colour icon.png
edit("src/tray.rs", '"../Frameworks/App.framework/Resources/flutter_assets/assets/icon.png"',
     '"../Frameworks/App.framework/Resources/flutter_assets/assets/mac-tray.png"')

copy("AppIcon.icns", "flutter/macos/Runner/AppIcon.icns")
copy("mac-tray.png", "res/mac-tray-dark-x2.png", "flutter/assets/mac-tray.png")
```

Match counts were checked on the current tree: M1 1, M2 1, M3 3, M4 1, M5 1, M6 1, M7 1.
Optional: leave `PRODUCT_COPYRIGHT` (`AppInfo.xcconfig:14`) as the upstream notice (AGPL, see PLAN.md R11).

### 5.2 `BRANDING_RS` changes (Rust appended to `src/common.rs`)

1. Remove `keys::OPTION_HIDE_HELP_CARDS,` from the builtin loop (`apply_branding.py:81`) and add after the loop:
   ```rust
   // macOS: this would also hide the Screen Recording / Accessibility / Input Monitoring cards
   // (desktop_home_page.dart:585-588), leaving users no way to grant them.
   #[cfg(not(target_os = "macos"))]
   b.insert(keys::OPTION_HIDE_HELP_CARDS.to_owned(), "Y".to_owned());
   ```
2. Phase 2 only (QS DMG). Change the hook's gate from `#[cfg(windows)]` to `#[cfg(any(windows, target_os = "macos"))]` and add:
   ```rust
   #[cfg(target_os = "macos")]
   fn is_bravetel_quick_support() -> bool {
       // QS DMG ships the same bundle renamed "Bravetel-Support-QS.app"; the agent keeps "Bravetel-Support.app".
       std::env::current_exe().ok().map_or(false, |p| {
           p.ancestors().any(|a| {
               a.extension().map_or(false, |e| e == "app")
                   && a.file_stem().map_or(false, |n| n.to_string_lossy().to_lowercase().contains("-qs"))
           })
       })
   }
   ```
   Inside the QS branch on macOS, add HARD `conn-type=incoming` if wanted. `disable-installation` is harmless there but does nothing on macOS (3.4).
3. No other Rust changes are needed for macOS. `allow-auto-update=N` (overwrite) and `is_custom_client()` both block the root silent updater that `start_os_service()` starts (`macos.rs:858-866`; `src/updater.rs:474-525`, gates at `:518-525`). The macOS "Auto update" checkbox is already hidden for custom clients (`desktop_setting_page.dart:527-528`). H1 (`get_license_from_exe_name`) is Windows only. The Flutter 3.44 patch script edits only `flutter/lib/common.dart` and `pubspec.yaml` (`apply_flutter_3.44_source_patches.sh:127-135`), so it does not collide with our Dart edits.

Then run `cargo check` on a Mac or in CI. Compile status of 5.2 is UNVERIFIED.

### 5.3 `make_icons.py`

Add the two blocks from 2.2, regenerate, and commit `branding/assets/AppIcon.icns` and `branding/assets/mac-tray.png`.

---

## 6. Risks

- **R1 TCC grants are tied to the code identity.** With ad hoc signing the designated requirement is the cdhash (Apple code signing behaviour, secondary source), so every new build likely needs Screen Recording, Accessibility and Input Monitoring granted again (UNVERIFIED). Moving from ad hoc to Developer ID invalidates them once more. Grants made to stock RustDesk (`com.carriez.rustdesk`) never carry over. Reset with `tccutil reset All com.bravetel.support` (pattern at `macos.rs:158`).
- **R2 Gatekeeper on unsigned builds.** A downloaded, quarantined, un-notarised app is blocked. On macOS 15 the Control-click Open bypass is gone; the user must try to open it, then go to System Settings > Privacy & Security > Open Anyway (admin), or run `xattr -dr com.apple.quarantine /Applications/Bravetel-Support.app` (Apple macOS 15 behaviour, secondary source, UNVERIFIED on our build). Fine for a pilot; plan Developer ID + notarisation before fleet rollout.
- **R3 Bundle id is permanent.** TCC, the launchd `AssociatedBundleIdentifiers`, the update identity checks (`macos.rs:74`, `1200-1205`) and any MDM PPPC profile bind to it. It must not contain `rustdesk` (`macos.rs:367-370`).
- **R4 `PRODUCT_NAME` != `APP_NAME` breaks install** (1.2). This includes case on case-sensitive volumes. The `.app` must live exactly at `/Applications/Bravetel-Support.app`; `~/Applications` or a renamed copy counts as not installed (`macos.rs:938`).
- **R5 Help-cards regression** if 5.2 item 1 is skipped (3.3).
- **R6 Tray blob** if M7 and the template asset are skipped (2.3).
- **R7 Xib module binding** (1.2): pinning `PRODUCT_MODULE_NAME` avoids it. Verify the app shows its window on the first run.
- **R8 Unattended deploy needs a human at the Mac** for TCC. PPPC can pre-approve Accessibility but not Screen Recording, and needs a signed build with a code requirement (Apple MDM docs, secondary source, UNVERIFIED). The daemon card needs an admin password (`install.scpt:19`).
- **R9 macOS 15+ recurring Screen Recording re-consent** prompts for apps on legacy capture APIs. The x86_64 build lacks `screencapturekit` (`flutter-build.yml:928-930` vs `937-938`). Secondary source, UNVERIFIED.
- **R10 Login Items (macOS 13+):** the LaunchAgent and Daemon appear under System Settings > General > Login Items and a user can switch them off, which kills unattended access. How an unsigned item is labelled there is UNVERIFIED.
- **R11 Two Flutter versions:** x86_64 3.24.5, arm64 3.44.9 with on-the-fly source patches (`flutter-build.yml:36-42`). Any future Dart branding edit must match both states.
- **R12 Existing stock RustDesk on a Mac:** it uses different labels and paths, so both daemons could run side by side. Uninstall stock first. ID reuse and hbbs key behaviour: see PLAN.md section 4 (UNVERIFIED).
- **R13 Supply chain:** NASM zip and rcodesign tarball are downloaded without checksum (`flutter-build.yml:983`, `1004`); `brew` is unpinned.
- **R14 Licence:** keep the upstream copyright (`AppInfo.xcconfig:14`) and publish the `bravetel` source (AGPL-3.0, PLAN.md R11).

## 7. Console impact (rustdesk-app), for later

- macOS install steps for technicians: open the DMG, drag to Applications, grant 3 permissions, click Install (admin), set the password in the GUI or with `sudo .../Bravetel-Support --password` (3.1).
- Deep link `bravetel-support://` on macOS once the technician runs the branded build (1.4).
- QS download per arch (phase 1: the same DMG; phase 2: `bravetel-support-qs-<ver>-<arch>.dmg`).
