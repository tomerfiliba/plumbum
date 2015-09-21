# -*- coding: utf-8 -*-
from __future__ import print_function, division
import unittest
from plumbum import cli
from plumbum.lib import captured_stdout
from plumbum.lib import six

class TestValidator(unittest.TestCase):
    def test_named(self):
        class Try(object):
            @cli.positional(x=abs, y=str)
            def main(selfy, x, y):
                pass

        self.assertEqual(Try.main.positional, [abs, str])
        self.assertEqual(Try.main.positional_varargs, None)

    def test_position(self):
        class Try(object):
            @cli.positional(abs, str)
            def main(selfy, x, y):
                pass

        self.assertEqual(Try.main.positional, [abs, str])
        self.assertEqual(Try.main.positional_varargs, None)

    def test_mix(self):
        class Try(object):
            @cli.positional(abs, str, d=bool)
            def main(selfy, x, y, z, d):
                pass

        self.assertEqual(Try.main.positional, [abs, str, None, bool])
        self.assertEqual(Try.main.positional_varargs, None)

    def test_var(self):
        class Try(object):
            @cli.positional(abs, str, int)
            def main(selfy, x, y, *g):
                pass

        self.assertEqual(Try.main.positional, [abs, str])
        self.assertEqual(Try.main.positional_varargs, int)
        
    def test_defaults(self):
        class Try(object):
            @cli.positional(abs, str)
            def main(selfy, x, y = 'hello'):
                pass
            
        self.assertEqual(Try.main.positional, [abs, str])


class TestProg(unittest.TestCase):
    def test_prog(self):
        class MainValidator(cli.Application):
            @cli.positional(int, int, int)
            def main(self, myint, myint2, *mylist):
                print(repr(myint), myint2, mylist)        
        
        with captured_stdout() as stream:
            _, rc = MainValidator.run(["prog", "1", "2", '3', '4', '5'], exit = False)
        self.assertEqual(rc, 0)
        self.assertEqual("1 2 (3, 4, 5)", stream.getvalue().strip())


    def test_failure(self):
        class MainValidator(cli.Application):
            @cli.positional(int, int, int)
            def main(self, myint, myint2, *mylist):
                print(myint, myint2, mylist)
        with captured_stdout() as stream:
            _, rc = MainValidator.run(["prog", "1.2", "2", '3', '4', '5'], exit = False)
        self.assertEqual(rc, 2)
        value = stream.getvalue().strip()
        self.assertTrue("'int'>, not '1.2':" in value)
        self.assertTrue(" 'int'>, not '1.2':" in value)
        self.assertTrue('''ValueError("invalid literal for int() with base 10: '1.2'"''' in value)

    def test_defaults(self):
        class MainValidator(cli.Application):
            @cli.positional(int, int)
            def main(self, myint, myint2=2):
                print(repr(myint), repr(myint2))        
        
        with captured_stdout() as stream:
            _, rc = MainValidator.run(["prog", "1"], exit = False)
        self.assertEqual(rc, 0)
        self.assertEqual("1 2", stream.getvalue().strip())
        
        with captured_stdout() as stream:
            _, rc = MainValidator.run(["prog", "1", "3"], exit = False)
        self.assertEqual(rc, 0)
        self.assertEqual("1 3", stream.getvalue().strip())

# Unfortionatly, Py3 anotations are a syntax error in Py2, so using exec to add test for Py3
if six.PY3:
    exec("""
class Main3Validator(cli.Application):
    def main(self, myint:int, myint2:int, *mylist:int):
        print(myint, myint2, mylist)
class TestProg3(unittest.TestCase):
    def test_prog(self):
        with captured_stdout() as stream:
            _, rc = Main3Validator.run(["prog", "1", "2", '3', '4', '5'], exit = False)
        self.assertEqual(rc, 0)
        self.assertIn("1 2 (3, 4, 5)", stream.getvalue())""")
