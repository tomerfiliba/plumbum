#!/usr/bin/env python
import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

exec(open(os.path.join(os.path.dirname(__file__), 'plumbum', 'version.py')).read())

setup(name = "plumbum",
    version = version_string, #@UndefinedVariable
    description = "Plumbum: shell combinators library",
    author = "Tomer Filiba",
    author_email = "tomerfiliba@gmail.com",
    license = "MIT",
    url = "http://plumbum.readthedocs.org",
    packages = [
        'plumbum',
    ],
    platforms = ["POSIX", "Windows"],
    use_2to3 = False,
    zip_safe = True,
    long_description = """Plumbum (Latin for *lead*) is a small yet very functional library for 
writing shell-script-like programs in Python. Plumbum treats programs as first-class objects, 
which you can invoke to run the program, or form pipelines, just like you'd do in shell scripts.
The idea is to never have to write shell scripts again.

See http://plumbum.readthedocs.org for more info.""",
    classifiers = [
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        #"Programming Language :: Python :: 3",
        #"Programming Language :: Python :: 3.0",
        #"Programming Language :: Python :: 3.1",
        #"Programming Language :: Python :: 3.2",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
    ],
)

