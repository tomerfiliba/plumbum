from __future__ import annotations

import pytest

from plumbum import cli
from plumbum.cli.application import SwitchCombinationError


class Main3Validator(cli.Application):
    def main(self, myint: int, myint2: int, *mylist: int):
        print(myint, myint2, mylist)


class TestProg3:
    def test_prog(self, capsys):
        _, rc = Main3Validator.run(["prog", "1", "2", "3", "4", "5"], exit=False)
        assert rc == 0
        assert "1 2 (3, 4, 5)" in capsys.readouterr()[0]


class Main4Validator(cli.Application):
    def main(self, myint: int, myint2: int, *mylist: int) -> None:
        print(myint, myint2, mylist)


class TestProg4:
    def test_prog(self, capsys):
        _, rc = Main4Validator.run(["prog", "1", "2", "3", "4", "5"], exit=False)
        assert rc == 0
        assert "1 2 (3, 4, 5)" in capsys.readouterr()[0]


class SwitchCombinationApp(cli.Application):
    flag_a = cli.Flag("--flag-a")
    flag_b = cli.Flag("--flag-b", excludes=["--flag-a"])
    flag_c = cli.Flag("--flag-c", requires=["--flag-a"])

    def main(self):
        pass


class TestSwitchCombination:
    def test_excludes_no_crash(self):
        # Regression: defining excludes= crashed with "unhashable type: SwitchInfo"
        # before SwitchInfo was made a frozen dataclass
        _, rc = SwitchCombinationApp.run(["prog", "--flag-b"], exit=False)
        assert rc == 0

    def test_excludes_raises_on_conflict(self):
        with pytest.raises(SwitchCombinationError):
            SwitchCombinationApp.run(["prog", "--flag-a", "--flag-b"], exit=False)

    def test_requires_raises_when_missing(self):
        with pytest.raises(SwitchCombinationError):
            SwitchCombinationApp.run(["prog", "--flag-c"], exit=False)

    def test_requires_ok_when_present(self):
        _, rc = SwitchCombinationApp.run(["prog", "--flag-a", "--flag-c"], exit=False)
        assert rc == 0
