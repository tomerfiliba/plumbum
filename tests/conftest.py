import pytest
import os
import tempfile

SDIR = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture()
def testdir():
    os.chdir(SDIR)

@pytest.fixture()
def cleandir():
    newpath = tempfile.mkdtemp()
    os.chdir(newpath)
