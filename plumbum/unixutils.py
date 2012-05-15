import re
from plumbum.cmd import mount

MOUNTED_PATTERN = re.compile(r"(.+?) on (.+?) type")

def mounted(fs):
    """
    Returns True if a the given filesystem is currently mounted.
    """
    for line in mount().splitlines():
        m = MOUNTED_PATTERN.match(line)
        if fs in m.groups():
            return True

    return False
