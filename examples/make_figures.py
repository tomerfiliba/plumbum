#!/usr/bin/env python3
from __future__ import annotations

from typing import TYPE_CHECKING

from plumbum import FG, cli, local
from plumbum.cmd import convert, pdflatex
from plumbum.path.utils import delete

if TYPE_CHECKING:
    from plumbum.path.local import LocalPath


def image_comp(item: LocalPath) -> None:
    pdflatex["-shell-escape", item] & FG
    print("Converting", item)
    convert[item.with_suffix(".svg"), item.with_suffix(".png")] & FG

    delete(
        item.with_suffix(".log"),
        item.with_suffix(".aux"),
    )


class MyApp(cli.Application):
    def main(self, *srcfiles: str) -> None:
        print("Tex files should start with:")
        print(r"\documentclass[tikz,convert={outfile=\jobname.svg}]{standalone}")
        items = map(cli.ExistingFile, srcfiles) if srcfiles else local.cwd // "*.tex"
        for item in items:
            image_comp(item)


if __name__ == "__main__":
    MyApp.run()
