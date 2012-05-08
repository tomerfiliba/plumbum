#!/usr/bin/env python
from plumbum import local, cli
from plumbum.utils import delete


class BuildProject(cli.Application):
    upload = cli.Flag("upload", help = "If given, the artifacts will be uploaded to PyPI")
    
    def main(self):
        delete(local.cwd // "*.egg-info", "build", "dist")
        
        local.python("setup.py", "sdist", "--formats=zip,gztar", 
            "upload" if self.upload else "")
        local.python("setup.py", "bdist_wininst", "--plat-name=win32", 
            "upload" if self.upload else "")
        
        delete(local.cwd // "*.egg-info", "build")


if __name__ == "__main__":
    BuildProject.run()
