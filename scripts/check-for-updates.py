# -*- coding: utf-8 -*-
"""
The updater. Separate from the server on purpose.

The server that controls your PC makes no network connection at all - you can
grep it and check. This little program is the only part that talks to the
network, and it runs only when a person starts it by hand (CHECK-FOR-UPDATES.bat
double-clicked, or `python check-for-updates.py`). The server neither offers nor
triggers it, so there is no path by which the thing driving your mouse can reach
the internet on its own.

What it does, and nothing more:
  1. asks GitHub's public release API whether a newer version exists;
  2. if there is one, prints the version and the release page and asks you,
     in plain words, whether to download it;
  3. only after you type yes, downloads the .mcpb;
  4. verifies the download against the SHA-256 in the release notes before it is
     written to disk. On a mismatch it refuses and saves nothing.

It never installs anything and never touches your Claude config. You install the
downloaded file yourself, the same way as the first time.
"""
import hashlib
import json
import os
import re
import ssl
import sys
import urllib.request

RELEASE_API = ("https://api.github.com/repos/desteny-dev/"
               "pc-screen-control/releases/latest")
THIS_VERSION_FALLBACK = "1.1.0"


def _installed_version():
    """Best effort: read the version out of the installed server, else fall
    back. Purely informational - the comparison still works either way."""
    hier = os.path.dirname(os.path.abspath(__file__))
    for kandidat in (os.path.join(hier, "..", "src", "server.py"),
                     os.path.join(os.environ.get("LOCALAPPDATA", ""),
                                  "pc-screen-control", "server.py")):
        try:
            with open(kandidat, encoding="utf-8") as fh:
                m = re.search(r'SERVER_VERSION\s*=\s*"([^"]+)"', fh.read())
                if m:
                    return m.group(1)
        except Exception:
            pass
    return THIS_VERSION_FALLBACK


def _tup(s):
    out = []
    for teil in str(s).lstrip("vV").split("."):
        ziffern = "".join(c for c in teil if c.isdigit())
        out.append(int(ziffern) if ziffern else 0)
    return tuple(out)


def frage_ja(text):
    try:
        return input(text + " [y/N] ").strip().lower() in ("y", "yes", "j", "ja")
    except (EOFError, KeyboardInterrupt):
        return False


def main():
    ctx = ssl.create_default_context()
    aktuell = _installed_version()
    print("PC Screen Control - update check")
    print("You have version %s.\n" % aktuell)

    try:
        req = urllib.request.Request(
            RELEASE_API, headers={"User-Agent": "pc-screen-control-updater"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            rel = json.loads(r.read())
    except Exception as e:
        code = getattr(e, "code", None)
        if code == 404:
            print("No public release exists yet. You are on the current build.")
            return 0
        print("Could not reach GitHub (%s). Try again later, or check the "
              "releases page in your browser." % e)
        return 1

    neueste = rel.get("tag_name") or ""
    if _tup(neueste) <= _tup(aktuell):
        print("You are on the latest version (%s)." % neueste)
        return 0

    print("A newer version is available: %s" % neueste)
    print("Release page: %s\n" % rel.get("html_url"))
    if not frage_ja("Download it now?"):
        print("Nothing downloaded. You can get it any time from the release "
              "page above.")
        return 0

    anhang = None
    for a in rel.get("assets", []):
        if str(a.get("name", "")).endswith(".mcpb"):
            anhang = a
            break
    if not anhang:
        print("The release has no .mcpb to download. Get it from the page.")
        return 1

    # The hash we will check against, pulled from the release notes.
    m = re.search(r"SHA-?256[^0-9a-fA-F]*([0-9a-fA-F]{64})",
                  rel.get("body") or "", re.IGNORECASE)
    erwartet = m.group(1).lower() if m else None

    print("Downloading %s ..." % anhang["name"])
    try:
        dl = urllib.request.Request(
            anhang["browser_download_url"],
            headers={"User-Agent": "pc-screen-control-updater"})
        with urllib.request.urlopen(dl, timeout=120, context=ctx) as r:
            daten = r.read()
    except Exception as e:
        print("Download failed (%s). Get it from the release page instead." % e)
        return 1

    tatsaechlich = hashlib.sha256(daten).hexdigest()
    if erwartet is None:
        print("REFUSED: the release notes carry no SHA-256 to verify this "
              "against, so nothing was saved. This is unusual for a real "
              "release - treat it as suspect and get it from the page by hand.")
        return 1
    if tatsaechlich != erwartet:
        print("REFUSED: the downloaded file does not match the SHA-256 in the "
              "release notes.\n  expected %s\n  got      %s\nNothing was saved. "
              "This can be a corrupted download or a tampered file. Do not "
              "install anything; try again on a connection you trust."
              % (erwartet, tatsaechlich))
        return 1

    ziel_ordner = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(ziel_ordner, exist_ok=True)
    ziel = os.path.join(ziel_ordner, os.path.basename(anhang["name"]))
    with open(ziel, "wb") as fh:
        fh.write(daten)

    print("\nDownloaded and verified. Saved to:\n  %s\n" % ziel)
    print("To install it:")
    print("  1. In Claude Desktop: Settings > Extensions > Advanced >")
    print("     Install extension... and pick that file.")
    print("  2. Close Claude completely (tray icon too) and start it again.")
    print("\nThis updater installed nothing and did not touch any config.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
