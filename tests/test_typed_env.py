import pytest
from plumbum.typed_env import TypedEnv


class TestTypedEnv:

    def test_env(self):

        class E(TypedEnv):
            terminal = TypedEnv.Str("TERM")
            B = TypedEnv.Bool("BOOL", default=True)
            I = TypedEnv.Int("INT INTEGER".split())
            INTS = TypedEnv.CSV("CS_INTS", type=int)

        raw_env = dict(TERM="xterm", CS_INTS="1,2,3,4")
        e = E(raw_env)

        assert e.terminal == "xterm"
        e.terminal = "foo"
        assert e.terminal == "foo"
        assert raw_env["TERM"] == "foo"
        assert "terminal" not in raw_env

        # check default
        assert e.B is True

        raw_env['BOOL'] = "no"
        assert e.B is False

        raw_env['BOOL'] = "0"
        assert e.B is False

        e.B = True
        assert raw_env['BOOL'] == "yes"

        e.B = False
        assert raw_env['BOOL'] == "no"

        assert e.INTS == [1, 2, 3, 4]
        e.INTS = [1, 2]
        assert e.INTS == [1, 2]
        e.INTS = [1, 2, 3, 4]

        with pytest.raises(KeyError):
            e.I

        raw_env["INTEGER"] = "4"
        assert e.I == 4
        assert e['I'] == 4

        e.I = "5"
        assert raw_env['INT'] == "5"
        assert e.I == 5
        assert e['I'] == 5

        assert "{I} {B} {terminal}".format(**e) == "5 False foo"
        assert dict(e) == dict(I=5, B=False, terminal='foo', INTS=[1, 2, 3, 4])

        r = TypedEnv(raw_env)
        assert "{INT} {BOOL} {TERM}".format(**r) == "5 no foo"
