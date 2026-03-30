import sys

import pytest

from plumbum import async_local, local

cmd1 = "print('test pipe1\\ntest pipe2')"
cmd2 = """
import sys
for line in sys.stdin:
    print(line.strip().upper())
"""


def test_issue_795_sync():
    echo = local[sys.executable]["-c", cmd1]
    upper = local[sys.executable]["-c", cmd2]

    command = echo | upper

    proc = command.popen()
    assert proc.stdout is not None
    lines = []
    while i := proc.stdout.readline():
        lines.append(i.decode().strip())

    assert len(lines) == 2
    assert lines == ["TEST PIPE1", "TEST PIPE2"]
    # Ensure child processes are reaped and return code is checked
    proc.wait()
    assert proc.returncode == 0


@pytest.mark.asyncio
async def test_issue_795_async():
    echo = async_local[sys.executable]["-c", cmd1]
    upper = async_local[sys.executable]["-c", cmd2]

    command = echo | upper

    proc = await command.popen()
    assert proc.stdout is not None
    lines = []
    while i := await proc.stdout.readline():
        lines.append(i.decode().strip())

    assert len(lines) == 2
    assert lines == ["TEST PIPE1", "TEST PIPE2"]
    # Ensure child processes are reaped and return code is checked
    await proc.wait()
    assert proc.returncode == 0
