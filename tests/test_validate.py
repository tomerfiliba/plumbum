# -*- coding: utf-8 -*-
import unittest
from plumbum import cli
from plumbum.lib import captured_stdout, ensure_skipIf
from plumbum.lib import six

class MainValidator(cli.Application):
    @cli.validate(int, int, int)
    def main(self, myint, myint2, *mylist):
        print(myint, myint2, mylist)

class TestValidator(unittest.TestCase):
    def test_named(self):
        class Try(object):
            @cli.validate(x=abs, y=str)
            def main(selfy, x, y):
                pass

        self.assertEqual(Try.main.positional, [abs, str])
        self.assertEqual(Try.main.positional_varargs, None)

    def test_position(self):
        class Try(object):
            @cli.validate(abs, str)
            def main(selfy, x, y):
                pass

        self.assertEqual(Try.main.positional, [abs, str])
        self.assertEqual(Try.main.positional_varargs, None)
        
    def test_mix(self):  
        class Try(object):
            @cli.validate(abs, str, d=bool)
            def main(selfy, x, y, z, d):
                pass

        self.assertEqual(Try.main.positional, [abs, str, None, bool])
        self.assertEqual(Try.main.positional_varargs, None)
        
    def test_var(self):
        class Try(object):
            @cli.validate(abs, str, int)
            def main(selfy, x, y, *g):
                pass

        self.assertEqual(Try.main.positional, [abs, str])
        self.assertEqual(Try.main.positional_varargs, int)
        
class TestProg(unittest.TestCase):
    def test_prog(self):
        with captured_stdout() as stream:
            _, rc = MainValidator.run(["prog", "1", "2", '3', '4', '5'], exit = False)
        self.assertEqual(rc, 0)
        self.assertIn("1 2 (3, 4, 5)", stream.getvalue())
   
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