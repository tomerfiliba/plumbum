from __future__ import annotations

import pytest

from plumbum.lib import IS_WIN32
from plumbum.commands import CommandNotFound

from plumbum import local

if IS_WIN32:
    # POSIX compatibility aliases on Windows (via Git for Windows)
    try:
        GIT_PATH = local.which("git")
    except CommandNotFound:
        GIT_BIN_PATH = None
    else:
        GIT_BIN_PATH = GIT_PATH.dirname.dirname.join("usr/bin")
    if GIT_BIN_PATH:
        GIT_ALIASES = {
            "bash":     GIT_BIN_PATH.join("bash.exe"),
            "ls":       GIT_BIN_PATH.join("ls.exe"),
            "pwd":      GIT_BIN_PATH.join("pwd.exe"),
            "rm":       GIT_BIN_PATH.join("rm.exe"),
            "mv":       GIT_BIN_PATH.join("mv.exe"),
            "cp":       GIT_BIN_PATH.join("cp.exe"),
            "sleep":    GIT_BIN_PATH.join("sleep.exe"),
            "head":     GIT_BIN_PATH.join("head.exe"),
            "tail":     GIT_BIN_PATH.join("tail.exe"),
            "printf":   GIT_BIN_PATH.join("printf.exe"),
            "wc":       GIT_BIN_PATH.join("wc.exe"),
            "touch":    GIT_BIN_PATH.join("touch.exe"),
            "cat":      GIT_BIN_PATH.join("cat.exe"),
            "grep":     GIT_BIN_PATH.join("grep.exe"),
            "echo":     GIT_BIN_PATH.join("echo.exe"),
            "date":     GIT_BIN_PATH.join("date.exe"),
            "uniq":     GIT_BIN_PATH.join("uniq.exe"),
            "truncate": GIT_BIN_PATH.join("truncate.exe"),
            "clear":    GIT_BIN_PATH.join("clear.exe"),
            "basename": GIT_BIN_PATH.join("basename.exe"),
            "dirname":  GIT_BIN_PATH.join("dirname.exe"),
        }
        for name, exe_path in GIT_ALIASES.items():
            local.alias(name, exe_path)

skip_if_no_posix_tools = pytest.mark.skipif(
    IS_WIN32 and GIT_BIN_PATH is None,
    reason="POSIX aliases unavailable (Git for Windows not found)"
)
