from __future__ import annotations

import plumbum.cmd
from plumbum.fs import mounts


def test_mount_entry_string_and_options() -> None:
    entry = mounts.MountEntry("/dev/disk1s1", "/", "apfs", "rw,nosuid")

    assert entry.options == ["rw", "nosuid"]
    assert str(entry) == "/dev/disk1s1 on / type apfs (rw,nosuid)"


def test_mount_entry_without_options() -> None:
    entry = mounts.MountEntry(
        "map auto_home", "/System/Volumes/Data/home", "autofs", None
    )

    assert entry.options == []
    assert str(entry) == "map auto_home on /System/Volumes/Data/home type autofs ()"


def test_mount_table_parses_only_matching_lines(monkeypatch) -> None:
    sample = "\n".join(
        [
            "/dev/disk1s1 on / type apfs (rw,local,journaled)",
            "map auto_home on /System/Volumes/Data/home type autofs (automounted,static)",
            "not a mount line",
        ]
    )

    monkeypatch.setattr(plumbum.cmd, "mount", lambda: sample)

    table = mounts.mount_table()

    assert len(table) == 2
    assert table[0].dev == "/dev/disk1s1"
    assert table[0].point == "/"
    assert table[0].fstype == "apfs"
    assert table[0].options == ["rw", "local", "journaled"]
    assert table[1].dev == "map auto_home"


def test_mounted_checks_device_and_mount_point(monkeypatch) -> None:
    monkeypatch.setattr(
        mounts,
        "mount_table",
        lambda: [
            mounts.MountEntry("/dev/disk1s1", "/", "apfs", "rw"),
            mounts.MountEntry("map auto_home", "/home", "autofs", "rw"),
        ],
    )

    assert mounts.mounted("/dev/disk1s1")
    assert mounts.mounted("/home")
    assert not mounts.mounted("/not-mounted")
