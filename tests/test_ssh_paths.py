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


class TestScpTranslatesLocalSideOnly:
    """Only the local path is parsed by the local scp binary, so only it may
    be drive-letter translated; the remote path must be passed through verbatim.
    """

    def _make(self, mocker, translate):
        mocker.patch("plumbum.machines.ssh_machine.BaseRemoteMachine")
        m = SshMachine("host", ssh_command=local["ssh"], scp_command=local["scp"])
        m._scp_translate = translate
        m._scp_command = mocker.MagicMock()
        return m

    def test_download_translates_only_local_dst(self, mocker):
        m = self._make(mocker, translate=True)
        # remote src has a colon (legal in POSIX filenames); local dst is Windows
        m.download("/tmp/a:b", r"c:\Users\foo")
        local_remote = m._scp_command.call_args[0]
        # remote src passed through untouched (colon preserved, no /c rewrite)
        assert local_remote[0] == "host:/tmp/a:b"
        # local dst translated
        assert local_remote[1] == "/c/Users/foo"

    def test_upload_translates_only_local_src(self, mocker):
        m = self._make(mocker, translate=True)
        # local src is Windows; remote dst has a colon
        m.upload(r"c:\Users\foo", "/tmp/a:b")
        local_remote = m._scp_command.call_args[0]
        # local src translated
        assert local_remote[0] == "/c/Users/foo"
        # remote dst passed through untouched
        assert local_remote[1] == "host:/tmp/a:b"

    def test_no_translation_when_disabled(self, mocker):
        m = self._make(mocker, translate=False)
        m.upload(r"c:\Users\foo", "/remote/dst")
        local_remote = m._scp_command.call_args[0]
        assert local_remote[0] == r"c:\Users\foo"
