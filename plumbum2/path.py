class Path(object):
    pass

class LocalPath(object):
    pass

class SshPath(object):
    def __init__(self, ssh):
        self.ssh = ssh

