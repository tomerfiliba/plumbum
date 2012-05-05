#import logging
#logging.basicConfig(level=logging.DEBUG)
import unittest
from plumbum import local, FG, BG


class LocalMachineTest(unittest.TestCase):
    def test_imports(self):
        from plumbum.cmd import ls
        print ls()

    def _test_piping(self):
        from plumbum.cmd import grep
        ls = local["ls"]
        chain = (ls | grep["path"])
        print chain
        print chain()
    
#    def _test_quoting(self):
#        ssh = local["ssh"]
#        pwd = local["pwd"]
#        
#        print (ssh, pwd)
#        print (local.cwd // "*.py")
#        
#        cmd = ssh["localhost", "cd", "/usr", "&&", ssh["localhost", "cd", "/", "&&", 
#            ssh["localhost", "cd", "/bin", "&&", pwd]]]
#        print (cmd.formulate(0))


if __name__ == "__main__":
    unittest.main()

