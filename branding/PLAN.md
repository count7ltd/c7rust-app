# Bravetel Support: branded Windows x64 client, build plan

As of 2026-11-13. Source read: fork `shadikur/rustdesk` master `e7bacd0` (Cargo `1.5.3`), submodule
`libs/hbb_common` at `fae47e0`. All `file:line` refs are to that tree. `UNVERIFIED` marks anything not
confirmed from source or by a run.

---

## 0. One decision needed first: the internal app name

`APP_NAME` is not just a label. It is the service name, IPC pipe, config dir, registry keys, install dir,
installed exe name and URI scheme:

- service: `sc create {app_name} ...` unquoted (`src/platform/windows.rs:4078-4083`, `4101-4102`, `3622`, `4036`); dispatcher registers `get_app_name()` (`windows.rs:553`, `673`)
- pipe: `\\.\pipe\{APP_NAME}\query{postfix}` (`libs/hbb_common/src/config.rs:1003-1011`)
- config file/dir: `{APP_NAME}.toml` under `ProjectDirs::from("", "", APP_NAME)` (`config.rs:878-881`, `920-938`)
- install dir `%ProgramFiles%\{APP_NAME}`, installed exe `{InstallLocation}\{APP_NAME}.exe` (`windows.rs:1433-1447`, `1495-1507`); `is_installed()` = that exe exists (`windows.rs:1997-2000`)
- HKCR ext + URL protocol `.{app_name lowercase}` unquoted in `reg add` (`windows.rs:1573`, `1603-1618`, `1856-1857`); URI prefix `{app_name lowercase}://` (`src/common.rs:1236-1238`)
- `taskkill /F /IM {app_name}.exe` (`windows.rs:1855`, `3393`, `3428`, `3655`)
- MSI build looks for `<dist>\{app-name}.exe` and runs it via an unquoted shell string (`res/msi/preprocess.py:464-470`, `165`)
- Upstream note: "app_name only contains alphanumeric and hyphen" (`src/lang.rs:289`)

**Conclusion: "Bravetel Support" (with a space) is NOT safe as `APP_NAME`.** It breaks the unquoted `sc`/`reg`/
`taskkill` scripts and the URI scheme. The visible title, tray, Start menu, ARP entry and service display
name all come from `APP_NAME` (`flutter/windows/runner/main.cpp:87-97`, `176-180`; `src/tray.rs:83-93`;
`windows.rs:1679-1687`, `1784`, `4101`), and translations swap "RustDesk" for `APP_NAME` (`src/lang.rs:274-296`).

| Option | APP_NAME | Exe on disk | Visible as | Notes |
|---|---|---|---|---|
| A (recommended) | `Bravetel-Support` | `bravetel-support.exe` | Bravetel-Support | Matches requested exe name. Windows paths are case-insensitive, so lowercase file matches `Bravetel-Support.exe` (`windows.rs:1505`, `4353`; `preprocess.py:165`). URI `bravetel-support://` is a valid scheme. |
| B | `BravetelSupport` | `bravetelsupport.exe` | BravetelSupport | No hyphen. |
| C | `Bravetel Support` | n/a | Bravetel Support | Unsafe, see above. Needs patches to every unquoted script line. Not recommended. |

The true string "Bravetel Support" (with space) is used only where it is pure metadata (exe version info,
packer version info). The rest of this plan assumes **Option A**. Swap the string if B is chosen.

---

## 1. Base version

- Upstream tag `1.5.3` = `95cca3f` (lightweight tag; `git ls-remote https://github.com/rustdesk/rustdesk refs/tags/1.5.3`). The fork has no `1.5.3` tag (`git ls-remote origin` returned nothing).
- master `e7bacd0` is 20 commits ahead of `1.5.3`, 0 behind, 35 files (GitHub compare API). Mostly
  translations, docs, CI runner bumps, plus: clipboard file sizes (`libs/clipboard/src/windows/wf_cliprdr.c`),
  Linux uinput, incoming-only quit button text (`0bfe22083d`), vcpkg mfx-dispatch patch vendored
  (`2fe026917d`, avoids HTTP 429 fetching a patch during vcpkg), lang fix spelling RustDesk in 5 locales (`53a1e8aea4`, relevant
  because the brand swap matches the literal "RustDesk", `src/lang.rs:274-276`). hbb_common pin unchanged.
- **Recommendation:** branch `bravetel` from tag `1.5.3` (released, tested) and cherry-pick `2fe026917d`
  (CI reliability) and `53a1e8aea4` (brand swap in translations). Both report version `1.5.3`. Basing on
  master `e7bacd0` is an acceptable fallback (low-risk delta), but pins an untagged Windows clipboard change.
- Keep the fork's `master` equal to upstream; do all branding on `bravetel`.

---

## 2. Edits

Approach: branding lives in the fork as (a) committed assets under `branding/assets/`, (b) one script
`branding/apply_branding.py` that performs exact-string replacements and asserts each match count == 1, run
in CI before the build. This keeps source diffs out of upstream files and fails loudly on upstream drift.
No change to `libs/hbb_common` (no submodule fork needed).

### 2.1 Name

| # | File | Edit | Why |
|---|---|---|---|
| N1 | `src/common.rs:2509` | `pub fn load_custom_client() {` -> `pub fn load_custom_client() {\n    apply_bravetel_branding();` and append the function in 2.3 | Runtime `APP_NAME` set at the same point upstream's own custom.txt sets it (`common.rs:2627-2631`). Runs first in `core_main` (`src/core_main.rs:45-49`) and flutter init (`src/flutter_ffi.rs:50-55`). The service (`--service`) and every helper process enter through `core_main` via the runner (`main.cpp:30-58`). |
| N2 | `flutter/windows/runner/Runner.rc:93` | `"RustDesk Remote Desktop"` -> `"Bravetel Support"` | Exe FileDescription |
| N3 | `Runner.rc:95` | `VALUE "InternalName", "rustdesk"` -> `"bravetel-support"` | |
| N4 | `Runner.rc:97` | `"rustdesk.exe"` -> `"bravetel-support.exe"` | OriginalFilename |
| N5 | `Runner.rc:98` | `VALUE "ProductName", "RustDesk"` -> `"Bravetel Support"` | |
| N6 | `Runner.rc:92` | CompanyName `"Purslane Tech Pte. Ltd."` -> `<Bravetel legal entity>` | Value TBD by user. Leave `LegalCopyright` (`Runner.rc:96`) as is or append, see Risks R11. |
| N7 | `libs/portable/Cargo.toml:31-33` | `ProductName = "RustDesk"` -> `"Bravetel Support"`; `OriginalFilename = "rustdesk.exe"` -> `"bravetel-support.exe"`; `FileDescription = "RustDesk Remote Desktop"` -> `"Bravetel Support"` | Version info of the downloadable self-extracting exe (winres in `libs/portable/build.rs`). |
| N8 | CI, after build | `Move-Item rustdesk\rustdesk.exe rustdesk\bravetel-support.exe` | Keep `BINARY_NAME "rustdesk"` (`flutter/windows/CMakeLists.txt:7`). Upstream renames the exe the same way for its MSI template (`.github/workflows/flutter-build.yml:524`). No Rust code hardcodes `rustdesk.exe` for the Flutter build (only sciter path `windows.rs:1251`). |
| N9 | MSI (optional) | `preprocess.py ... --app-name Bravetel-Support -m "<Manufacturer>"` | Product name, UpgradeCode, langs, license derive from `--app-name` (`preprocess.py:84`, `246-254`, `273-279`, `500-509`). |
| skip | `Cargo.toml:261-265` winres | Only used by the sciter `inline` build (`build.rs:31-35` is `#[cfg(all(windows, feature = "inline"))]`). Optional for consistency. |
| skip | `flutter/pubspec.yaml:1` `flutter_hbb` | Not user-visible on Windows. Renaming breaks Dart imports. |
| keep | `librustdesk.dll`, `RuntimeBroker_rustdesk.exe`, `drivers\RustDeskPrinterDriver`, IPC/service derived names | Loaded by fixed name (`main.cpp:30`; `src/privacy_mode/win_topmost_window.rs:33`; `res/msi/CustomActions/RemotePrinter.cpp:25-27`). Upstream template comment says these must never be renamed (`flutter-build.yml:512-514`). |

Safe vs breaking summary: safe = anything derived from `APP_NAME` at runtime when `APP_NAME` has no space
(service, pipe, config dir, reg keys, shortcuts, URI scheme all follow automatically). Breaking = a space in
`APP_NAME`; renaming `librustdesk.dll`; renaming the exe to a stem that differs from `APP_NAME` once installed
(install/`is_installed`/MSI all assume `{APP_NAME}.exe`).

### 2.2 Icons

Source: `C:\Users\Shadikur\workspace\fusionpbx-automation\brand\exports\bravetel-icon-1024.png` (1024x1024 RGBA, checked).
Generate once locally with Pillow (installed, 13.0.0), commit outputs under `branding/assets/`, and have
`apply_branding.py` copy them into place.

| Target | Current | Generate | Used by |
|---|---|---|---|
| `flutter/windows/runner/resources/app_icon.ico` | 48 only | 16,20,24,32,40,48,64,128,256 | Exe icon (`Runner.rc:55`) |
| `flutter/assets/icon.ico` (new) | absent | same as above | Window/taskbar icon at runtime (`flutter/windows/runner/win32_window.cpp:22-40`); shortcut + ARP DisplayIcon for custom clients (`windows.rs:2284-2300`, `1672`, `1783`). Bundled because pubspec ships `assets/` (`flutter/pubspec.yaml:158-159`). |
| `flutter/assets/icon.png` (new) | absent (svg fallback) | 256x256 | In-app icon (`flutter/lib/common.dart:3864-3871`); tray icon override, takes precedence over the ico (`src/tray.rs:53-56`, `301-317`) |
| `res/tray-icon.ico` | 32 | 16,20,24,32,48 | Compiled-in tray fallback (`src/tray.rs:50`) |
| `res/icon.ico` | 16,32,48,64,128 | 16,24,32,48,64,128,256 | Self-extracting packer exe icon (`libs/portable/build.rs` `set_icon("../../res/icon.ico")`); MSI icon (`preprocess.py:450-456`) |
| `flutter/assets/logo_light.png`, `logo_dark.png` (new, optional) | absent | from `bravetel-logo-light-1600.png` / `-dark-1600.png` (1600x489) scaled to 600x183 | Home page logo, max 300x60 box (`common.dart:3797-3860`). Light theme loads `logo_light.png`, dark loads `logo_dark.png` (`common.dart:3801-3805`). Which brand file suits which theme: UNVERIFIED, check visually. |
| not needed on Windows | `res/icon.png`, `res/32x32.png`, `64x64`, `128x128`, `128x128@2x`, `res/mac-*.png`, `res/*.svg` | optional | Linux/macOS packaging (`build.py:756`, `864`) |
| leave | `flutter/assets/icon.svg` | optional | Fallback only when `icon.png` is missing (`common.dart:3867-3870`) |
| leave | `libs/portable/src/res/label.png` | n/a | Packer splash label (`libs/portable/src/ui.rs:6`). Content UNVERIFIED (renders blank in preview, likely white text). |

```python
# branding/make_icons.py (run locally, commit outputs)
from PIL import Image
src = Image.open(r"...\bravetel-icon-1024.png").convert("RGBA")
ico = [(s, s) for s in (16, 20, 24, 32, 40, 48, 64, 128, 256)]
src.save("branding/assets/app_icon.ico", sizes=ico)          # -> runner/resources/app_icon.ico and flutter/assets/icon.ico
src.save("branding/assets/icon.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])  # -> res/icon.ico
src.save("branding/assets/tray-icon.ico", sizes=[(s, s) for s in (16, 20, 24, 32, 48)])       # -> res/tray-icon.ico
src.resize((256, 256), Image.LANCZOS).save("branding/assets/icon.png")                         # -> flutter/assets/icon.png
```

### 2.3 Baked server config (compile-time, no custom.txt)

Why not the upstream mechanisms:
- `custom.txt` must be signed with RustDesk's key `5Qbwsde3...` (`src/common.rs:2607-2620`). Not usable.
- `RENDEZVOUS_SERVERS` / `RS_PUB_KEY` consts (`config.rs:116-117`) live in the submodule and are only
  fallbacks; `custom-rendezvous-server` and `key` options win (`config.rs:1049-1097`; `common.rs:2158-2177`).
  Not needed.
- `OVERWRITE_SETTINGS` beats the saved config and defaults (`config.rs:1359-1388`), cannot be saved over
  (`config.rs:1395-1400`, `2859-2866`), and greys the control in the UI (`src/ui_interface.rs:223-233`;
  `desktop_setting_page.dart:2732`). API strategy sync also refuses to change these keys
  (`src/hbbs_http/sync.rs:294-303`). This is the hook to use.

Keys verified in `libs/base/src/config/keys.rs`: `custom-rendezvous-server` (76), `api-server` (77), `key` (78),
`relay-server` (hbb_common `config.rs:2973`, re-exported `keys.rs:6`), `allow-auto-update` (33),
`enable-check-update` (32, a LOCAL key, `keys.rs:254`). All of the first five are in `KEYS_SETTINGS` (`keys.rs:274-337`).

Append to `src/common.rs` (N1 calls it):

```rust
// Bravetel branding. Values are compiled in; see branding/PLAN.md.
pub const BRAVETEL_APP_NAME: &str = "Bravetel-Support";

pub fn apply_bravetel_branding() {
    *config::APP_NAME.write().unwrap() = BRAVETEL_APP_NAME.to_owned();
    {
        let mut s = config::OVERWRITE_SETTINGS.write().unwrap();
        s.insert(keys::OPTION_CUSTOM_RENDEZVOUS_SERVER.into(), "rd.bravetel.com".into());
        s.insert(keys::OPTION_RELAY_SERVER.into(), "rd.bravetel.com".into());
        s.insert(keys::OPTION_KEY.into(), "mEQ+vfSzFwRzxyTXKvj9cYRvji4N31+NQb0KRcyWUr8=".into());
        s.insert(keys::OPTION_API_SERVER.into(), "https://remote.bravetel.com".into());
        s.insert(keys::OPTION_ALLOW_AUTO_UPDATE.into(), "N".into());
    }
    config::OVERWRITE_LOCAL_SETTINGS
        .write()
        .unwrap()
        .insert(keys::OPTION_ENABLE_CHECK_UPDATE.into(), "N".into());
    {
        let mut b = config::BUILTIN_SETTINGS.write().unwrap();
        for k in [
            keys::OPTION_HIDE_SERVER_SETTINGS,
            keys::OPTION_HIDE_NETWORK_SETTINGS,
            keys::OPTION_HIDE_PROXY_SETTINGS,
            keys::OPTION_HIDE_WEBSOCKET_SETTINGS,
            keys::OPTION_HIDE_SECURITY_SETTINGS,   // see 2.4, decision
            keys::OPTION_HIDE_STOP_SERVICE,
            keys::OPTION_HIDE_POWERED_BY_ME,
            keys::OPTION_HIDE_HELP_CARDS,
            keys::OPTION_DISABLE_CHANGE_ID,
        ] {
            b.insert(k.to_owned(), "Y".to_owned());
        }
    }
    #[cfg(windows)]
    if is_bravetel_quick_support() {
        let mut h = config::HARD_SETTINGS.write().unwrap();
        h.insert("disable-installation".into(), "Y".into());
        // optional: h.insert("conn-type".into(), "incoming".into());
    }
}

#[cfg(windows)]
fn is_bravetel_quick_support() -> bool {
    // Same rule as core_main.rs:911-914 and libs/portable/src/main.rs:375-379.
    let qs = |s: &str| {
        let s = s.to_lowercase();
        s.contains("-qs-") || s.contains("-qs.exe") || s.contains("_qs.exe")
    };
    std::env::var(PORTABLE_APPNAME_RUNTIME_ENV_KEY).map_or(false, |s| qs(&s))
        || std::env::current_exe()
            .ok()
            .and_then(|p| p.file_name().map(|n| qs(&n.to_string_lossy())))
            .unwrap_or(false)
}
```

Notes:
- `keys` is `base::config::keys` in `common.rs:11`; it re-exports hbb_common keys (`keys.rs:6`). `config` and
  `PORTABLE_APPNAME_RUNTIME_ENV_KEY` are in scope in `common.rs` (`common.rs:20`, `54`).
- `api-server` https without `:21114` is used as-is (`common.rs:1270-1285`).
- Relay: the option wins over the hbbs-provided relay (`src/rendezvous_mediator.rs:1367-1376`).
- Key must equal hbbs `id_ed25519.pub`. UNVERIFIED here (taken from the brief).
- Do NOT set builtin `register-device=N`: it blanks the API server (`common.rs:1271-1273`).

Optional hardening (recommended), H1: an exe renamed to `...host=X,key=Y,.exe` overrides the baked
server (exe-name license read in `windows.rs:2174-2181`, applied first in `windows.rs:2212-2214`,
`common.rs:1254-1258`, `1287-1292`, `2158-2163`; `EXE_RENDEZVOUS_SERVER` wins in `config.rs:1049-1052`).
To lock it: make `get_license_from_exe_name` start with `bail!("disabled in Bravetel build");`
(`windows.rs:2174`). `get_license()` then falls back to registry values that are never written
(`windows.rs:4217-4229`).

### 2.4 Hidden settings

| Key (builtin) | Value | Effect (source) |
|---|---|---|
| `hide-server-settings` | Y | Hides ID/relay server entry (`flutter/lib/desktop/pages/desktop_setting_page.dart:1833-1842`) |
| `hide-network-settings` | Y | Removes the whole Network tab (`desktop_setting_page.dart:74-76`) |
| `hide-proxy-settings`, `hide-websocket-settings` | Y | Redundant with the above; harmless |
| `hide-security-settings` | Y (decision) | Removes Security tab (`desktop_setting_page.dart:70-73`). **Does not block CLI.** `--password` is blocked only by HARD `disable-settings` (without `allow-command-line-settings-when-settings-disabled=Y`) or builtin `disable-change-permanent-password` (`src/core_main.rs:425-444`, `882-888`). `--option` likewise (`core_main.rs:514-529`). Set N if end users must manage their own password. |
| `hide-stop-service` | Y | Hides Stop service in settings and tray (`desktop_setting_page.dart:501-507`; `src/tray.rs:68`) |
| `hide-powered-by-me` | Y | Removes "Powered by RustDesk" link (`flutter/lib/common.dart:3773-3776`) |
| `hide-help-cards` | Y | Hides help cards (`flutter/lib/desktop/pages/desktop_home_page.dart:587`) |
| `disable-change-id` | Y | Blocks ID change in UI and `--set-id` (`core_main.rs:472-475`; `config.rs:1321-1328`) |
| `hide-tray` | leave unset | Keeps tray visible for end-user transparency (`src/tray.rs:13-18`) |
| `disable-change-permanent-password` | **never set** | Breaks unattended `--password` (`core_main.rs:430-433`) |
| HARD `disable-settings` | **never set** | Hides tabs and blocks CLI unless the allow key is also set (`core_main.rs:882-888`; `desktop_setting_page.dart:71-81`) |

`--password` also requires installed + elevated (`core_main.rs:434-442`).

### 2.5 Update checker

- Startup "new version" check returns early for any custom client (`APP_NAME != "RustDesk"`) (`src/common.rs:1060-1063`, `2709-2711`). Update card hidden for custom clients (`desktop_home_page.dart:431`); "Check for update" checkbox hidden (`desktop_setting_page.dart:596-602`).
- **Gap:** the Windows "Auto update" checkbox still shows when installed, custom or not (`desktop_setting_page.dart:527-528`, `603-608`). The installed service runs the updater (`src/rendezvous_mediator.rs:320-323`), which fetches `https://api.rustdesk.com/version/latest` (`libs/hbb_common/src/lib.rs:510-511`) and installs the stock RustDesk exe if `allow-auto-update=Y` (`src/updater.rs:189-246`). That would replace the branded agent with stock RustDesk.
- Fix: `OVERWRITE_SETTINGS allow-auto-update=N` (in 2.3). `allow-` options are true only on `"Y"` (`config.rs:2927-2928`), and the overwrite disables the checkbox (`ui_interface.rs:223-233`). Belt and braces: `OVERWRITE_LOCAL_SETTINGS enable-check-update=N`.
- Optional D1 (cosmetic): `desktop_setting_page.dart:527` `final showAutoUpdate = (isWindows && bind.mainIsInstalled()) ||` -> `final showAutoUpdate = (isWindows && bind.mainIsInstalled() && !bind.isCustomClient()) ||`.

### 2.6 Variants: one build, chosen by file name (runtime switch)

Same bytes, different names. No second build needed.

| Variant | File name | Behaviour (source) |
|---|---|---|
| Unattended agent | `bravetel-support-1.5.3-x64.exe` run with `--silent-install` (console script), or MSI | Packer passes args through and pre-extracts (`libs/portable/src/main.rs:286-311`); `--silent-install` -> `install_me` (`core_main.rs:284-298`). Installed to `%ProgramFiles%\Bravetel-Support\Bravetel-Support.exe` (`windows.rs:1433-1447`, `1505`), service `Bravetel-Support` (`windows.rs:4101`). Then `--password`, `--get-id` against the installed exe. |
| Click-to-install | name ending `install.exe` | Auto `--install` (`common.rs:1249-1251`; `main.rs:286`, `308-309`) |
| QuickSupport | `bravetel-support-qs-x64.exe` (keep the `-qs-` form) | Packer passes `--quick_support` (`main.rs:288`, `310-311`); `core_main` runs non-installed quick support with portable service (`core_main.rs:161-168`, `192-203`). Our hook adds HARD `disable-installation=Y`, which hides the Install card (`desktop_home_page.dart:461`) and blocks `--install`/`--silent-install`/`--update` (`core_main.rs:138-150`, `248`, `285`). Detection uses the packer name passed in env `RUSTDESK_APPNAME` (`main.rs:24`, `239-249`) or the exe name. |

- Use `-qs-` in the middle: a browser duplicate like `bravetel-support-qs (1).exe` no longer matches `-qs.exe`, but `bravetel-support-qs-x64 (1).exe` still matches `-qs-` (rule at `core_main.rs:911-914`).
- Optional for QS: HARD `conn-type=incoming` gives the compact incoming-only window (`config.rs:2869-2875`; `desktop_home_page.dart:61-68`). Upstream supports it for MSI too (`preprocess.py:78-82`). Visual result UNVERIFIED.
- Agent and QS share `APP_NAME`, so on a PC where the agent is installed, the QS exe talks to the installed service's pipe (`config.rs:1003-1011`; QS mode only applies when not installed, `core_main.rs:163`). Acceptable.

### 2.7 Other visible upstream links (decide, values TBD)

- About tab: rustdesk.com privacy and website links (`desktop_setting_page.dart:2620`, `2628`); copyright line `Purslane Tech Pte. Ltd.` (`desktop_setting_page.dart:2646`). Keep the copyright/license notice (AGPL appropriate legal notices, R11). Link targets: need Bravetel URLs from user.
- Install page privacy link (`flutter/lib/desktop/pages/install_page.dart:236-238`). Same.
- "Setup server" tip linking rustdesk.com/pricing shows only on the public server (`flutter/lib/desktop/pages/connection_page.dart:81-86`). Not reachable with baked config.

### 2.8 `branding/apply_branding.py` rules (exact replace, assert count == 1)

```
src/common.rs                          "pub fn load_custom_client() {\n" -> + "    apply_bravetel_branding();\n"; append block from 2.3
flutter/windows/runner/Runner.rc       N2..N6
libs/portable/Cargo.toml               N7
src/platform/windows.rs                H1 (optional): "pub fn get_license_from_exe_name() -> ResultType<CustomServer> {\n"
                                          -> + "    bail!(\"disabled in Bravetel build\");\n    #[allow(unreachable_code)]\n"
flutter/lib/desktop/pages/desktop_setting_page.dart   D1 (optional)
copy branding/assets/app_icon.ico  -> flutter/windows/runner/resources/app_icon.ico, flutter/assets/icon.ico
copy branding/assets/icon.png      -> flutter/assets/icon.png
copy branding/assets/icon.ico      -> res/icon.ico
copy branding/assets/tray-icon.ico -> res/tray-icon.ico
copy branding/assets/logo_*.png    -> flutter/assets/ (optional)
```
Then run `cargo check` locally once (UNVERIFIED that the snippet compiles as written; `bail!` and `unreachable_code` placement in H1 to be confirmed by compiler).

---

## 3. Trimmed CI workflow (`.github/workflows/bravetel-windows.yml`, x64, unsigned)

Versions copied from `flutter-build.yml` env: `FLUTTER_VERSION 3.24.5` (31), Windows toolchain
`SCITER_RUST_VERSION 1.75` (24, used at 292), `LLVM_VERSION 15.0.6` (30), `VCPKG_COMMIT_ID 9e593bb18ea69cc5095e012465dcd675a822ed0d` (53),
`VCPKG_BINARY_SOURCES clear;x-gha,readwrite` (46), `VERSION 1.5.3` (56). Bridge: `FLUTTER_RUST_BRIDGE_VERSION 1.80.1`,
`CARGO_EXPAND_VERSION 1.0.95`, Flutter `3.22.3` for the default bridge (`bridge.yml:9-11`, `21-27`).

```yaml
name: Bravetel Windows x64 (unsigned)
on:
  workflow_dispatch:
    inputs:
      build_msi: { type: boolean, default: false }
permissions: { contents: read }
env:
  FLUTTER_VERSION: "3.24.5"
  SCITER_RUST_VERSION: "1.75"
  LLVM_VERSION: "15.0.6"
  VCPKG_COMMIT_ID: "9e593bb18ea69cc5095e012465dcd675a822ed0d"
  VCPKG_BINARY_SOURCES: "clear;x-gha,readwrite"
  VERSION: "1.5.3"
jobs:
  generate-bridge:                       # reuse unchanged: no secrets; also builds an unused 3.44 artifact in parallel
    uses: ./.github/workflows/bridge.yml
  build-RustDeskTempTopMostWindow:       # WindowInjection.dll for privacy mode (flutter-build.yml:134-153)
    uses: ./.github/workflows/third-party-RustDeskTempTopMostWindow.yml
    with: { upload-artifact: true, target: windows-2022, configuration: Release, platform: x64, target_version: Windows10 }
  build-windows-x64:
    needs: [generate-bridge, build-RustDeskTempTopMostWindow]
    runs-on: windows-2022
    steps:
      - Export ACTIONS_CACHE_URL / ACTIONS_RUNTIME_TOKEN    # github-script, as flutter-build.yml:186-191 (vcpkg x-gha cache)
      - Checkout (submodules: recursive)                     # flutter-build.yml:193-196
      - Apply branding: python branding/apply_branding.py    # NEW; fails on any pattern miss
      - Restore bridge files: download-artifact name=bridge-artifact path=./   # flutter-build.yml:198-205
      - Install LLVM ${{ env.LLVM_VERSION }}                 # :207-210
      - Install flutter 3.24.5 (subosito pinned sha, architecture x64)   # :212-222
      - Replace engine with rustdesk custom flutter engine (x64)         # :259-266
      - Patch flutter (dropdown diff)                        # :268-278
      - Rust 1.75, target x86_64-pc-windows-msvc, rustfmt    # :289-294
      - Swatinem/rust-cache                                  # :296-298
      - lukka/run-vcpkg @ VCPKG_COMMIT_ID                    # :300-305
      - vcpkg install --triplet x64-windows-static (bash)    # :307-325
      - Build: python3 .\build.py --portable --flutter --skip-portable-pack --hwcodec --vram
               mv ./flutter/build/windows/x64/runner/Release ./rustdesk
               usbmmidd_v2 + printer driver downloads as upstream   # :334-373
      - Rename + smoke test (pwsh):
               Move-Item ./rustdesk/rustdesk.exe ./rustdesk/bravetel-support.exe
               $v = (& ./rustdesk/bravetel-support.exe --version | Out-String).Trim(); if ($v -ne $env:VERSION) { throw $v }   # pattern from :423-433; --version at core_main.rs:151-154
      - Download topmostwindow-artifacts-x64 into ./rustdesk # :402-407
      - Upload artifact bravetel-support-portable-x64 (./rustdesk)       # :409-414
      - Self-extracting exe (bash):                          # :466-476
               sed -i '/dpiAware/d' res/manifest.xml
               cd libs/portable && pip3 install -r requirements.txt
               python3 ./generate.py -f ../../rustdesk/ -o . -e ../../rustdesk/bravetel-support.exe
               mkdir -p ../../out
               cp ../../target/release/rustdesk-portable-packer.exe ../../out/bravetel-support-$VERSION-x64.exe
               cp ../../target/release/rustdesk-portable-packer.exe ../../out/bravetel-support-qs-x64.exe
      - if build_msi: microsoft/setup-msbuild (x86)           # :478-485
      - if build_msi (pwsh):                                  # :487-500
               pushd res/msi
               python preprocess.py --arp -d ../../rustdesk --app-name Bravetel-Support -m "<Manufacturer>"
               nuget restore msi.sln
               msbuild msi.sln -p:Configuration=Release -p:Platform=x64 /p:TargetVersion=Windows10
               move Package/bin/*/Release/en-us/Package.msi ../../out/bravetel-support-$env:VERSION-x64.msi
      - Upload artifact bravetel-support-installers-x64 (./out)
```

Dropped upstream steps and why (all need secrets or publish upstream-only material):

| Upstream step | Lines | Secret / reason | Action |
|---|---|---|---|
| `validate-update-metadata-keys` job | 64-102 | `RUSTDESK_UPDATE_ED25519_SEED`, var public key | Drop (we never publish update metadata) |
| `generate-sbom` | 103-128 | `contents: write`, publishes a release | Drop |
| Run the Rust tests | 375-384 | none; only when not uploading | Drop (time) |
| find Runner.res | 386-400 | none; nothing in repo consumes `libs/portable/Runner.res` (grep found no reader) | Drop |
| Sign rustdesk files | 416-421 | `SIGN_BASE_URL`, `SIGN_SECRET_KEY` (gated by `SIGN_BASE_URL != '-2'`, env at 63) | Drop |
| Verify Windows Flutter version | 423-433 | none | Replaced by smoke test |
| Verify template payload signatures, Build/Upload template packer | 435-464 | signed payloads | Drop (Server Pro templates) |
| Build/Upload pre-built MSI template | 502-548 | none, Pro template only | Drop |
| Sign self-extracted file, Upload signed EXE/MSI | 550-570 | signing + update metadata | Drop |
| Publish Release (softprops, tag `nightly`) | 572-581 | writes a GitHub release | Drop; use artifacts (or own release step later) |
| arm64 matrix, Flutter 3.44 patches | 175-184, 224-257, 280-287, 327-332 | x64 only | Drop |

Build time estimate (UNVERIFIED, no run yet): bridge job ~10-20 min (parallel); Windows job first run
~75-110 min (vcpkg builds ffmpeg/libvpx etc. from source; upstream notes the Rust build alone is ~25 min,
`flutter-build.yml:247`); warm cache ~40-60 min. Total wall clock first run ~1.5-2 h.

Fork housekeeping (before first push of `bravetel`):
- Disable upstream workflows in the fork: `ci.yml` and `flutter-ci.yml` run on push to master and on PRs,
  `flutter-nightly.yml` on a daily cron, `update-webpki-roots.yml` weekly, `flutter-tag.yml`/`fdroid.yml` on
  tags like `1.5.3` (trigger blocks in each file). `gh workflow disable <name> -R shadikur/rustdesk`.
- Do not push version-pattern tags to the fork; tag Bravetel releases like `bravetel-1.5.3-1`.

---

## 4. Impact on the console (rustdesk-app)

- Installer script: install path becomes `C:\Program Files\Bravetel-Support\Bravetel-Support.exe` (`windows.rs:1433-1447`, `1505`); service `Bravetel-Support`. `--option`/`--config` for server keys become no-ops (`config.rs:1395-1400`) and can be removed. Keep `--password`, `--get-id`.
- QuickSupport download: serve `bravetel-support-qs-x64.exe`; config-carrying file names are no longer needed (and are ignored if H1 is applied).
- "Connect" deep link: branded client registers `bravetel-support://` (`common.rs:1236-1238`, `windows.rs:1614-1618`). Technicians on stock RustDesk keep `rustdesk://`; if technicians switch to the branded build, the console must emit `bravetel-support://`.
- Existing stock-RustDesk enrolments: different `APP_NAME` means separate service, config and key pair. The ID is MAC-derived (`config.rs:1195-1205`) so it will likely be the same number. Whether hbbs accepts the re-registration with a new key pair: UNVERIFIED. Uninstall stock RustDesk first to avoid two services claiming one ID.

---

## 5. Risks and unverified items

- R1 Display name shows `Bravetel-Support` (hyphen) in title, tray, Start menu, ARP, service and translated strings (section 0). True "Bravetel Support" would need patching every unquoted script line plus URI handling. Not recommended.
- R2 Unsigned: SmartScreen "unknown publisher" on the downloaded exe/MSI, UAC shows unknown publisher; remote-access tools often draw AV heuristics. UNVERIFIED for this build until tested on a clean PC.
- R3 Auto-update gap (2.5) is closed only by the overwrite; do not drop it.
- R4 Exe-name server override bypasses baked config unless H1 is applied (2.3).
- R5 MSI and EXE installs are mutually exclusive (`windows.rs:1628-1632`). Pick one per fleet. Recommend the EXE (`--silent-install`), MSI only for GPO/Intune.
- R6 `Replace engine` downloads `rustdesk/engine` release `main`, unpinned (`flutter-build.yml:264`). Supply-chain and reproducibility risk. Same for usbmmidd and printer driver downloads (`:342`, `:350-352`; the driver is sha256-checked, usbmmidd is not).
- R7 vcpkg `x-gha` binary cache behaviour on the fork: copied from upstream, UNVERIFIED on our runs. Without it every run rebuilds vcpkg deps.
- R8 Build time: estimate only (section 3).
- R9 Logo light/dark mapping and `label.png` content: UNVERIFIED.
- R10 hbbs key `mEQ+...` correctness and `rd.bravetel.com` port defaults (21116/21117, `config.rs:119-122`): taken from the brief, UNVERIFIED here.
- R11 Licence (not legal advice): RustDesk is AGPL-3.0 (`LICENCE`). Keep the upstream copyright notice in About (`desktop_setting_page.dart:2646`) and exe version info; publish the `bravetel` branch source (fork is public). Note `preprocess.py:500-509` rewrites the MSI `License.rtf`, replacing "Purslane Tech Pte. Ltd" with the app name; review before shipping an MSI.
- R12 Snippet compile status: UNVERIFIED until `cargo check`; the GitHub Actions free-minutes assumption for public repos is from GitHub billing policy, not checked in this session.
- R13 `conn-type=incoming` for QS: optional, visual result UNVERIFIED.
- R14 Printer: remote printer uses the app name for its printer (`windows.rs:1401-1404`, `res/msi/CustomActions/Common.h:23`); not tested.
