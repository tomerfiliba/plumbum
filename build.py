#!/usr/bin/env python
from plumbum import local, cli, FG
from plumbum.path.utils import delete

try:
    from plumbum.cmd import twine
except ImportError:
    twine = None

class BuildProject(cli.Application):
    'Build and optionally upload. For help, see https://packaging.python.org/en/latest/distributing/#uploading-your-project-to-pypi'
    upload = cli.Flag("upload", help = "If given, the artifacts will be uploaded to PyPI")

    def main(self):
        delete(local.cwd // "*.egg-info", "build", "dist")

        #if self.upload:
        #    local.python("setup.py", "register")

        local.python("setup.py", "sdist", "--formats=zip,gztar", "bdist_wininst", "--plat-name=win32")

        delete(local.cwd // "*.egg-info", "build")

        if self.upload:
            if twine is None:
                print("Twine not installed, cannot securly upload. Install twine.")
            else:
                twine['upload','dist/*'] & FG


if __name__ == "__main__":
    BuildProject.run()
