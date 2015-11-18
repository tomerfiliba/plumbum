import pytest
import os

SDIR = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture()
def testdir():
    os.chdir(SDIR)
