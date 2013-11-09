#!/usr/bin/env python
from plumbum import local, cli
from plumbum.path.utils import delete


class BuildProject(cli.Application):
    upload = cli.Flag("upload", help = "If given, the artifacts will be uploaded to PyPI")
    
    def main(self):
        delete(local.cwd // "*.egg-info", "build", "dist")

        if self.upload:
            local.python("setup.py", "register")
        
        local.python("setup.py", "sdist", "--formats=zip,gztar", "bdist_wininst", "--plat-name=win32", 
            "upload" if self.upload else None)
        
        delete(local.cwd // "*.egg-info", "build")


if __name__ == "__main__":
    BuildProject.run()
