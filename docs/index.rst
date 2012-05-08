Plumbum: Shell Combinators
==========================

Ever wished the wrist-handiness of shell scripts be put into a *real* programming language? 
Say hello to *Plumbum Shell Combinators*. Plumbum (Latin for *lead*, which was used to create 
pipes back in the day) is a small yet feature-rich library for shell script-like programs in Python. 
The motto of the library is *"You'll never have to write shell scripts again"*, and thus it
attempts to mimic the shell syntax where it makes sense, while keeping it all pythonic and
cross-platform.

Apart from shell-like syntax and handy shortcuts, the library provides *local* and *remote* 
command execution (over SSH), local and remote file-system *paths*, easy working-directory and 
environment manipulation, and a programmatic *command-line interface* (CLI) application toolkit. 

Let's see some code! ::

    >>> from plumbum import local, FG, BG
    >>> from plumbum.cmd import ls, grep, wc, cat, head
    >>> ls
    LocalCommand(<LocalPath /bin/ls>)
    >>> ls()
    u'build.py\ndist\ndocs\nLICENSE\nplumbum\nREADME.rst\nsetup.py\ntests\ntodo.txt\n'
    
    # piping
    >>> chain = ls["-a"] | grep["-v", "\\.py"] | wc["-l"]
    >>> print chain
    /bin/ls -a | /bin/grep -v '\.py' | /usr/bin/wc -l
    >>> chain()
    u'13\n'

    # cwd manipulation
    >>> local.cwd
    <Workdir /home/tomer/workspace/plumbum>
    >>> with local.cwd(local.cwd / "docs"):
    ...     chain()
    ... 
    u'15\n'
    
    # redirection
    >>> ((cat < "setup.py") | head["-n", 4])()
    u'#!/usr/bin/env python\nimport os\n\ntry:\n'
    >>> (ls["-a"] > "file.list")()
    u''
    >>> (cat["file.list"] | wc["-l"])()
    u'17\n'
    
    # FG and BG
    >>> (ls["-a"] | grep["\\.py"]) & FG         # The output is printed to stdout directly
    build.py
    .pydevproject
    setup.py
    >>> (ls["-a"] | grep["\\.py"]) & BG         # The process runs in the backround
    <Future ['/bin/grep', '\\.py'] (running)>

And you no longer have to stuggle with ``optparse``/``argparse`` to write CLI applications...
Plumbum makes it damn easy! ::

    from plumbum import cli, local
    from plumbum.utils import delete, copy
    logger = ...
    
    class FileCopier(cli.Application):
        overwrite = cli.Flag("-o", help = "If given, overwrite existing files")
    
        @cli.switch(["-l", "--log-to-file"], argtype = str)
        def log_to_file(self, filename):
            """Logs all output to the given file"""
            handler = logging.FileHandler(filename)
            logger.addHandler(handler)
    
        @cli.switch(["--verbose"], requires=["--log-to-file"])
        def set_debug(self):
            """Sets verbose mode"""
            logger.setLevel(logging.DEBUG)
    
        def main(self, src, dst):
            if local.path(dst).exists():
                if not self.overwrite:
                    logger.debug("Oh no! It's terrible")
                    raise ValueError("Destination already exists")
                else:
                    delete(dst)
    
            logger.debug("I'm going to copy %s to %s", src, dst)
            copy(src, dst)
            logger.debug("Great success")
    
    if __name__ == "__main__":
        FileCopier.run()


Development
===========
The library is developed on `github <https://github.com/tomerfiliba/plumbum>`_, using
its lovely `issue tracker <https://github.com/tomerfiliba/plumbum/issues>`_; if you encounter
a problem with the library, please open an issue. 

You can **download** the library from `PyPI <http://pypi.python.org/pypi/plumbum>`_, or 
``easy-install``/``pip install`` it directly.

The library is released under the `MIT license 
<https://github.com/tomerfiliba/plumbum/blob/master/LICENSE>`_.

Guide
=====
.. toctree::
   :maxdepth: 2
   
   local_commands
   local_machine
   paths
   remote_machine
   cli
  
API Reference
=============
.. toctree::
   :maxdepth: 2
   
   api/cli
   api/commands
   api/local_machine
   api/path
   api/remote_machine
   api/session
   api/utils

About
=====
The original purpose of Plumbum was to enable local and remote program execution with ease, 
assuming nothing fancier than good-old SSH. On top of this, a file-system abstraction layer
was devised, so that working with local and remote files would be seamless. 

I've toyed with this idea for some time now, but it wasn't until I had to write build scripts
for a project I've been working on that I decided I've had it with shell scripts and it's time
to make it happen. Plumbum was born from the scraps of the ``Path`` class, which I 
wrote for the aforementioned build system, and the ``SshContext`` and ``SshTunnel`` classes
that I wrote for `RPyC <http://rpyc.sf.net>`_. When I combined the two with *shell combinators*
(because shell scripts do have an edge there) the magic happened and here we are.

Credits
=======
The project has been inspired by `PBS <https://github.com/amoffat/pbs>`_ 
of `Andrew Moffat <https://github.com/amoffat>`_, 
and has borrowed some of his ideas (namely treating programs like functions and the
nice trick for importing commands). However, I felt there was too much magic going on in PBS, 
and that the syntax wasn't what I had in mind when I came to write shell-like programs. 
I contacted Andrew about these issues, but he wanted to keep PBS this way. Other than that, 
the two libraries go in different directions, where Plumbum attempts to provide a more
wholesome approach.

Plumbum also pays tribute to `Rotem Yaari <https://github.com/vmalloc/>`_ who suggested a 
library code-named ``pyplatform`` for that very same purpose, but which had never materialized.
