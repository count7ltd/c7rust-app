"""Apply Count7 (C7Support) branding to the RustDesk source tree. Run from the repo root before building.

Every edit is an exact string replacement that must match the expected number of times, so an upstream
change fails the build instead of silently shipping a half-branded client. See branding/PLAN.md for the
source references behind each edit.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = Path(__file__).resolve().parent / "assets"

APP_NAME = "C7Support"  # internal name: letters, digits and hyphens only (src/lang.rs)
DISPLAY_NAME = "C7Support"  # file metadata only
EXE_NAME = "c7support.exe"
COMPANY = "Count7 Ltd"
WEBSITE = "https://count7.co.uk"
PRIVACY = "https://count7.co.uk/privacy-policy/"
# macOS: permanent once shipped (privacy grants are tied to it); must not contain "rustdesk"
# (src/platform/macos.rs correct_app_name rewrites that word after swapping the bundle id).
BUNDLE_ID = "net.count7.support"
URI_SCHEME = APP_NAME.lower()  # must match get_uri_prefix in src/common.rs

ID_SERVER = "rd.count7.net"
RELAY_SERVER = "rd.count7.net"
SERVER_KEY = "mEQ+vfSzFwRzxyTXKvj9cYRvji4N31+NQb0KRcyWUr8="
API_SERVER = "https://remote.count7.net"

errors: list[str] = []


def edit(rel: str, old: str, new: str, count: int = 1) -> None:
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    found = text.count(old)
    if found != count:
        errors.append(f"{rel}: expected {count} match(es), found {found}: {old[:70]!r}")
        return
    path.write_text(text.replace(old, new), encoding="utf-8", newline="")


def copy(asset: str, *targets: str) -> None:
    for t in targets:
        dest = ROOT / t
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ASSETS / asset, dest)


BRANDING_RS = f'''

// ---- Bravetel branding (added by branding/apply_branding.py) ----
pub const BRAVETEL_APP_NAME: &str = "{APP_NAME}";

/// Compiled-in branding. Runs where upstream applies a signed custom.txt (load_custom_client).
pub fn apply_bravetel_branding() {{
    *config::APP_NAME.write().unwrap() = BRAVETEL_APP_NAME.to_owned();
    {{
        // OVERWRITE_SETTINGS win over saved config, cannot be saved over, grey out the UI controls,
        // and are refused by API strategy sync.
        let mut s = config::OVERWRITE_SETTINGS.write().unwrap();
        s.insert(keys::OPTION_CUSTOM_RENDEZVOUS_SERVER.into(), "{ID_SERVER}".into());
        s.insert(keys::OPTION_RELAY_SERVER.into(), "{RELAY_SERVER}".into());
        s.insert(keys::OPTION_KEY.into(), "{SERVER_KEY}".into());
        s.insert(keys::OPTION_API_SERVER.into(), "{API_SERVER}".into());
        // Never let the updater replace this build with stock RustDesk.
        s.insert(keys::OPTION_ALLOW_AUTO_UPDATE.into(), "N".into());
    }}
    config::OVERWRITE_LOCAL_SETTINGS
        .write()
        .unwrap()
        .insert(keys::OPTION_ENABLE_CHECK_UPDATE.into(), "N".into());
    {{
        // Must NOT include disable-change-permanent-password or hard disable-settings: the unattended
        // installer sets the permanent password with --password.
        let mut b = config::BUILTIN_SETTINGS.write().unwrap();
        for k in [
            keys::OPTION_HIDE_SERVER_SETTINGS,
            keys::OPTION_HIDE_NETWORK_SETTINGS,
            keys::OPTION_HIDE_PROXY_SETTINGS,
            keys::OPTION_HIDE_WEBSOCKET_SETTINGS,
            keys::OPTION_HIDE_SECURITY_SETTINGS,
            keys::OPTION_HIDE_STOP_SERVICE,
            keys::OPTION_HIDE_POWERED_BY_ME,
            keys::OPTION_DISABLE_CHANGE_ID,
        ] {{
            b.insert(k.to_owned(), "Y".to_owned());
        }}
        // Not on macOS: there it also hides the Screen Recording / Accessibility / Input Monitoring
        // cards (desktop_home_page.dart buildInstallCard), leaving users no way to grant them.
        #[cfg(not(target_os = "macos"))]
        b.insert(keys::OPTION_HIDE_HELP_CARDS.to_owned(), "Y".to_owned());
    }}
    #[cfg(windows)]
    if is_bravetel_quick_support() {{
        // QuickSupport: run without install, hide the Install prompt, block --install.
        config::HARD_SETTINGS
            .write()
            .unwrap()
            .insert("disable-installation".into(), "Y".into());
    }}
}}

#[cfg(windows)]
fn is_bravetel_quick_support() -> bool {{
    // Same rule as core_main.rs is_quick_support_exe and libs/portable/src/main.rs.
    let qs = |s: &str| {{
        let s = s.to_lowercase();
        s.contains("-qs-") || s.contains("-qs.exe") || s.contains("_qs.exe")
    }};
    std::env::var(PORTABLE_APPNAME_RUNTIME_ENV_KEY).map_or(false, |s| qs(&s))
        || std::env::current_exe()
            .ok()
            .and_then(|p| p.file_name().map(|n| qs(&n.to_string_lossy())))
            .unwrap_or(false)
}}
'''


def main() -> int:
    # Name and baked config: hook runs first in load_custom_client.
    edit("src/common.rs", "pub fn load_custom_client() {\n", "pub fn load_custom_client() {\n    apply_bravetel_branding();\n")
    with (ROOT / "src/common.rs").open("a", encoding="utf-8", newline="") as f:
        f.write(BRANDING_RS)

    # An exe renamed to "host=...,key=..." must not override the baked server.
    edit(
        "src/platform/windows.rs",
        "pub fn get_license_from_exe_name() -> ResultType<CustomServer> {\n",
        "pub fn get_license_from_exe_name() -> ResultType<CustomServer> {\n"
        '    bail!("server settings from the exe name are disabled in this build")\n'
        "}\n\n#[allow(dead_code)]\nfn upstream_get_license_from_exe_name() -> ResultType<CustomServer> {\n",
    )

    # Exe version info (Flutter runner).
    rc = "flutter/windows/runner/Runner.rc"
    edit(rc, '"CompanyName", "Purslane Tech Pte. Ltd." "\\0"', f'"CompanyName", "{COMPANY}" "\\0"')
    edit(rc, '"FileDescription", "RustDesk Remote Desktop" "\\0"', f'"FileDescription", "{DISPLAY_NAME}" "\\0"')
    edit(rc, '"InternalName", "rustdesk" "\\0"', '"InternalName", "c7support" "\\0"')
    edit(rc, '"OriginalFilename", "rustdesk.exe" "\\0"', f'"OriginalFilename", "{EXE_NAME}" "\\0"')
    edit(rc, '"ProductName", "RustDesk" "\\0"', f'"ProductName", "{DISPLAY_NAME}" "\\0"')

    # Version info of the self-extracting download.
    pc = "libs/portable/Cargo.toml"
    edit(pc, 'ProductName = "RustDesk"', f'ProductName = "{DISPLAY_NAME}"\nCompanyName = "{COMPANY}"')
    edit(pc, 'OriginalFilename = "rustdesk.exe"', f'OriginalFilename = "{EXE_NAME}"')
    edit(pc, 'FileDescription = "RustDesk Remote Desktop"', f'FileDescription = "{DISPLAY_NAME}"')

    # Hide the Windows "Auto update" checkbox for this build (the overwrite above already disables it).
    edit(
        "flutter/lib/desktop/pages/desktop_setting_page.dart",
        "final showAutoUpdate = (isWindows && bind.mainIsInstalled()) ||",
        "final showAutoUpdate = (isWindows && bind.mainIsInstalled() && !bind.isCustomClient()) ||",
    )

    # About and install page links. The upstream copyright notice in About stays (AGPL).
    edit("flutter/lib/desktop/pages/desktop_setting_page.dart", "'https://rustdesk.com/privacy.html'", f"'{PRIVACY}'")
    edit("flutter/lib/desktop/pages/desktop_setting_page.dart", "launchUrlString('https://rustdesk.com');", f"launchUrlString('{WEBSITE}');")
    edit("flutter/lib/desktop/pages/install_page.dart", "'https://rustdesk.com/privacy.html'", f"'{PRIVACY}'", count=2)

    # macOS bundle (see branding/PLAN-macos.md). Inert on Windows: these files are not compiled there.
    xc = "flutter/macos/Runner/Configs/AppInfo.xcconfig"
    # The bundle name must equal APP_NAME (install checks, launchd plists); keep the Swift module name
    # that MainMenu.xib binds to.
    edit(xc, "PRODUCT_NAME = RustDesk", f"PRODUCT_NAME = {APP_NAME}\nPRODUCT_MODULE_NAME = RustDesk")
    edit(xc, "PRODUCT_BUNDLE_IDENTIFIER = com.carriez.flutterHbb", f"PRODUCT_BUNDLE_IDENTIFIER = {BUNDLE_ID}")
    edit(
        "flutter/macos/Runner.xcodeproj/project.pbxproj",
        "PRODUCT_BUNDLE_IDENTIFIER = com.carriez.rustdesk;",
        f"PRODUCT_BUNDLE_IDENTIFIER = {BUNDLE_ID};",
        count=3,
    )
    pl = "flutter/macos/Runner/Info.plist"
    edit(pl, "<string>com.carriez.rustdesk</string>", f"<string>{BUNDLE_ID}</string>")
    edit(pl, "<string>rustdesk</string>", f"<string>{URI_SCHEME}</string>")
    edit(
        "build.py",
        "./build/macos/Build/Products/Release/RustDesk.app/Contents/MacOS/",
        f"./build/macos/Build/Products/Release/{APP_NAME}.app/Contents/MacOS/",
    )
    # macOS menu bar icon is a template (alpha only): use the "B" glyph, not the colour icon.png.
    edit(
        "src/tray.rs",
        '"../Frameworks/App.framework/Resources/flutter_assets/assets/icon.png"',
        '"../Frameworks/App.framework/Resources/flutter_assets/assets/mac-tray.png"',
    )

    # Icons and logos.
    copy("AppIcon.icns", "flutter/macos/Runner/AppIcon.icns")
    copy("mac-tray.png", "res/mac-tray-dark-x2.png", "flutter/assets/mac-tray.png")
    copy("app_icon.ico", "flutter/windows/runner/resources/app_icon.ico", "flutter/assets/icon.ico")
    copy("icon.png", "flutter/assets/icon.png")
    copy("icon.ico", "res/icon.ico")
    copy("tray-icon.ico", "res/tray-icon.ico")
    copy("logo_light.png", "flutter/assets/logo_light.png")
    copy("logo_dark.png", "flutter/assets/logo_dark.png")

    # Refuse to build while the settings at the top still carry the template's (Bravetel) name or key:
    # such an app would carry someone else's brand, and the key must be the one from your own server.
    template = (APP_NAME, COMPANY, WEBSITE, PRIVACY, BUNDLE_ID, ID_SERVER, RELAY_SERVER, API_SERVER)
    if any("bravetel" in v.lower() for v in template) or SERVER_KEY.startswith("mEQ+vfSz"):
        errors.append("set your own app name, company, website, bundle id and server key at the top of this file")

    if errors:
        print("Branding FAILED:", *errors, sep="\n  ")
        return 1
    print(f"Branding applied: {APP_NAME} -> {ID_SERVER} / {API_SERVER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
