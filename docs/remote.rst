.. _guide-remote:

Remote
======
Just like running local commands, Plumbum supports running commands on remote systems, by executing
them over SSH. 

.. _guide-remote-machines:

Remote Machines
---------------
Forming a connection to a remote machine is very straight forward::

    >>> from plumbum import SshMachine
    >>> rem = SshMachine("hostname", user = "john", keyfile = "/path/to/idrsa")
    >>> # ...
    >>> rem.close()

Or as a context-manager::

    >>> with SshMachine("hostname", user = "john", keyfile = "/path/to/idrsa") as rem:
    ...     pass

.. note::

   ``SshMachine`` requires ``ssh`` (``openSSH`` or compatible) installed on your system in order 
   to connect to remote machines. The remote machine must have bash as the default shell (or any shell
   that supports the ``2>&1`` syntax for stderr redirection).
   Alternatively, you can use the pure-Python implementation of
   :ref:`ParamikoMachine <guide-paramiko-machine>`.

Only the ``hostname`` parameter is required, all other parameters are optional. If the host has
your ``id-rsa.pub`` key in its ``authorized_keys`` file, or if you've set up your ``~/.ssh/config``
to login with some user and ``keyfile``, you can simply use ``rem = SshMachine("hostname")``.

Much like the :ref:`local object <guide-local-machine>`, remote machines expose ``which()``,
``path()``, ``python``, ``cwd`` and ``env``. You can also run remote commands, create SSH tunnels, 
upload/download files, etc. You may also refer to :class:`the full API  
<plumbum.remote_machine.SshMachine>`, as this guide will only survey the features.

.. note::

   `PuTTY <http://www.chiark.greenend.org.uk/~sgtatham/putty/>`_ users on Windows should use
   the dedicated :class:`PuttyMachine <plumbum.remote_machine.PuttyMachine>` instead of 
   ``SshMachine``. See also :ref:`ParamikoMachine <guide-paramiko-machine>`.

   .. versionadded:: 1.0.1

Working Directory and Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The ``cwd`` and ``env`` attributes represent the remote machine's working directory and environment 
variables, respectively, and can be used to inspect or manipulate them. Much like their local 
counterparts, they can be used as context managers, so their effects can be contained. :: 

    >>> rem.cwd
    <Workdir /home/john>
    >>> with rem.cwd(rem.cwd / "Desktop"):
    ...     print rem.cwd
    /home/john/Desktop
    >>> rem.env["PATH"]
    /bin:/sbin:/usr/bin:/usr/local/bin
    >>> rem.which("ls")
    <RemotePath /bin/ls>


Tunneling
^^^^^^^^^
SSH tunneling is a very useful feature of the SSH protocol. It allows you to connect from your
machine to a remote server process, while having your connection authenticated and encrypted
out-of-the-box. Say you run on ``machine-A``, and you wish to connect to a server program
running on ``machine-B``. That server program binds to ``localhost:8888`` (where ``localhost`` 
refers naturally to to ``machine-B``). Using Plumbum, you can easily set up a tunnel from
port 6666 on ``machine-A`` to port 8888 on ``machine-B``::

    >>> tun = rem.tunnel(6666, 8888)
    >>> # ...
    >>> tun.close()

Or as a context manager::

    >>> with rem.tunnel(6666, 8888):
    ...     pass

You can now connect a socket to ``machine-A:6666``, and it will be securely forwarded over SSH 
to ``machine-B:8888``. When the tunnel object is closed, all active connections will be 
dropped.


.. _guide-remote-commands:

Remote Commands
---------------

Like local commands, remote commands are created using indexing (``[]``) on a remote machine 
object. You can either pass the command's name, in which case it will be resolved by through 
``which``, or the path to the program. ::

    >>> rem["ls"]
    <RemoteCommand(<RemoteMachine ssh://hostname>, '/bin/ls')>
    >>> rem["/usr/local/bin/python3.2"]
    <RemoteCommand(<RemoteMachine ssh://hostname>, '/usr/local/bin/python3.2')>
    >>> r_ls = rem["ls"]
    >>> r_grep = rem["grep"]
    >>> r_ls()
    u'foo\nbar\spam\n'

Nesting Commands
^^^^^^^^^^^^^^^^
Remote commands can be nested just like local ones. In fact, that's how the ``SshMachine`` operates
behind the scenes - it nests each command inside ``ssh``. Here are some examples::

    >>> r_sudo = rem["sudo"]
    >>> r_ifconfig = rem["ifconfig"]
    >>> print r_sudo[r_ifconfig["-a"]]()
    eth0      Link encap:Ethernet HWaddr ...
    [...]

You can nest multiple commands, one within another. For instance, you can connect to some machine
over SSH and use that machine's SSH client to connect to yet another machine. Here's a sketch:: 

    >>> from plumbum.cmd import ssh
    >>> print ssh["localhost", ssh["localhost", "ls"]]
    /usr/bin/ssh localhost /usr/bin/ssh localhost ls
    >>>
    >>> ssh["localhost", ssh["localhost", "ls"]]()
    u'bin\nDesktop\nDocuments\n...'


Piping
^^^^^^
Piping works for remote commands as well, but there's a caveat to note here: the plumbing takes
place on the local machine! Consider this code for instance ::

    >>> r_grep = rem["grep"]
    >>> r_ls = rem["ls"]
    >>> (r_ls | r_grep["b"])()
    u'bin\nPublic\n'

Although ``r_ls`` and ``r_grep`` are remote commands, the data is sent from ``r_ls`` to the local 
machine, which then sends it to the remote one for running ``grep``. This will be fixed in a future
version of Plumbum. 

It should be noted, however, that piping remote commands into local ones is perfectly fine. 
For example, the previous code can be written as ::

    >>> from plumbum.cmd import grep
    >>> (r_ls | grep["b"])()
    u'bin\nPublic\n'

Which is even more efficient (no need to send data back and forth over SSH).

.. _guide-paramiko-machine:

Paramiko Machine
----------------
.. versionadded:: 1.1

``SshMachine`` relies on the system's ``ssh`` client to run commands; this means that for each
remote command you run, a local process is spawned and an SSH connection is established.
While relying on a well-known and trusted SSH client is the most stable option, the incurred 
overhead of creating a separate SSH connection for each command may be too high. In order to 
overcome this, Plumbum provides integration for `paramiko <https://github.com/paramiko/paramiko/>`_,
an open-source, pure-Python implementation of the SSH2 protocol. This is the ``ParamikoMachine``, 
and it works along the lines of the ``SshMachine``::

    >>> from plumbum.machines.paramiko_machine import ParamikoMachine
    >>> rem = ParamikoMachine("192.168.1.143")
    >>> rem["ls"]
    RemoteCommand(<ParamikoMachine paramiko://192.168.1.143>, <RemotePath /bin/ls>)
    >>> r_ls = rem["ls"]
    >>> r_ls()
    u'bin\nDesktop\nDocuments\nDownloads\nexamples.desktop\nMusic\nPictures\n...'
    >>> r_ls("-a")
    u'.\n..\n.adobe\n.bash_history\n.bash_logout\n.bashrc\nbin...'

.. note::
    Using ``ParamikoMachine`` requires paramiko to be installed on your system. Also, you have
    to explicitly import it (``from plumbum.machines.paramiko_machine import ParamikoMachine``) as paramiko
    is quite heavy.

    Refer to :class:`the API docs <plumbum.paramiko_machine.ParamikoMachine>` for more details.

The main advantage of using ``ParamikoMachine`` is that only a single, persistent SSH connection 
is created, over which commands execute. Moreover, paramiko has a built-in SFTP client, which is 
used instead of ``scp`` to copy files (employed by the ``.download()``/``.upload()`` methods), 
and tunneling is much more light weight: In the ``SshMachine``, a tunnel is created by an external 
process that lives for as long as the tunnel is to remain active. The ``ParamikoMachine``, however,
can simply create an extra *channel* on top of the same underlying connection with ease; this is 
exposed by ``connect_sock()``, which creates a tunneled TCP connection and returns a socket-like 
object

.. warning::
    Piping and input/output redirection don't really work with ``ParamikoMachine`` commands.
    You'll get all kinds of errors, like ``'ChannelFile' object has no attribute 'fileno'`` or 
    ``I/O operation on closed file`` -- this is due to the fact that Paramiko's channels are not
    real, OS-level files, so they can't interact with ``subprocess.Popen``.
    
    This will be solved in a future release; in the meanwhile, you can use the machine's 
    ``.session()`` method, like so ::
    
        >>> s = mach.session()
        >>> s.run("ls | grep b")
        (0, u'bin\nPublic\n', u'')


Tunneling Example
^^^^^^^^^^^^^^^^^ 

On ``192.168.1.143``, I ran the following sophisticated server (notice it's bound to ``localhost``)::

    >>> import socket
    >>> s=socket.socket()
    >>> s.bind(("localhost", 12345))
    >>> s.listen(1)
    >>> s2,_=s.accept()
    >>> while True:
    ...     data = s2.recv(1000)
    ...     if not data:
    ...         break
    ...     s2.send("I eat " + data)
    ...

On my other machine, I connect (over SSH) to this host and then create a tunneled connection to
port 12345, getting back a socket-like object::

    >>> rem = ParamikoMachine("192.168.1.143")
    >>> s = rem.connect_sock(12345)
    >>> s.send("carrot")
    6
    >>> s.recv(1000)
    'I eat carrot'
    >>> s.send("babies")
    6
    >>> s.recv(1000)
    'I eat babies'
    >>> s.close()


.. _guide-remote-paths:

Remote Paths
------------
Analogous to local paths, remote paths represent a file-system path of a remote system, and 
expose a set of utility functions for iterating over subpaths, creating subpaths, moving/copying/
renaming paths, etc. ::

    >>> p = rem.path("/bin")
    >>> p / "ls"
    <RemotePath /bin/ls>
    >>> (p / "ls").is_file()
    True
    >>> rem.path("/dev") // "sd*"
    [<RemotePath /dev/sda>, < RemotePath /dev/sdb>, <RemotePath /dev/sdb1>, <RemotePath /dev/sdb2>]

.. note::
   See the :ref:`guide-utils` guide for copying, moving and deleting remote paths

For futher information, see the :ref:`api docs <api-remote-machines>`.

