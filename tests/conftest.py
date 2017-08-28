import pytest
import os
import sys
import tempfile

if sys.version_info[0] < 3:
    collect_ignore = ['test_3_cli.py']

SDIR = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture()
def testdir():
    os.chdir(SDIR)

@pytest.fixture()
def cleandir():
    newpath = tempfile.mkdtemp()
    os.chdir(newpath)
