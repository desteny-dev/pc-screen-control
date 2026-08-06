# When Claude on Windows refuses to install the extension

**Short version: do not uninstall the old version before installing a new one,
and if you are already stuck, use the `.zip` instead of the `.mcpb`. Nothing is
lost either way — both contain the same server.**

---

## The error

```
Installation der Erweiterung fehlgeschlagen
Die Erweiterung konnte aufgrund des folgenden Fehlers nicht installiert werden:
Private dir leaf redirects (junction/substitute-name plant):
C:\Users\<you>\AppData\Roaming\Claude\Claude Extensions
```

In English: *Extension installation failed — private dir leaf redirects.*

It appears **after** an extension has been uninstalled through
Settings → Extensions. A first-time install is not affected.

## What it is not

It is not this package. It is not your antivirus, your disk, or a corrupted
download. The same file installs on a machine that has never had it.

Measured on the machine where it happened: the server itself starts fine when
run by hand, answers `initialize` in milliseconds, and Claude's own MCP log
shows it loading and returning its tool list in 173 ms. Nothing about the
software is broken.

## What it is

Claude Desktop on Windows has an open defect around uninstalling extensions:
after a UI uninstall, the same extension cannot be installed again. Reported in
June 2026 as
[claude-code#67919](https://github.com/anthropics/claude-code/issues/67919)
(`bug`, `area:desktop`, `platform:windows`), still open. In that report the
install hangs silently; the message above is a different symptom of the same
sequence — **installed, uninstalled, blocked.**

Reinstalling Claude Desktop does not help, because the state lives in the
profile and the profile survives a reinstall.

## What to do

### If you are upgrading

**Install the new `.mcpb` straight over the old one.** Claude replaces it.
Do not uninstall first — that is the step that causes this.

Quit Claude completely before installing, tray icon included. Claude reads its
extensions at start.

### If you are already stuck

Use the other download. `pc-screen-control-setup.zip` → extract →
`INSTALL.bat` → restart Claude.

This registers the same server as an **MCP server** instead of an extension.
Same file, same 34 tools, same version. The only differences:

|  | as an extension | as an MCP server |
|---|---|---|
| shows up under | Extensions | Connectors |
| on/off switch in the UI | yes | no — remove the entry instead |
| updating | double-click the new file | run the installer again |
| affected by the defect above | yes | **no** |

Nothing about how it works changes. Both routes end at the same `server.py`.

## A note for people on the Store build

If Claude Desktop came from the Microsoft Store, it runs as a packaged app, and
Windows redirects `%APPDATA%` into the package's own container. Its config lives
at

```
%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude\claude_desktop_config.json
```

not at `%APPDATA%\Claude\`. The installer here writes both, so this is handled -
but if you edit a config by hand and nothing happens, that is why: there are two
files with the same name and only one of them is read.
