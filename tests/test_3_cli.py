# -*- coding: utf-8 -*-

from plumbum import cli


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
