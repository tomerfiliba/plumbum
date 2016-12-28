import pytest

import plumbum
from plumbum import local

from plumbum._testtools import (
    skip_on_windows
    )

try:
    from plumbum.cmd import printenv
except ImportError:
    pass

@skip_on_windows
class TestEnv:

    def test_change_env(self):
       with local.env(silly=12):
           assert 12 == local.env['silly']
           actual = set(x.split('=')[0] for x in printenv().splitlines() if '=' in x)
           localenv = set(x[0] for x in local.env)
           print(actual, localenv)
           assert localenv == actual
           assert len(local.env) == len(actual)

    def test_dictlike(self):
        keys = set(x.split('=')[0] for x in printenv().splitlines() if '=' in x)
        values = set(x.split('=', 1)[1].strip() for x in printenv().splitlines() if '=' in x)

        assert keys == set(local.env.keys())
        assert len(values) == len(set(local.env.values()))

    def test_custom_env(self):
        with local.env():
            items = {'one':'OnE', 'tww':'TWOO'}
            local.env.update(items)
            assert 'tww' in local.env
            local.env.clear()
            assert 'tww' not in local.env

    def test_item(self):
        with local.env():
            local.env['simple_plum'] = 'thing'
            assert 'simple_plum' in local.env
            del local.env['simple_plum']
            assert 'simple_plum' not in local.env
            local.env['simple_plum'] = 'thing'
            assert 'simple_plum' in local.env
            assert 'thing' == local.env.pop('simple_plum')
            assert 'simple_plum' not in local.env
            local.env['simple_plum'] = 'thing'
        assert 'simple_plum' not in local.env


    @skip_on_windows
    def test_home(self):
        assert local.env.home == local.env['HOME']
        old_home = local.env.home
        with local.env():
            local.env.home = 'Nobody'
            assert local.env.home == local.env['HOME']
            assert local.env.home == 'Nobody'
        assert local.env.home == old_home

    @skip_on_windows
    def test_user(self):
        assert local.env.user

