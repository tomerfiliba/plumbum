"""
Module hack: ``from plumbum.cmd import ls``
"""
import sys
from types import ModuleType
from plumbum.local_machine import local

__all__ = []

class LocalModule(ModuleType):
    """The module-hack that allows us to use ``from plumbum.cmd import some_program``"""
    def __init__(self, name):
        ModuleType.__init__(self, name, __doc__)
        self.__file__ = None
        self.__package__ = ".".join(name.split(".")[:-1])
    def __getattr__(self, name):
        return local[name]

LocalModule = LocalModule("plumbum.cmd")
sys.modules[LocalModule.__name__] = LocalModule
