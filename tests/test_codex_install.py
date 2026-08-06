# -*- coding: utf-8 -*-
"""
Registering with Codex must not damage a config that is already there.

This used to live in a separate script, `install-for-gpt.py`, shipped in a
download named for GPT. That name is why this file changed: the package was the
only route that still worked when Claude refused to install an extension, and
every Claude user read "for GPT" and closed it again. The writer now lives in
the installer itself, so ONE run registers every client on the machine.

The file being written is not ours. `~/.codex/config.toml` may already hold
other MCP servers, model settings and API keys, written by hand or by another
tool. Adding one block to it is easy to get almost right and ruinous to get
wrong, so the same things are checked here that the Claude installer checks:
foreign entries survive untouched, a second run updates instead of duplicating,
a backup is made once and never overwritten, Windows paths come out the other
side meaning what they said, and the result is read back before anything is
called a success.

Runs against temporary files. Nothing real is read or written.
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src")
sys.path.insert(0, SRC)

import server as srv  # noqa: E402

failures = []


def check(name, ok, detail=""):
    if not ok:
        failures.append(name)
    print("  %-58s %-6s %s" % (name, "OK" if ok else "FAIL", detail))


try:
    import tomllib as _toml
except ImportError:                                   # Python 3.9 / 3.10
    _toml = None


def toml_ok(text):
    """Ohne Parser laesst sich das nicht messen - dann wird es auch nicht
    behauptet. Auf 3.11+ laeuft es echt, und dort laeuft die CI auch."""
    if _toml is None:
        return True
    try:
        _toml.loads(text)
        return True
    except Exception:
        return False


def toml_fehler(text):
    if _toml is None:
        return "kein tomllib in dieser Python-Fassung - ungeprueft"
    try:
        _toml.loads(text)
        return ""
    except Exception as e:
        return "%s: %s" % (type(e).__name__, e)


FREMD = """model = "gpt-5"
approval_policy = "on-request"

[mcp_servers.context7]
command = "npx"
args = ["-y", "@upstash/context7-mcp"]

[mcp_servers.other-thing]
command = "node"
args = ["x.js"]
"""

# Deliberately not a path under a real home directory. The consistency checker
# refuses those anywhere in the published tree, and it is right to: a fixture
# that looks like somebody's own machine is how one leaks.
SRV = r"X:\Tools\pc-screen-control\server.py"
SRV2 = r"X:\Anders\server.py"


class Heim(object):
    """Point expanduser at a temporary directory, so a test run can never
    reach the config of the person running it."""

    def __init__(self, mit_codex=True):
        self.mit_codex = mit_codex

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix="psc_codex_")
        self.alt = srv.os.path.expanduser
        srv.os.path.expanduser = lambda p: (
            self.dir + p[1:] if p.startswith("~") else p)
        if self.mit_codex:
            os.makedirs(os.path.join(self.dir, ".codex"))
        return self

    def __exit__(self, *a):
        srv.os.path.expanduser = self.alt
        shutil.rmtree(self.dir, ignore_errors=True)

    @property
    def config(self):
        return os.path.join(self.dir, ".codex", "config.toml")

    def schreiben(self, text):
        with open(self.config, "w", encoding="utf-8") as fh:
            fh.write(text)

    def lesen(self):
        with open(self.config, encoding="utf-8") as fh:
            return fh.read()


def main():
    print("\n1 - Windows paths survive being written into TOML")
    w = srv._toml_string(SRV)
    check("backslashes are escaped", "\\\\" in w and w.startswith('"'))
    check("it round-trips to the path that went in",
          w[1:-1].replace("\\\\", "\\") == SRV, w)
    check("a quote in a path cannot end the string early",
          srv._toml_string('a"b') == '"a\\"b"', srv._toml_string('a"b'))

    print("\n2 - The block names the server and both commands")
    b = srv._codex_block(SRV)
    check("our table header is there",
          "[mcp_servers.pc-screen-control]" in b)
    check("command and args are both set",
          "command = " in b and "args = [" in b)
    check("timeouts are given, so a slow first start is not a failure",
          "startup_timeout_sec" in b and "tool_timeout_sec" in b)

    print("\n3 - A config that is not ours comes back intact")
    with Heim() as h:
        h.schreiben(FREMD)
        state, detail = srv._install_write_codex(SRV)
        check("reported as added", state == "added", "%s %s" % (state, detail))
        neu = h.lesen()
        check("the other servers are still there",
              "[mcp_servers.context7]" in neu
              and "[mcp_servers.other-thing]" in neu)
        check("their arguments are unchanged",
              '"@upstash/context7-mcp"' in neu and '["x.js"]' in neu)
        check("settings outside any table survive",
              'model = "gpt-5"' in neu
              and 'approval_policy = "on-request"' in neu)
        check("our block arrived", "[mcp_servers.pc-screen-control]" in neu)
        check("a backup was made", os.path.isfile(h.config + ".backup"))
        check("the backup holds the ORIGINAL, not the new file",
              open(h.config + ".backup", encoding="utf-8").read() == FREMD)

    print("\n4 - A second run updates instead of duplicating")
    with Heim() as h:
        h.schreiben(FREMD)
        srv._install_write_codex(SRV)
        state, _ = srv._install_write_codex(SRV2)
        neu = h.lesen()
        check("reported as updated", state == "updated", state)
        check("our table appears exactly once",
              neu.count("[mcp_servers.pc-screen-control]") == 1,
              "%d times" % neu.count("[mcp_servers.pc-screen-control]"))
        check("it points at the NEW server",
              "Anders" in neu and "pc-screen-control\\\\server.py" not in neu)
        check("the foreign servers survived the update too",
              "[mcp_servers.context7]" in neu
              and "[mcp_servers.other-thing]" in neu)
        check("the backup was NOT overwritten by the second run",
              open(h.config + ".backup", encoding="utf-8").read() == FREMD)

    print("\n5 - Our block ends at the next table, not at the file's end")
    # This is the line that decides whether an update eats everything below it.
    # If the block were terminated by anything other than the next header, the
    # servers listed after ours would silently disappear on the second run.
    with Heim() as h:
        h.schreiben("[mcp_servers.pc-screen-control]\ncommand = \"old\"\n"
                    "args = [\"old\"]\n\n[mcp_servers.danach]\n"
                    "command = \"keep-me\"\n")
        srv._install_write_codex(SRV)
        neu = h.lesen()
        check("the table after ours is untouched",
              "[mcp_servers.danach]" in neu and '"keep-me"' in neu)
        check("the old command is gone", '"old"' not in neu)

    print("\n6 - No config file yet, but Codex is installed")
    with Heim() as h:
        state, _ = srv._install_write_codex(SRV)
        check("reported as added", state == "added", state)
        check("the file was created", os.path.isfile(h.config))
        check("no backup for a file that never existed",
              not os.path.isfile(h.config + ".backup"))

    print("\n7 - No Codex on the machine: skipped, and nothing is created")
    # An installer that plants a config folder for a program somebody does not
    # have is littering. "skipped" has to mean skipped, on disk as well.
    with Heim(mit_codex=False) as h:
        state, detail = srv._install_write_codex(SRV)
        check("reported as skipped", state == "skipped", state)
        check("no .codex folder was created",
              not os.path.exists(os.path.join(h.dir, ".codex")))
        check("the message says what to do if they DO use Codex",
              "start it" in detail.lower() and "run this again" in detail,
              detail)

    print("\n8 - The installer actually calls it")
    # A writer nothing calls is the same as no writer. Checked in the source,
    # because _install() itself cannot run off Windows.
    quelle = open(os.path.join(SRC, "server.py"), encoding="utf-8").read()
    einbau = quelle.split("def _install():", 1)[1].split("\ndef ", 1)[0]
    check("_install_write_codex is called from _install",
          "_install_write_codex(server_path)" in einbau)
    check("its result is reported like every other client",
          '"Codex / ChatGPT"' in einbau)
    check("its result counts towards 'any client was written'",
          "geschrieben.append((\"Codex / ChatGPT\"" in einbau)

    print("\n9 - A commented-out attempt cannot be mistaken for our entry")
    # This is the defect this release is about, in the writer that fixes it:
    # deciding with `kopf in alt` (anywhere in the text) and replacing with an
    # exact line match meant a commented-out header made it report "updated"
    # and write nothing. Decide and replace now use the same test.
    with Heim() as h:
        h.schreiben('# [mcp_servers.pc-screen-control]\n'
                    '# command = "old"\n\n'
                    '[mcp_servers.context7]\ncommand = "npx"\n')
        state, _ = srv._install_write_codex(SRV)
        neu_txt = h.lesen()
        check("reported as added, not as updated", state == "added", state)
        echte = [z for z in neu_txt.splitlines()
                 if z.strip() == "[mcp_servers.pc-screen-control]"]
        check("a real header line was actually written", len(echte) == 1,
              "%d Kopfzeilen" % len(echte))
        check("the commented-out line is still a comment",
              "# [mcp_servers.pc-screen-control]" in neu_txt)

    print("\n10 - A multi-line array in our block does not eat the next table")
    # The end marker used to be 'line starts with [', which is also true of a
    # value line inside an array written across lines - so replacing our block
    # stopped in the middle of one and left its tail behind as garbage. That
    # does not break our entry, it breaks the whole file, and with it every
    # other MCP server the person has.
    with Heim() as h:
        h.schreiben('[mcp_servers.pc-screen-control]\n'
                    'command = "python"\n'
                    'args = [\n  "a.py",\n  "b.py",\n]\n'
                    '\n[mcp_servers.context7]\ncommand = "npx"\n')
        srv._install_write_codex(SRV)
        neu_txt = h.lesen()
        check("no leftovers from the old array", '"a.py"' not in neu_txt
              and '"b.py"' not in neu_txt, repr(neu_txt[-120:]))
        check("the table after it survived",
              "[mcp_servers.context7]" in neu_txt and '"npx"' in neu_txt)
        check("the result still parses as TOML", toml_ok(neu_txt),
              toml_fehler(neu_txt))

    print("\n11 - Every result of this writer parses as TOML")
    # Not one of the cases above asserted that. A read-back that searches its
    # own text for its own header proves only that its header is in the text.
    for name, vorher in (("foreign config", FREMD),
                         ("empty file", ""),
                         ("no trailing newline", 'model = "gpt-5"'),
                         ("windows line endings", FREMD.replace("\n", "\r\n"))):
        with Heim() as h:
            if vorher:
                h.schreiben(vorher)
            srv._install_write_codex(SRV)
            check("%s -> valid TOML" % name, toml_ok(h.lesen()),
                  toml_fehler(h.lesen()))

    print("\n12 - Removing puts the file back the way it was")
    # --install writes four clients; --uninstall used to clean three and say
    # "every MCP client". The one left behind pointed at a file the same run
    # had just deleted.
    with Heim() as h:
        h.schreiben(FREMD)
        srv._install_write_codex(SRV)
        state, _ = srv._deinstall_codex()
        nachher = h.lesen()
        check("reported as removed", state == "removed", state)
        check("our table is gone",
              "[mcp_servers.pc-screen-control]" not in nachher)
        check("the foreign servers are untouched",
              "[mcp_servers.context7]" in nachher
              and "[mcp_servers.other-thing]" in nachher)
        check("what is left still parses", toml_ok(nachher),
              toml_fehler(nachher))
        check("a copy from before the removal is kept",
              os.path.isfile(h.config + ".before-uninstall"))
    with Heim() as h:
        h.schreiben(FREMD)
        state, _ = srv._deinstall_codex()
        check("nothing of ours in it -> skipped, not failed",
              state == "skipped", state)

    print("\n13 - Installing twice does not destroy a working install")
    # The first version wiped lib/ before copying it. On Windows a .pyd held
    # open by a running server cannot be deleted, rmtree(ignore_errors) hides
    # that, and the copy then fails on a folder that is already there - turning
    # a working installation into a broken one, during a run that INSTALL.bat
    # calls "safe to run more than once". Behaviour, not a search for rmtree.
    quell_dir = tempfile.mkdtemp(prefix="psc_paket_")
    ziel_dir = tempfile.mkdtemp(prefix="psc_ziel_")
    try:
        os.makedirs(os.path.join(quell_dir, "lib", "comtypes", "gen"))
        for p, t in (("server.py", "# server"), ("overlay.py", "# overlay"),
                     ("lib/uiautomation.py", "# ui"),
                     ("lib/comtypes/gen/__init__.py", "# gen")):
            with open(os.path.join(quell_dir, *p.split("/")), "w") as fh:
                fh.write(t)
        # Ein Ziel, das schon steht - und eine Datei darin, die sich nicht
        # loeschen laesst. Genau der Windows-Fall, nur portabel nachgebaut.
        os.makedirs(os.path.join(ziel_dir, "lib", "comtypes", "gen"))
        gehalten = os.path.join(ziel_dir, "lib", "comtypes", "gen",
                                "_gehalten.py")
        with open(gehalten, "w") as fh:
            fh.write("# in use")
        os.chmod(os.path.join(ziel_dir, "lib", "comtypes", "gen"), 0o500)

        alt_datei, alt_dir = srv.__file__, srv.INSTALL_DIR
        try:
            srv.__file__ = os.path.join(quell_dir, "server.py")
            srv.INSTALL_DIR = ziel_dir
            fehler = None
            try:
                srv._install_copy_self()
            except Exception as e:
                fehler = "%s: %s" % (type(e).__name__, e)
            check("a second install does not raise", fehler is None, fehler)
            check("the new libraries arrived",
                  os.path.isfile(os.path.join(ziel_dir, "lib",
                                              "uiautomation.py")))
            check("the file that could not be removed is still there",
                  os.path.isfile(gehalten))
            check("server.py itself was copied",
                  os.path.isfile(os.path.join(ziel_dir, "server.py")))
            check("overlay.py came with it",
                  os.path.isfile(os.path.join(ziel_dir, "overlay.py")))
        finally:
            srv.__file__, srv.INSTALL_DIR = alt_datei, alt_dir
    finally:
        for d in (quell_dir, ziel_dir):
            for wurzel, ordner, _ in os.walk(d):
                for o in ordner:
                    try:
                        os.chmod(os.path.join(wurzel, o), 0o700)
                    except OSError:
                        pass
            shutil.rmtree(d, ignore_errors=True)

    print("\n14 - A source checkout has no lib/ and must not be broken by it")
    quell_dir = tempfile.mkdtemp(prefix="psc_quelle_")
    ziel_dir = tempfile.mkdtemp(prefix="psc_ziel2_")
    try:
        for p in ("server.py", "overlay.py"):
            with open(os.path.join(quell_dir, p), "w") as fh:
                fh.write("# x")
        alt_datei, alt_dir = srv.__file__, srv.INSTALL_DIR
        try:
            srv.__file__ = os.path.join(quell_dir, "server.py")
            srv.INSTALL_DIR = ziel_dir
            srv._install_copy_self()
            check("no lib/ was invented",
                  not os.path.exists(os.path.join(ziel_dir, "lib")))
            check("the server still arrived",
                  os.path.isfile(os.path.join(ziel_dir, "server.py")))
        finally:
            srv.__file__, srv.INSTALL_DIR = alt_datei, alt_dir
    finally:
        shutil.rmtree(quell_dir, ignore_errors=True)
        shutil.rmtree(ziel_dir, ignore_errors=True)

    print("\n" + "=" * 66)
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("test_codex_install: all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
