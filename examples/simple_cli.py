#!/usr/bin/env python
"""
$ python simple_cli.py --help
simple_cli.py v1.0

Usage: simple_cli.py [SWITCHES] srcfiles...
Meta-switches:
    -h, --help                 Prints this help message and quits
    --version                  Prints the program's version and quits

Switches:
    -I VALUE:str               Specify include directories; may be given
                               multiple times
    --loglevel LEVEL:int       Sets the log-level of the logger
    -v, --verbose              Enable verbose mode

$ python simple_cli.py x.cpp y.cpp z.cpp
Verbose: False
Include dirs: []
Compiling: ('x.cpp', 'y.cpp', 'z.cpp')

$ python simple_cli.py -v
Verbose: True
Include dirs: []
Compiling: ()

$ python simple_cli.py -v -Ifoo/bar -Ispam/eggs
Verbose: True
Include dirs: ['foo/bar', 'spam/eggs']
Compiling: ()

$ python simple_cli.py -v -I foo/bar -Ispam/eggs x.cpp y.cpp z.cpp
Verbose: True
Include dirs: ['foo/bar', 'spam/eggs']
Compiling: ('x.cpp', 'y.cpp', 'z.cpp')
"""
import logging
from plumbum import cli


class MyCompiler(cli.Application):
    verbose = cli.Flag(["-v", "--verbose"], help = "Enable verbose mode")
    include_dirs = cli.SwitchAttr("-I", list = True, help = "Specify include directories")

    @cli.switch("-loglevel", int)
    def set_log_level(self, level):
        """Sets the log-level of the logger"""
        logging.root.setLevel(level)

    def main(self, *srcfiles):
        print "Verbose:", self.verbose
        print "Include dirs:", self.include_dirs
        print "Compiling:", srcfiles


if __name__ == "__main__":
    MyCompiler.run()

