from __future__ import annotations

import os
from typing import TYPE_CHECKING, cast

import pytest

from plumbum import lib

if TYPE_CHECKING:
    from io import StringIO


class _NoDocAttr:
    def __getattribute__(self, name: str):
        if name == "__doc__":
            raise AttributeError
        return super().__getattribute__(name)


def test_captured_stdout_restores_streams() -> None:
    orig_stdin = lib.sys.stdin
    orig_stdout = lib.sys.stdout

    with lib.captured_stdout("hello\n") as out:
        print("written")
        assert lib.sys.stdin.readline() == "hello\n"
        assert cast("StringIO", out).getvalue() == "written\n"

    assert lib.sys.stdin is orig_stdin
    assert lib.sys.stdout is orig_stdout


def test_static_property_access_via_class_and_instance() -> None:
    class Holder:
        value = 0

        @lib.StaticProperty
        def token():
            Holder.value += 1
            return Holder.value

    assert Holder.token == 1
    assert Holder().token == 2


def test_getdoc_handles_attribute_error() -> None:
    assert lib.getdoc(_NoDocAttr()) is None


def test_read_fd_decode_safely_handles_partial_utf8() -> None:
    # UTF-8 3-byte character read in too-small chunks first.
    payload = b"\xe2\x82\xac"
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, payload)
        os.close(write_fd)
        write_fd = None

        with os.fdopen(read_fd, "rb", closefd=True) as stream:
            data, text = lib.read_fd_decode_safely(stream, size=1)  # type: ignore[arg-type]

        assert data == payload
        assert text == payload.decode("utf-8")
    finally:
        if write_fd is not None:
            os.close(write_fd)


def test_read_fd_decode_safely_raises_on_invalid_sequence() -> None:
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, b"\xff")
        os.close(write_fd)
        write_fd = None

        with (
            os.fdopen(read_fd, "rb", closefd=True) as stream,
            pytest.raises(UnicodeDecodeError),
        ):
            lib.read_fd_decode_safely(stream, size=1)  # type: ignore[arg-type]
    finally:
        if write_fd is not None:
            os.close(write_fd)


def test_read_fd_decode_safely_raises_when_stream_ends_mid_char() -> None:
    # One byte of a 4-byte UTF-8 sequence forces retry loop then final decode failure.
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, b"\xf0")
        os.close(write_fd)
        write_fd = None

        with (
            os.fdopen(read_fd, "rb", closefd=True) as stream,
            pytest.raises(UnicodeDecodeError),
        ):
            lib.read_fd_decode_safely(stream, size=1)  # type: ignore[arg-type]
    finally:
        if write_fd is not None:
            os.close(write_fd)
