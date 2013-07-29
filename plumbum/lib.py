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


