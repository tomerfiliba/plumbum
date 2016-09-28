
import pytest

import plumbum
from plumbum import local

from plumbum._testtools import (
    skip_on_windows
    )


# This is a seperate file to make seperating (ugly) sudo command easier
# For example, you can now run test_local direcly without typing a password


class TestSudo:

    @skip_on_windows
    def test_as_user(self):
        with local.as_root():
            local["date"]()

