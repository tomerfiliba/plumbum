import sys


IS_WIN32 = (sys.platform == "win32")

try:
    bytes = bytes  # @ReservedAssignment
except NameError:
    bytes = str  # @ReservedAssignment
try:
    ascii = ascii  # @UndefinedVariable
except NameError:
    ascii = repr  # @ReservedAssignment


def _setdoc(super):  # @ReservedAssignment
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
    if PY3:
        integer_types = (int,)
        string_types = (str,)
        MAXSIZE = sys.maxsize
        @staticmethod
        def b(s):
            return s.encode("latin-1")
        @staticmethod
        def get_method_function(m):
            return m.__func__
    else:
        integer_types = (int, long)
        string_types = (str, unicode)
        MAXSIZE = getattr(sys, "maxsize", sys.maxint)
        @staticmethod
        def b(st):
            return st
        @staticmethod
        def get_method_function(m):
            return m.im_func


