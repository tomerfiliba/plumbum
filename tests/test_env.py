from __future__ import annotations

import contextlib
import os

import pytest
from posix_cmd import skip_if_no_posix_tools

from plumbum import local
from plumbum._testtools import skip_on_windows
from plumbum.lib import IS_WIN32

with contextlib.suppress(ImportError):
    from plumbum.cmd import printenv


class TestEnv:
    @skip_on_windows
    @skip_if_no_posix_tools
    def test_change_env(self):
        with local.env(silly=12):
            assert local.env["silly"] == 12
            env_dict = {
                x.split("=")[0]: x.split("=", 1)[1].strip()
                for x in printenv().splitlines()
                if "=" in x
            }
            if IS_WIN32:
                env_dict.pop("TERM", None)
            actual = set(env_dict.keys())
            localenv = {x[0] for x in local.env}
            print(actual, localenv)
            assert localenv == actual
            assert len(local.env) == len(actual)

    @skip_if_no_posix_tools
    def test_dictlike(self):
        env_dict = {
            x.split("=")[0]: x.split("=", 1)[1].strip()
            for x in printenv().splitlines()
            if "=" in x
        }
        if IS_WIN32:
            env_dict.pop("TERM", None)
        keys = set(env_dict.keys())
        values = list(env_dict.values())
        assert keys == set(local.env.keys())
        assert len(values) == len(list(local.env.values()))

    def test_custom_env(self):
        with local.env():
            items = {"one": "OnE", "tww": "TWOO"}
            local.env.update(items)
            assert "tww" in local.env
            local.env.clear()
            assert "tww" not in local.env

    def test_item(self):
        with local.env():
            local.env["simple_plum"] = "thing"
            assert "simple_plum" in local.env
            del local.env["simple_plum"]
            assert "simple_plum" not in local.env
            local.env["simple_plum"] = "thing"
            assert "simple_plum" in local.env
            assert local.env.pop("simple_plum") == "thing"
            assert "simple_plum" not in local.env
            local.env["simple_plum"] = "thing"
        assert "simple_plum" not in local.env

    @pytest.mark.skipif(
        "HOME" not in os.environ, reason="environment variable HOME is not set"
    )
    def test_home(self):
        assert local.env.home == local.env["HOME"]
        old_home = local.env.home
        with local.env():
            local.env.home = "Nobody"
            assert local.env.home == local.env["HOME"]
            assert local.env.home == "Nobody"
        assert local.env.home == old_home

    def test_user(self):
        assert local.env.user
