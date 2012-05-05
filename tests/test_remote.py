import unittest


class RemoteMachineTest(unittest.TestCase):
    def test_imports(self):
        pass

#if __name__ == "__main__":
#    import logging
#    logging.basicConfig(level = logging.DEBUG)
#    with SshMachine("hollywood.xiv.ibm.com") as r: 
#        r.cwd.chdir(r.cwd / "workspace" / "plumbum")
#        #print r.cwd // "*/*.py"
#        r_ssh = r["ssh"]
#        r_ls = r["ls"]
#        r_grep = r["grep"]
#
#        print (r_ssh["localhost", "cd", r.cwd, "&&", r_ls | r_grep[".py"]])()
#        r.close()



if __name__ == "__main__":
    unittest.main()
