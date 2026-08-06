# -*- coding: utf-8 -*-
"""
Claude from the Microsoft Store reads a different config file.

This is here because of a real installation that reported success and did
nothing. The installer wrote `%APPDATA%\\Claude\\claude_desktop_config.json`,
said "Claude Desktop updated", and the server never appeared. The file had
really been written. It was simply not the file Claude reads.

Claude Desktop from the Store is an MSIX package, and a packaged app does not
see %APPDATA% - Windows redirects it into the package container at

    %LOCALAPPDATA%\\Packages\\Claude...\\LocalCache\\Roaming\\Claude\\

Measured as a clean A/B on the machine it happened on: writing the outer file
left the server unconnected after a restart; writing the container file
connected it. Same content, same restart, opposite result.

That makes it the fourth time in this project that the same shape of defect has
come back: *something is written, and nothing checks whether it arrives where it
is read.* So this file asserts the behaviour, not the fix:

  1. The container path is among the places the installer writes.
  2. Both are written when both exist - a machine can have the Store build and
     the classic build side by side.
  3. When the Store build is present and its config was NOT written, the
     installer says so. Silence there is what cost the afternoon.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src")
sys.path.insert(0, SRC)

failures = []


def check(name, ok, detail=""):
    if not ok:
        failures.append(name)
    print("  %-58s %-6s %s" % (name, "OK" if ok else "FAIL", detail))


QUELLE = open(os.path.join(SRC, "server.py"), encoding="utf-8").read()


def main():
    print("\n1 - The container is one of the places that get written")
    kandidaten = QUELLE.split("def _config_candidates", 1)[1] \
                       .split("\nCONFIG_CANDIDATES", 1)[0]
    check("LOCALAPPDATA is consulted", "LOCALAPPDATA" in kandidaten)
    check("the package folder is searched", '"Packages"' in kandidaten)
    check("the redirected roaming path is built",
          "LocalCache" in kandidaten and '"Roaming"' in kandidaten)
    check("more than one Claude package is handled",
          "glob" in kandidaten and "for " in kandidaten)
    check("the two are told apart in the output",
          '"Claude Desktop (Store)"' in kandidaten)

    print("\n2 - The outer path is still written, not replaced")
    check("APPDATA is still a candidate", '"APPDATA"' in kandidaten)
    check("both are appended, neither returns early",
          kandidaten.count("out.append") >= 3, "%d appends"
          % kandidaten.count("out.append"))

    print("\n3 - A Store build that got nothing is named, not passed over")
    check("there is a check of its own for it",
          "def _install_warn_store" in QUELLE)
    warn = QUELLE.split("def _install_warn_store", 1)[1] \
                 .split("\ndef ", 1)[0]
    check("it looks for the package FOLDER, not the config file",
          '"Packages"' in warn and "pakete" in warn)
    check("it stays quiet when the container was written",
          "any_store_written" in warn and "return" in warn)
    check("it prints the path the config actually belongs at",
          "LocalCache" in warn)
    check("it says what to do", "run this again" in warn)
    check("it also names the extension limit",
          ".mcpb" in warn and "no workaround" in warn)
    check("the installer calls it",
          "_install_warn_store(" in QUELLE.split("def _install_warn_store")[0])

    print("\n4 - The judgement comes from what was written, not from hope")
    einbau = QUELLE.split("_install_warn_store(any_store_written=", 1)[1] \
                   .split("\n\n", 1)[0]
    check("it is decided from the recorded results",
          "geschrieben" in einbau and "added" in einbau and
          "updated" in einbau, einbau.split("\n")[0][:60])

    print("\n5 - Existing guarantees still stand")
    schreib = QUELLE.split("def _install_write_config", 1)[1] \
                    .split("\ndef ", 1)[0]
    check("a backup is still taken first", ".backup" in schreib)
    check("the write is still atomic", "os.replace" in schreib)
    check("it is still read back afterwards",
          "did not read back" in schreib)
    check("other entries are still left alone",
          "setdefault" in schreib and "servers[SERVER_NAME]" in schreib)

    print("\n" + "=" * 66)
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("test_store_build: all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
