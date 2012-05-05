#!/usr/bin/env python
from plumbum import local, rm
from plumbum import cli

class BuildProject(cli.Application):
    upload = cli.Flag("upload", help = "If given, the artifacts will be uploaded to PyPI")
    
    def main(self):
        rm(local.cwd // "*.egg-info", "build", "dist")
        
        local.python("setup.py", "sdist", "--formats=zip,gztar", 
            "upload" if self.upload else "")
        local.python("setup.py", "bdist_wininst", "--plat-name=win32", 
            "upload" if self.upload else "")
        
        rm(local.cwd // "*.egg-info", "build")


if __name__ == "__main__":
    BuildProject.run()
