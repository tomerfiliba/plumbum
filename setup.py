#!/usr/bin/env python
import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

HERE = os.path.dirname(__file__)
exec(open(os.path.join(HERE, "plumbum", "version.py")).read())

setup(name = "plumbum",
    version = version_string, #@UndefinedVariable
    description = "Plumbum: shell combinators library",
    author = "Tomer Filiba",
    author_email = "tomerfiliba@gmail.com",
    license = "MIT",
    url = "https://github.com/tomerfiliba/plumbum",
    packages = ["plumbum"],
    platforms = ["POSIX", "Windows"],
    install_requires = ["six"],
    use_2to3 = False,
    #zip_safe = True,
    long_description = open(os.path.join(HERE, "README.rst"), "r").read(),
    classifiers = [
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.0",
        "Programming Language :: Python :: 3.1",
        "Programming Language :: Python :: 3.2",
        "Topic :: System :: Systems Administration",
    ],
)

