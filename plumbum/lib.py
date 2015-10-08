import sys
from contextlib import contextmanager
from abc import ABCMeta
import inspect

IS_WIN32 = (sys.platform == "win32")

def _setdoc(super):  # @ReservedAssignment
    """This inherits the docs on the current class. Not really needed for Python 3.5,
    due to new behavoir of inspect.getdoc, but still doesn't hurt."""
    def deco(func):
        func.__doc__ = getattr(getattr(super, func.__name__, None), "__doc__", None)
        return func
    return deco

class ProcInfo(object):
    def __init__(self, pid, uid, stat, args):
        self.pid = pid
        self.uid = uid
        self.stat = stat
        self.args = args
    def __repr__(self):
        return "ProcInfo(%r, %r, %r, %r)" % (self.pid, self.uid, self.stat, self.args)

class six(object):
    """
    A light-weight version of six (which works on IronPython)
    """
    PY3 = sys.version_info[0] >= 3
    ABC = ABCMeta('ABC', (object,), {'__module__':__name__, '__slots__':()})

    # Be sure to use named-tuple access, so that usage is not affected
    try:
        getfullargspec = staticmethod(inspect.getfullargspec)
    except AttributeError:
        getfullargspec = staticmethod(inspect.getargspec) # extra fields will not be available

    if PY3:
        integer_types = (int,)
        string_types = (str,)
        MAXSIZE = sys.maxsize
        ascii = ascii  # @UndefinedVariable
        bytes = bytes  # @ReservedAssignment
        unicode_type = str

        @staticmethod
        def b(s):
            return s.encode("latin-1", "replace")
        @staticmethod
        def u(s):
            return s
        @staticmethod
        def get_method_function(m):
            return m.__func__
    else:
        integer_types = (int, long)
        string_types = (str, unicode)
        MAXSIZE = getattr(sys, "maxsize", sys.maxint)
        ascii = repr  # @ReservedAssignment
        bytes = str   # @ReservedAssignment
        unicode_type = unicode

        @staticmethod
        def b(st):
            return st
        @staticmethod
        def u(s):
            return s.decode("unicode-escape")
        @staticmethod
        def get_method_function(m):
            return m.im_func

# Try/except fails because io has the wrong StringIO in Python2
# You'll get str/unicode errors
if six.PY3:
    from io import StringIO
else:
    from StringIO import StringIO


@contextmanager
def captured_stdout(stdin = ""):
    """
    Captures stdout (similar to the redirect_stdout in Python 3.4+, but with slightly different arguments)
    """
    prevstdin = sys.stdin
    prevstdout = sys.stdout
    sys.stdin = StringIO(six.u(stdin))
    sys.stdout = StringIO()
    try:
        yield sys.stdout
    finally:
        sys.stdin = prevstdin
        sys.stdout = prevstdout

class StaticProperty(object):
    """This acts like a static property, allowing access via class or object.
    This is a non-data descriptor."""
    def __init__(self, function):
        self._function = function
        self.__doc__ = function.__doc__

    def __get__(self, obj, klass=None):
        return self._function()


def getdoc(object):
    """
    This gets a docstring if avaiable, and cleans it, but does not look up docs in
    inheritance tree (Pre 3.5 behavior of ``inspect.getdoc``).
    """
    try:
        doc = object.__doc__
    except AttributeError:
        return None
    if not isinstance(doc, str):
        return None
    return inspect.cleandoc(doc)

