**Basics** ::

    >>> from plumbum import local
    >>> ls = local["ls"]
    >>> ls
    LocalCommand(<LocalPath /bin/ls>)
    >>> ls()
    u'build.py\ndist\ndocs\nLICENSE\nplumbum\nREADME.rst\nsetup.py\ntests\ntodo.txt\n'
    >>> notepad = local["c:\\windows\\notepad.exe"]
    >>> notepad()                                   # Notepad window pops up
    u''                                             # Notepad window is closed by user, command returns

Instead of writing ``xxx = local["xxx"]`` for every program you wish to use, you can 
also :ref:`import commands <import-hack>`:
    
    >>> from plumbum.cmd import grep, wc, cat, head
    >>> grep
    LocalCommand(<LocalPath /bin/grep>)

**Piping** ::
    
    >>> chain = ls["-a"] | grep["-v", "\\.py"] | wc["-l"]
    >>> print chain
    /bin/ls -a | /bin/grep -v '\.py' | /usr/bin/wc -l
    >>> chain()
    u'13\n'

**Redirection** ::

    >>> ((cat < "setup.py") | head["-n", 4])()
    u'#!/usr/bin/env python\nimport os\n\ntry:\n'
    >>> (ls["-a"] > "file.list")()
    u''
    >>> (cat["file.list"] | wc["-l"])()
    u'17\n'

**Working-directory manipulation** ::
    
    >>> local.cwd
    <Workdir /home/tomer/workspace/plumbum>
    >>> with local.cwd(local.cwd / "docs"):
    ...     chain()
    ... 
    u'15\n'
    
**Foreground and background execution** ::

    >>> from plumbum import FG, BG
    >>> (ls["-a"] | grep["\\.py"]) & FG         # The output is printed to stdout directly
    build.py
    .pydevproject
    setup.py
    >>> (ls["-a"] | grep["\\.py"]) & BG         # The process runs "in the background"
    <Future ['/bin/grep', '\\.py'] (running)>
    
**Command nesting** ::
    
    >>> from plumbum.cmd import sudo
    >>> print sudo[ifconfig["-a"]]
    /usr/bin/sudo /sbin/ifconfig -a
    >>> (sudo[ifconfig["-a"]] | grep["-i", "loop"]) & FG
    lo        Link encap:Local Loopback  
              UP LOOPBACK RUNNING  MTU:16436  Metric:1

**Remote commands (over SSH)**

Supports `openSSH <http://www.openssh.org/>`_-compatible clients, 
`PuTTY <http://www.chiark.greenend.org.uk/~sgtatham/putty/>`_ (on Windows)
and `Paramiko <https://github.com/paramiko/paramiko/>`_ (a pure-Python implementation of SSH2) ::

    >>> from plumbum import SshMachine
    >>> remote = SshMachine("somehost", user = "john", keyfile = "/path/to/idrsa")
    >>> r_ls = remote["ls"]
    >>> with remote.cwd("/lib"):
    ...     (r_ls | grep["0.so.0"])()
    ... 
    u'libusb-1.0.so.0\nlibusb-1.0.so.0.0.0\n'

**CLI applications** ::

    import logging
    from plumbum import cli
    
    class MyCompiler(cli.Application):
        verbose = cli.Flag(["-v", "--verbose"], help = "Enable verbose mode")
        include_dirs = cli.SwitchAttr("-I", list = True, help = "Specify include directories")
        
        @cli.switch("-loglevel", int)
        def set_log_level(self, level):
            """Sets the log-level of the logger"""
            logging.root.setLevel(level)
        
        def main(self, *srcfiles):
            print "Verbose:", self.verbose
            print "Include dirs:", self.include_dirs 
            print "Compiling:", srcfiles
    
    
    if __name__ == "__main__":
        MyCompiler.run()

Sample output::

    $ python simple_cli.py -v -I foo/bar -Ispam/eggs x.cpp y.cpp z.cpp
    Verbose: True
    Include dirs: ['foo/bar', 'spam/eggs']
    Compiling: ('x.cpp', 'y.cpp', 'z.cpp')

**Color controls** ::

    from plumbum import colors
    with colors.red:
        print("This library provides safe, flexible color access.")
        print("Color", "(and styles in general)" << colors.bold, "are easy!")
    print("The simple 16 colors or", '256 named colors,' << colors.orchid + color.underline,
          "or full hex colors" << colors["#129240"], 'can be used.')
    print("Unsafe " + colors.bg.dark_khaki + "color access" - colors.bg + " is available too.")

Sample output:

.. raw:: html

    <div class="highlight">
    <code>
    <pre><font color="#800000">This library provides safe color access.
    Color <b>(and styles in general)</b> are easy!
    </font>The simple 16 colors, <font color="#D75FD7"><span style="text-decoration: underline;">256 named colors,</span></font> <font color="#129240">or full hex colors</font> can be used.
    Unsafe <span style="background-color: #AFAF5F">color access</span> is available too.</pre>
    </code>
    </div>

