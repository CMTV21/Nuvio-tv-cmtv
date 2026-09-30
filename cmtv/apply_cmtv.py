#!/usr/bin/env python3
"""CMTV changes to a clean NuvioTV checkout (run in the checkout's root). 2026-09-29.

Every change checks that the original text is there exactly once and stops otherwise, so a new Nuvio release that moved
something fails loudly instead of building a half-changed app. What it changes (and nothing else):
  - separate app identity info.cmtv.nuvio (installs next to the official Nuvio), version <upstream>-cmtv.<rev>
  - in-app updates from billing (billing.cmtv.info/api/cmtv/app-updates/, GitHub-shaped; only builds the owner publishes),
    never from Nuvio's GitHub (that would replace our build with the official one); "-cmtv.N" counts as stable; no switching servers
  - our server (nuvio.cmtv.info) as the built-in one, with username + password sign-in on the TV
    (a username gets "@nuvio.cmtv.info" added: billing's accounts are <username>@nuvio.cmtv.info; an old-style login with
    "@" and no dot after it, like Rob@2025, becomes rob_at_2025, as in billing's login_id())
  - sign-in texts say "CMTV username"; tagline "... Provided by CMTV."
  - a small CMTV badge in the corner of the Nuvio icon and TV banner (all icon colour choices)
The Nuvio name and logo stay as they are.
Usage: python3 apply_cmtv.py <cmtv revision number> <badge png>
"""
import re
import sys
from pathlib import Path

REV = int(sys.argv[1]) if len(sys.argv) > 1 else 1
BADGE = sys.argv[2] if len(sys.argv) > 2 else "/opt/frontend/public/cmtv/favicon-192.png"
DOMAIN = "nuvio.cmtv.info"


def edit(path, old, new, count=1):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    n = s.count(old)
    if n != count:
        sys.exit(f"STOP: {path}: expected {count}x {old[:70]!r}, found {n}. Nuvio changed this file; update apply_cmtv.py.")
    p.write_text(s.replace(old, new), encoding="utf-8")


def edit_re(path, pattern, repl, count=1):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    new, n = re.subn(pattern, repl, s, flags=re.S)
    if n != count:
        sys.exit(f"STOP: {path}: pattern {pattern[:70]!r} matched {n}x, expected {count}.")
    p.write_text(new, encoding="utf-8")


G = "app/build.gradle.kts"
edit(G, 'applicationId = "com.nuvio.tv"', 'applicationId = "info.cmtv.nuvio" // CMTV build')
edit_re(G, r'versionCode = (\d+)\n', lambda m: f'versionCode = {int(m.group(1)) * 10 + REV} // CMTV: upstream x10 + {REV}\n')
edit_re(G, r'versionName = "([^"]+)"', lambda m: f'versionName = "{m.group(1)}-cmtv.{REV}"')
full = re.search(r'create\("full"\) \{.*?\n        \}', Path(G).read_text(encoding="utf-8"), re.S).group(0)
full2 = full.replace('"FEATURE_CUSTOM_SERVER_CONNECTIONS_ENABLED", "true"', '"FEATURE_CUSTOM_SERVER_CONNECTIONS_ENABLED", "false"')
if full2.count('"false"') != full.count('"false"') + 1 or '"FEATURE_IN_APP_UPDATES_ENABLED", "true"' not in full2:
    sys.exit("STOP: the full flavor's custom-server / updater switches weren't found")
edit(G, full, full2)

# In-app updates come from billing, not Nuvio's GitHub (rev 3, 2026-09-29): billing serves GitHub-shaped release JSON at
# /api/cmtv/app-updates/repos/cmtv/nuvio-tv/releases[/latest], only for builds the owner publishes in Admin > Nuvio > App.
edit(G, 'buildConfigField("String", "GITHUB_OWNER", "\\"NuvioMedia\\"")', 'buildConfigField("String", "GITHUB_OWNER", "\\"cmtv\\"") // CMTV')
edit(G, 'buildConfigField("String", "GITHUB_REPO", "\\"NuvioTV\\"")', 'buildConfigField("String", "GITHUB_REPO", "\\"nuvio-tv\\"") // CMTV')
edit("app/src/main/java/com/nuvio/tv/core/di/NetworkModule.kt", '.baseUrl("https://api.github.com/")',
     '.baseUrl("https://billing.cmtv.info/api/cmtv/app-updates/") // CMTV: updates from billing')
# "-cmtv.N" builds are our stable releases, not betas (semver would call anything with a dash a pre-release)
edit("app/src/main/java/com/nuvio/tv/updater/ReleaseSelector.kt", "    version.prerelease.isNotEmpty() ||",
     '    (version.prerelease.isNotEmpty() && version.prerelease.firstOrNull() != "cmtv") || // CMTV')
edit("app/src/main/java/com/nuvio/tv/updater/VersionUtils.kt",
     "fun isPrerelease(raw: String?): Boolean = parse(raw)?.prerelease?.isNotEmpty() == true",
     'fun isPrerelease(raw: String?): Boolean = parse(raw)?.prerelease?.let { it.isNotEmpty() && it.firstOrNull() != "cmtv" } == true // CMTV')

edit("app/src/main/java/com/nuvio/tv/data/local/ServerConfigurationStore.kt",
     "            emailPasswordAuth = false,\n            tvLogin = true\n        ),\n        isCustom = false,",
     "            emailPasswordAuth = true, // CMTV: username + password on the TV\n            tvLogin = true\n        ),\n        isCustom = false,")
VM = "app/src/main/java/com/nuvio/tv/ui/screens/account/AccountViewModel.kt"
edit(VM, "get() = serverConfiguration.isCustom && serverConfiguration.capabilities.emailPasswordAuth",
     "get() = serverConfiguration.capabilities.emailPasswordAuth // CMTV: our server is the built-in one")
# username -> <id>@nuvio.cmtv.info; an "@" with no dot after it is an old Stremio login ("Rob@2025" -> "rob_at_2025"),
# the same rule as billing's cmtv_nuvio.login_id() (rev 4, 2026-09-30); a real email (dot after the @) is sent as typed
edit(VM, "authManager.signInWithEmail(email, password).fold(",
     'authManager.signInWithEmail(email.trim().let { if ("@" in it && "." in it.substringAfter("@")) it '
     f'else it.lowercase().replace("@", "_at_") + "@{DOMAIN}" }}, password).fold( // CMTV: username (+ old Rob@2025 logins)')
edit("app/src/main/java/com/nuvio/tv/ui/screens/account/AuthQrSignInScreen.kt",
     "placeholder = stringResource(R.string.auth_email_placeholder),\n            keyboardType = KeyboardType.Email,",
     "placeholder = stringResource(R.string.auth_email_placeholder),\n            keyboardType = KeyboardType.Text, // CMTV: username")

S = "app/src/main/res/values/strings.xml"
for name, old, new in [
    ("account_signin_email_subtitle", "Enter your self-hosted account email and password", "Enter your CMTV username and password"),
    ("auth_email_hint", "Sign in directly with the account on your self-hosted server.", "Sign in with your CMTV username and password."),
    ("auth_email_instruction", "Enter your email and password to continue.", "Enter your CMTV username and password to continue."),
    ("auth_email_placeholder", "Email address", "Username"),
    ("auth_qr_tagline", "Watch your library, anywhere", "Watch your library, anywhere. Provided by CMTV."),
]:
    edit(S, f'<string name="{name}">{old}</string>', f'<string name="{name}">{new}</string>')

# CMTV badge in the corner of every launcher icon and TV banner
from PIL import Image, ImageDraw

badge_src = Image.open(BADGE).convert("RGBA")


def add_badge(path: Path):
    im = Image.open(path)
    mode = im.mode
    im = im.convert("RGBA")
    w, h = im.size
    side = int(min(w, h) * (0.36 if w == h else 0.34))
    pad = max(2, side // 12)
    tile = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    r = side // 4
    d.rounded_rectangle([0, 0, side - 1, side - 1], radius=r, fill=(10, 16, 32, 235), outline=(34, 211, 238, 255),
                        width=max(1, side // 28))
    logo = badge_src.resize((side - 2 * pad, side - 2 * pad), Image.LANCZOS)
    tile.alpha_composite(logo, (pad, pad))
    margin = max(2, int(min(w, h) * 0.05))
    im.alpha_composite(tile, (w - side - margin, h - side - margin))
    (im if mode == "RGBA" else im.convert(mode)).save(path)


res = Path("app/src/main/res")
done = 0
for p in sorted(res.glob("mipmap-*/*.png")) + [res / "drawable/ic_launcher.png", res / "drawable/tv_banner.png"]:
    if p.exists() and (p.name.startswith("ic_launcher") or p.name.startswith("banner") or p.name == "tv_banner.png"):
        add_badge(p)
        done += 1
if done < 10:
    sys.exit(f"STOP: only {done} icons/banners found to badge")
print(f"CMTV changes applied (rev {REV}); badged {done} icons/banners")
