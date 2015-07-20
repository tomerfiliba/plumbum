#!/usr/bin/env python
from plumbum import cli

class App(cli.Application):
    #VERSION = "1.2.3"
    #x = cli.SwitchAttr("--lala")
    y = cli.Flag("-f")

    def main(self, x, y):
        pass

@App.subcommand("bar")
class Bar(cli.Application):
    z = cli.Flag("-z")

    def main(self, z, w):
        pass

if __name__ == "__main__":
    App.run()
