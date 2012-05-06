from __future__ import with_statement
import os
import socket
import unittest
import six
from plumbum import SshMachine, BG
import time
#import logging
#logging.basicConfig(level = logging.DEBUG)


tunnel_prog = r"""
import sys, six, socket
s = socket.socket()
s.bind(("", 0))
s.listen(1)
sys.stdout.write(six.b("%s\n" % (s.getsockname()[1],)))
sys.stdout.flush()
s2, _ = s.accept()
data = s2.recv(100)
s2.send(six.b("hello ") + data)
s2.close()
s.close()
"""

class RemoteMachineTest(unittest.TestCase):
    def test_remote(self):
        with SshMachine("localhost") as rem:
            r_ssh = rem["ssh"]
            r_ls = rem["ls"]
            r_grep = rem["grep"]
            
            self.assertTrue(".bashrc" in r_ls("-a").splitlines())
            
            with rem.cwd(os.path.dirname(__file__)):
                cmd = r_ssh["localhost", "cd", rem.cwd, "&&", r_ls | r_grep["\\.py"]]
                self.assertTrue("'|'" in str(cmd))
                self.assertTrue("test_remote.py" in cmd())
                self.assertTrue("test_remote.py" in [f.basename for f in rem.cwd // "*.py"])
    
    def test_download_upload(self):
        pass
    
    def test_session(self):
        pass
    
    def test_tunnel(self):
        with SshMachine("localhost") as rem:
            p = (rem.python["-u"] << tunnel_prog).popen()
            try:
                port = int(p.stdout.readline().strip())
            except ValueError:
                print(p.communicate())
                raise

            with rem.tunnel(12222, port) as tun:
                time.sleep(0.5)
                s = socket.socket()
                s.connect(("localhost", 12222))
                s.send(six.b("world"))
                data = s.recv(100)
                s.close()
                self.assertEqual(data, six.b("hello world"))
            
            p.communicate()



if __name__ == "__main__":
    unittest.main()
