# Setting French as system language
from __future__ import annotations

import importlib
import locale

import pytest

import plumbum.cli
import plumbum.cli.i18n


def reload_cli():
    importlib.reload(plumbum.cli.i18n)
    importlib.reload(plumbum.cli.switches)
    importlib.reload(plumbum.cli.application)
    importlib.reload(plumbum.cli)


@pytest.fixture()
def french():
    try:
        locale.setlocale(locale.LC_ALL, "fr_FR.utf-8")
        reload_cli()
        yield
    except locale.Error:
        pytest.skip(
            "No fr_FR locale found, run 'sudo locale-gen fr_FR.UTF-8' to run this test"
        )
    finally:
        locale.setlocale(locale.LC_ALL, "")
        reload_cli()


@pytest.mark.usefixtures("french")
def test_nolang_switches():
    class Simple(plumbum.cli.Application):
        foo = plumbum.cli.SwitchAttr("--foo")

        def main(self):
            pass

    _, rc = Simple.run(["foo", "-h"], exit=False)
    assert rc == 0
    _, rc = Simple.run(["foo", "--version"], exit=False)
    assert rc == 0


@pytest.mark.usefixtures("french")
def test_help_lang(capsys):
    class Simple(plumbum.cli.Application):
        foo = plumbum.cli.SwitchAttr("--foo")

        def main(self):
            pass

    _, rc = Simple.run(["foo", "-h"], exit=False)
    assert rc == 0
    stdout, stderr = capsys.readouterr()
    assert "Utilisation" in stdout
    assert "Imprime ce message d'aide et sort" in stdout
