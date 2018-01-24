# Setting French as system language
import os
os.environ['LC_ALL'] = 'fr_FR.utf-8'

import pytest
import sys

from plumbum import cli

class Simple(cli.Application):
    foo = cli.SwitchAttr("--foo")

    def main(self):
        pass

class TestFRCLI:
    def test_nolang_switches(self):
        _, rc = Simple.run(["foo", "-h"], exit = False)
        assert rc == 0
        _, rc = Simple.run(["foo", "--version"], exit = False)
        assert rc == 0

    def test_help_lang(self, capsys):
        _, rc = Simple.run(["foo", "-h"], exit = False)
        assert rc == 0
        stdout, stderr = capsys.readouterr()
        assert "Utilisation" in stdout
        assert "Imprime ce message d'aide et sort" in stdout
