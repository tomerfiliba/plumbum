# -*- coding: utf-8 -*-
from __future__ import absolute_import

from .application import Application
from .config import Config, ConfigINI
from .switches import (
    CSV,
    CountOf,
    ExistingDirectory,
    ExistingFile,
    Flag,
    NonexistentPath,
    Predicate,
    Range,
    Set,
    SwitchAttr,
    SwitchError,
    autoswitch,
    positional,
    switch,
)
