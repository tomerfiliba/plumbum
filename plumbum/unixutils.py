import re
from plumbum.cmd import mount


MOUNT_PATTERN = re.compile(r"(.+?)\s+on\s+(.+?)\s+type\s+(\S+)")

class MountEntry(object):
    """
    Represents a mount entry (device file, mount point and file system type) 
    """
    def __init__(self, dev, point, type):
        self.dev = dev
        self.point = point
        self.type = type
    def __str__(self):
        return "%s on %s, %s" % (self.dev, self.point, self.type)

def mount_table():
    """returns the system's current mount table (a list of 
    :class:`MountEntry <plumbum.unixutils.MountEntry>` objects)"""
    table = []
    for line in mount().splitlines():
        m = MOUNT_PATTERN.match(line)
        if not m:
            continue
        table.append(MountEntry(*m.groups()))
    return table

def mounted(fs):
    """
    Indicates if a the given filesystem (device file or mount point) is currently mounted
    """
    table = mount_table()
    for entry in table:
        if fs == entry.dev or fs == entry.point:
            return True
    return False



