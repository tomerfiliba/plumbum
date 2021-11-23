# -*- coding: utf-8 -*-
"""Test that PuttyMachine initializes its SshMachine correctly"""

import env
import pytest

from plumbum import PuttyMachine, SshMachine


@pytest.fixture(params=["default", "322"])
def ssh_port(request):
    return request.param


class TestPuttyMachine:
    @pytest.mark.skipif(env.PYPY & env.PY2, reason="PyPy2 doesn't support mocker.spy")
    def test_putty_command(self, mocker, ssh_port):
        local = mocker.patch("plumbum.machines.ssh_machine.local")
        init = mocker.spy(SshMachine, "__init__")
        mocker.patch("plumbum.machines.ssh_machine.BaseRemoteMachine")

        host = mocker.MagicMock()
        user = local.env.user
        port = keyfile = None
        ssh_command = local["plink"]
        scp_command = local["pscp"]
        ssh_opts = ["-ssh"]
        if ssh_port == "default":
            putty_port = None
            scp_opts = ()
        else:
            putty_port = int(ssh_port)
            ssh_opts.extend(["-P", ssh_port])
            scp_opts = ["-P", ssh_port]
        encoding = mocker.MagicMock()
        connect_timeout = 20
        new_session = True

        PuttyMachine(
            host,
            port=putty_port,
            connect_timeout=connect_timeout,
            new_session=new_session,
            encoding=encoding,
        )

        init.assert_called_with(
            mocker.ANY,
            host,
            user,
            port,
            keyfile=keyfile,
            ssh_command=ssh_command,
            scp_command=scp_command,
            ssh_opts=ssh_opts,
            scp_opts=scp_opts,
            encoding=encoding,
            connect_timeout=connect_timeout,
            new_session=new_session,
        )

    def test_putty_str(self, mocker):
        local = mocker.patch("plumbum.machines.ssh_machine.local")
        mocker.patch("plumbum.machines.ssh_machine.BaseRemoteMachine")

        host = mocker.MagicMock()
        user = local.env.user

        machine = PuttyMachine(host)
        assert str(machine) == "putty-ssh://{}@{}".format(user, host)
