# -*- coding: utf-8 -*-
from __future__ import print_function, division
from plumbum import cli
from plumbum.lib import six

class TestValidator:
    def test_named(self):
        class Try(object):
            @cli.positional(x=abs, y=str)
            def main(selfy, x, y):
                pass

        assert Try.main.positional == [abs, str]
        assert Try.main.positional_varargs == None

    def test_position(self):
        class Try(object):
            @cli.positional(abs, str)
            def main(selfy, x, y):
                pass

        assert Try.main.positional == [abs, str]
        assert Try.main.positional_varargs == None

    def test_mix(self):
        class Try(object):
            @cli.positional(abs, str, d=bool)
            def main(selfy, x, y, z, d):
                pass

        assert Try.main.positional == [abs, str, None, bool]
        assert Try.main.positional_varargs == None

    def test_var(self):
        class Try(object):
            @cli.positional(abs, str, int)
            def main(selfy, x, y, *g):
                pass

        assert Try.main.positional == [abs, str]
        assert Try.main.positional_varargs == int

    def test_defaults(self):
        class Try(object):
            @cli.positional(abs, str)
            def main(selfy, x, y = 'hello'):
                pass

        assert Try.main.positional == [abs, str]


class TestProg:
    def test_prog(self, capsys):
        class MainValidator(cli.Application):
            @cli.positional(int, int, int)
            def main(self, myint, myint2, *mylist):
                print(repr(myint), myint2, mylist)

        _, rc = MainValidator.run(["prog", "1", "2", '3', '4', '5'], exit = False)
        assert rc == 0
        assert "1 2 (3, 4, 5)" == capsys.readouterr()[0].strip()


    def test_failure(self, capsys):
        class MainValidator(cli.Application):
            @cli.positional(int, int, int)
            def main(self, myint, myint2, *mylist):
                print(myint, myint2, mylist)
        _, rc = MainValidator.run(["prog", "1.2", "2", '3', '4', '5'], exit = False)

        assert rc == 2
        value = capsys.readouterr()[0].strip()
        assert 'int' in value
        assert 'not' in value
        assert '1.2' in value


    def test_defaults(self, capsys):
        class MainValidator(cli.Application):
            @cli.positional(int, int)
            def main(self, myint, myint2=2):
                print(repr(myint), repr(myint2))

        _, rc = MainValidator.run(["prog", "1"], exit = False)
        assert rc == 0
        assert "1 2" == capsys.readouterr()[0].strip()

        _, rc = MainValidator.run(["prog", "1", "3"], exit = False)
        assert rc == 0
        assert "1 3" ==  capsys.readouterr()[0].strip()


# Unfortionatly, Py3 anotations are a syntax error in Py2, so using exec to add test for Py3
if six.PY3:
    exec("""
class Main3Validator(cli.Application):
    def main(self, myint:int, myint2:int, *mylist:int):
        print(myint, myint2, mylist)
class TestProg3:
    def test_prog(self, capsys):
        _, rc = Main3Validator.run(["prog", "1", "2", '3', '4', '5'], exit = False)
        assert rc == 0
        assert "1 2 (3, 4, 5)" in capsys.readouterr()[0]""")
