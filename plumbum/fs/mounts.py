from __future__ import annotations

import re


class MountEntry:
    """
    Represents a mount entry (device file, mount point and file system type)
    """

    def __init__(self, dev: str, point: str, fstype: str, options: str | None):
        self.dev = dev
        self.point = point
        self.fstype = fstype
        self.options = options.split(",") if options else []

    def __str__(self) -> str:
        options = ",".join(self.options)
        return f"{self.dev} on {self.point} type {self.fstype} ({options})"


MOUNT_PATTERN = re.compile(r"(.+?)\s+on\s+(.+?)\s+type\s+(\S+)(?:\s+\((.+?)\))?")


def mount_table() -> list[MountEntry]:
    """Returns the system's current mount table (a list of
    :class:`MountEntry <plumbum.unixutils.MountEntry>` objects)"""
    from plumbum.cmd import mount

    table = []
    for line in mount().splitlines():
        m = MOUNT_PATTERN.match(line)
        if m:
            table.append(MountEntry(*m.groups()))
    return table


def mounted(fs: str) -> bool:
    """
    Indicates if the given filesystem (device file or mount point) is currently mounted
    """
    return any(fs in {entry.dev, entry.point} for entry in mount_table())
