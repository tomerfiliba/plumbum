import pytest
import os
import sys

try:
    import pathlib
except ImportError:
    patlib = None

skip_without_pathlib = pytest.mark.skipif(pathlib is None,
        reason="This requires pathlib to be installed")

skip_without_chown = pytest.mark.skipif(not hasattr(os, "chown"),
        reason="os.chown not supported")

skip_without_tty = pytest.mark.skipif(not sys.stdin.isatty(),
        reason="Not a TTY")

skip_on_windows = pytest.mark.skipif(sys.platform == "win32",
        reason="Windows not supported for this test (yet)")
