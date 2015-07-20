#!/usr/bin/env python
import logging
from plumbum import cli, local
from plumbum.path.utils import delete, copy


logger = logging.getLogger("FileCopier")

class FileCopier(cli.Application):
    overwrite = cli.Flag("-o", help = "If given, overwrite existing files")

    @cli.switch(["-l", "--log-to-file"], argtype = str)
    def log_to_file(self, filename):
        """logs all output to the given file"""
        handler = logging.FileHandler(filename)
        logger.addHandler(handler)

    @cli.switch(["--verbose"], requires=["--log-to-file"])
    def set_debug(self):
        """Sets verbose mode"""
        logger.setLevel(logging.DEBUG)

    def main(self, src, dst):
        if local.path(dst).exists():
            if not self.overwrite:
                logger.debug("Oh no! That's terrible")
                raise ValueError("Destination already exists")
            else:
                delete(dst)

        logger.debug("I'm going to copy %s to %s", src, dst)
        copy(src, dst)
        logger.debug("Great success")


if __name__ == "__main__":
    FileCopier.run()
