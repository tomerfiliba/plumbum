from __future__ import annotations

from .application import Application
from .application import configs  # noqa: F401
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

__all__ = (
    "CSV",
    "Application",
    "configs",
    "Config",
    "ConfigINI",
    "CountOf",
    "ExistingDirectory",
    "ExistingFile",
    "Flag",
    "NonexistentPath",
    "Predicate",
    "Range",
    "Set",
    "SwitchAttr",
    "SwitchError",
    "autoswitch",
    "positional",
    "switch",
)
