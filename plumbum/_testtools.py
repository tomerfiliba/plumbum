import os
import sys
import unittest
from plumbum import local
from plumbum.lib import IS_WIN32

def ensure_skipIf(unittest):
    """
    This will ensure that unittest has skipIf. Call like::

        import unittest
        ensure_skipIf(unittest)
    """

    if not hasattr(unittest, "skipIf"):
        import logging
        import functools
        def skipIf(condition, reason):
            def deco(func):
                if not condition:
                    return func
                else:
                    @functools.wraps(func)
                    def wrapper(*args, **kwargs):
                        logging.warn("skipping test: "+reason)
                    return wrapper
            return deco
        unittest.skipIf = skipIf

ensure_skipIf(unittest)
skipIf = unittest.skipIf

skip_on_windows = unittest.skipIf(IS_WIN32, "Does not work on Windows (yet)")
skip_without_chown = unittest.skipIf(not hasattr(os, "chown"), "os.chown not supported")
skip_without_tty = unittest.skipIf(not sys.stdin.isatty(), "Not a TTY")
