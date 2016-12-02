from __future__ import print_function, division

from abc import abstractmethod
from plumbum.lib import six
from plumbum import local
import os

try:
    from configparser import ConfigParser # Py3
except ImportError:
    from ConfigParser import ConfigParser # Py2

class ConfigBase(six.ABC):
    """Base class for Config parsers.

    :param filename: The file to use

    Usage:

        with Config("~/.myprog_rc") as conf:
            value = conf.get("option", "default")
            value2 = conf["option"] # shortcut for default=None

    """

    __slots__ = "filename changed".split()

    def __init__(self, filename):
        self.filename = local.path(filename)
        self.changed = False

    def __enter__(self):
        if not self.filename.exists():
            self.filename.touch()
        self.read()

    @ABC.abstractmethod
    def read(self):
        pass

    @ABC.abstractmethod
    def save(self):
        pass

    @ABC.abstractmethod
    def _get(self, option):
        pass

    @ABC.abstractmethod
    def _set(self, option, value):
        pass

    def get(self, option, default=None):
        "Get an item from the store"
        try:
            return self._get(option)
        except KeyError:
            self._set(option, default)
            self.changed = True
            return default

    def __getitem__(self, option):
        return self.get(option)

class ConfigINI(ConfigBase):
    DEFAULT_SECTION = 'default'
    slots = "parser".split()
    def read(self):
        self.parser = ConfigParser()
        self.parser.read(self.filename)

    def save(self):
        with open(self.filename, 'wb') as f:
            self.parser.save(f)

    @classmethod
    def _sec_opt(cls, option):
        if '.' not in option:
            sec = cls.DEFAULT_SECTION
        else:
            sec, option = option.split('.',1)
        return sec, option

    def _get(self, option):
        sec, option = self._sec_opt(option)

        try:
            return self.parser.get(sec, option)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            raise KeyError("{sec}:{option}".format(sec=sec, option=option))


    def _set(self, option, value):
        sec, option = self._sec_opt(option)
        self.parser.set(sec, option, value)

Config = ConfigINI
