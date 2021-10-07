# -*- coding: utf-8 -*-
import pytest

from plumbum import local
from plumbum._testtools import skip_on_windows

pytestmark = pytest.mark.sudo

# This is a separate file to make separating (ugly) sudo command easier
# For example, you can now run test_local directly without typing a password


class TestSudo:
    @skip_on_windows
    def test_as_user(self):
        with local.as_root():
            local["date"]()
