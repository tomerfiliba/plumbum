#!/usr/bin/env python
import os

try:
    from setuptools import setup, Command
except ImportError:
    from distutils.core import setup, Command

HERE = os.path.dirname(__file__)
exec(open(os.path.join(HERE, "plumbum", "version.py")).read())

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

setup(name = "plumbum",
    version = version_string,  # @UndefinedVariable
    description = "Plumbum: shell combinators library",
    author = "Tomer Filiba",
    author_email = "tomerfiliba@gmail.com",
    license = "MIT",
    url = "http://plumbum.readthedocs.org",
    packages = ["plumbum", "plumbum.cli", "plumbum.commands", "plumbum.machines", "plumbum.path", "plumbum.fs", "plumbum.colorlib"],
    platforms = ["POSIX", "Windows"],
    provides = ["plumbum"],
    keywords = "path, local, remote, ssh, shell, pipe, popen, process, execution, color, cli",
    cmdclass = {
                'docs':PyDocs},
    # use_2to3 = False,
    # zip_safe = True,
    long_description = open(os.path.join(HERE, "README.rst"), "r").read(),
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Topic :: Software Development :: Build Tools",
        "Topic :: System :: Systems Administration",
    ],
)

