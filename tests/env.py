import os
import platform
import sys

LINUX = sys.platform.startswith("linux")
MACOS = sys.platform.startswith("darwin")
WIN = sys.platform.startswith("win32") or sys.platform.startswith("cygwin")

CPYTHON = platform.python_implementation() == "CPython"
PYPY = platform.python_implementation() == "PyPy"

IS_A_TTY = sys.stdin.isatty()
HAS_CHOWN = hasattr(os, "chown")
