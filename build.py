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

        local.python("setup.py", "sdist", "bdist_wheel")

        delete(local.cwd // "*.egg-info", "build")

        if self.upload:
            if twine is None:
                print("Twine not installed, cannot securely upload. Install twine.")
            else:
                twine['upload', 'dist/*tar.gz', 'dist/*.whl'] & FG


if __name__ == "__main__":
    BuildProject.run()
