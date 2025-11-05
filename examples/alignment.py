#!/usr/bin/env python3
from __future__ import annotations

from plumbum import cli


class App(cli.Application):
    # VERSION = "1.2.3"
    # x = cli.SwitchAttr("--lala")
    y = cli.Flag("-f")

    def main(self, x: str, y: str) -> None:
        pass


@App.subcommand("bar")
class Bar(cli.Application):
    z = cli.Flag("-z")

    def main(self, z: str, w: str) -> None:
        pass


if __name__ == "__main__":
    App.run()
