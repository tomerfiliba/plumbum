#!/usr/bin/env python
import os
from setuptools import setup, Command
from datetime import date

# Fix for building on non-Windows systems
import codecs
try:
    codecs.lookup('mbcs')
except LookupError:
    ascii = codecs.lookup('ascii')
    func = lambda name, enc=ascii: {True: enc}.get(name=='mbcs')
    codecs.register(func)

class PyDocs(Command):
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        import subprocess
        import sys
        os.chdir('docs')
        errno = subprocess.call(['make', 'html'])
        sys.exit(errno)

class PyTest(Command):
    user_options = [('cov', 'c', 'Produce coverage'),
                    ('report', 'r', 'Produce html coverage report')]

    def initialize_options(self):
        self.cov = None
        self.report = None
    def finalize_options(self):
        pass
    def run(self):
        import sys, subprocess
        proc = [sys.executable, '-m', 'pytest']
        if self.cov or self.report:
            proc += ['--cov','--cov-config=.coveragerc']
        if self.report:
            proc += ['--cov-report=html']
        errno = subprocess.call(proc)
        raise SystemExit(errno)

setup(cmdclass = {'test':PyTest, 'docs':PyDocs})
