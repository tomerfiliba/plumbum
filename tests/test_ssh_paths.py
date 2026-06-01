"""Tests for SshMachine local-path handling used by scp upload/download."""

from __future__ import annotations

import pytest

from plumbum import SshMachine, local


class TestTranslateDriveLetter:
    def test_translates_windows_drive(self):
        assert SshMachine._translate_drive_letter(r"c:\Users\foo") == "/c/Users/foo"

    def test_leaves_posix_path_untouched(self):
        assert SshMachine._translate_drive_letter("/home/foo") == "/home/foo"


class TestScpUsesPosixPaths:
    @pytest.mark.parametrize("dll", ["cygwin1.dll", "msys-2.0.dll"])
    def test_detects_cygwin_msys_runtime(self, tmp_path, dll):
        (tmp_path / dll).touch()
        scp = local[tmp_path / "scp"]["-r"]
        assert SshMachine._scp_uses_posix_paths(scp) is True

    def test_native_scp_needs_no_translation(self, tmp_path):
        scp = local[tmp_path / "scp"]["-r"]
        assert SshMachine._scp_uses_posix_paths(scp) is False


class TestScpTranslateGating:
    def _make(self, mocker, tmp_path):
        mocker.patch("plumbum.machines.ssh_machine.BaseRemoteMachine")
        return SshMachine(
            "host",
            ssh_command=local[tmp_path / "ssh"],
            scp_command=local[tmp_path / "scp"],
        )

    def test_no_translation_off_windows(self, mocker, tmp_path):
        (tmp_path / "msys-2.0.dll").touch()
        mocker.patch("plumbum.machines.ssh_machine.IS_WIN32", False)
        assert self._make(mocker, tmp_path)._scp_translate is False

    def test_translation_on_windows_with_cygwin_scp(self, mocker, tmp_path):
        (tmp_path / "cygwin1.dll").touch()
        mocker.patch("plumbum.machines.ssh_machine.IS_WIN32", True)
        assert self._make(mocker, tmp_path)._scp_translate is True

    def test_no_translation_on_windows_with_native_scp(self, mocker, tmp_path):
        mocker.patch("plumbum.machines.ssh_machine.IS_WIN32", True)
        assert self._make(mocker, tmp_path)._scp_translate is False
