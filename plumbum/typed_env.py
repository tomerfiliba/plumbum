import os
import inspect
from collections import MutableMapping


NO_DEFAULT = object()


class TypedEnv(MutableMapping):
    """
    This object can be used in 'exploratory' mode:

        nv = TypedEnv()
        print(nv.HOME)

    It can also be used as a parser and validator of environment variables:

    class MyEnv(TypedEnv):
        username = TypedEnv.Str("USER", default='anonymous')
        path = TypedEnv.CSV("PATH", separator=":")
        tmp = TypedEnv.Str("TMP TEMP".split())  # support 'fallback' var-names

    nv = MyEnv()

    print(nv.username)

    for p in nv.path:
        print(p)

    try:
        print(p.tmp)
    except KeyError:
        print("TMP/TEMP is not defined")
    else:
        assert False
    """

    __slots__ = ["_env", "_defined_keys"]

    class _BaseVar(object):

        def __init__(self, name, default=NO_DEFAULT):
            self.names = tuple(name) if isinstance(name, (tuple, list)) else (name,)
            self.name = self.names[0]
            self.default = default

        def convert(self, value):
            return value

        def __get__(self, instance, owner):
            if not instance:
                return self
            try:
                return self.convert(instance._raw_get(*self.names))
            except KeyError:
                if self.default is NO_DEFAULT:
                    raise
                return self.default

        def __set__(self, instance, value):
            instance[self.name] = value

    class Str(_BaseVar):
        pass

    class Bool(_BaseVar):

        def convert(self, s):
            s = s.lower()
            if s not in ("yes", "no", "true", "false", "1", "0"):
                raise ValueError("Unrecognized boolean value: %r" % (s,))
            return s in ("yes", "true", "1")

        def __set__(self, instance, value):
            instance[self.name] = "yes" if value else "no"

    class Int(_BaseVar):
        convert = staticmethod(int)

    class Float(_BaseVar):
        convert = staticmethod(float)

    class CSV(_BaseVar):

        def __init__(self, name, default=NO_DEFAULT, type=str, separator=","):
            super(TypedEnv.CSV, self).__init__(name, default=default)
            self.type = type
            self.separator = separator

        def __set__(self, instance, value):
            instance[self.name] = self.separator.join(map(str, value))

        def convert(self, value):
            return [self.type(v.strip()) for v in value.split(self.separator)]

    # =========

    def __init__(self, env=os.environ):
        self._env = env
        self._defined_keys = set(k for (k, v) in inspect.getmembers(self.__class__) if isinstance(v, self._BaseVar))

    def __iter__(self):
        return iter(dir(self))

    def __len__(self):
        return len(self._env)

    def __delitem__(self, name):
        del self._env[name]

    def __setitem__(self, name, value):
        self._env[name] = str(value)

    def _raw_get(self, *key_names):
        for key in key_names:
            value = self._env.get(key, NO_DEFAULT)
            if value is not NO_DEFAULT:
                return value
        else:
            raise KeyError(key_names[0])

    def __contains__(self, key):
        try:
            self._raw_get(key)
        except KeyError:
            return False
        else:
            return True

    def __getattr__(self, name):
        # if we're here then there was no descriptor defined
        try:
            return self._raw_get(name)
        except KeyError:
            raise AttributeError("%s has no attribute %r" % (self.__class__, name))

    def __getitem__(self, key):
        return getattr(self, key)  # delegate through the descriptors

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __dir__(self):
        if self._defined_keys:
            # return only defined
            return sorted(self._defined_keys)
        # return whatever is in the environemnt (for convenience)
        members = set(self._env.keys())
        members.update(dir(self.__class__))
        return sorted(members)
