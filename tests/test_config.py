
import pytest

from plumbum import local
from plumbum.cli import Config, ConfigINI


fname =  'test_config.ini'

class TestConfig:

    @pytest.mark.usefixtures('cleandir')
    def test_makefile(self):
        with ConfigINI(fname) as conf:
            conf['value'] = 12
            conf['string'] = 'ho'

        with open(fname) as f:
            contents = f.read()

        assert 'value = 12' in contents
        assert 'string = ho' in contents


    def test_readfile(self):
        with open(fname, 'w') as f:
            print('''
[DEFAULT]
one = 1
two = hello''', file=f)

        with ConfigINI(fname) as conf:
            assert conf['one'] == '1'
            assert conf['two'] == 'hello'


    def test_complex_ini(self):
        with Config(fname) as conf:
            conf['value'] = 'normal'
            conf['newer.value'] = 'other'

        with Config(fname) as conf:
            assert conf['value'] == 'normal'
            assert conf['DEFAULT.value'] == 'normal'
            assert conf['newer.value'] == 'other'


    def test_nowith(self):
        conf = ConfigINI(fname)
        conf['something'] = 'nothing'
        conf.write()

        with open(fname) as f:
            contents = f.read()

        assert 'something = nothing' in contents

    def test_home(self):
        mypath = local.env.home /  'some_simple_home_rc.ini'
        assert not mypath.exists()
        try:
            with Config('~/some_simple_home_rc.ini') as conf:
                conf['a'] = 'b'
            assert mypath.exists()
            mypath.unlink()

            with Config(mypath) as conf:
                conf['a'] = 'b'
            assert mypath.exists()
            mypath.unlink()

        finally:
            mypath.unlink()
