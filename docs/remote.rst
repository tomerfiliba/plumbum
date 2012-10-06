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
   At the moment, Plumbum requires ``ssh`` (``openSSH`` or compatible) installed on your 
   system in order to connect to remote machines. Future versions of Plumbum may utilize
   ``paramiko`` or similar tools.

Only the ``hostname`` parameter is required, all other parameters are optional. If the host has
your ``id-rsa.pub`` key in its ``authorized_keys`` file, or if you've set up your ``~/.ssh/config``
to login with some user and ``keyfile``, you can simply use ``rem = SshMachine("hostname")``.

Much like the :ref:`local object <guide-local-machine>`, remote machines expose ``which()``,
``path()``, ``python``, ``cwd`` and ``env``. You can also run remote commands, create SSH tunnels, 
upload/download files, etc. You may also refer to :class:`the full API  
<plumbum.remote_machine.SshMachine>`, as this guide will only survey the features.

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

.. _guide-remote-paths:

Remote Paths
------------
Analogous to local paths, remote paths represent a file-system path of a remote system, and 
expose a set of utility functions for iterating over subpaths, creating subpaths, moving/copying/
renaming paths, etc. ::

    >>> p = rem.path("/bin")
    >>> p / "ls"
    <RemotePath /bin/ls>
    >>> (p / "ls").isfile()
    True
    >>> rem.path("/dev") // "sd*"
    [<RemotePath /dev/sda>, < RemotePath /dev/sdb>, <RemotePath /dev/sdb1>, <RemotePath /dev/sdb2>]

.. note::
   See the :ref:`guide-utils` guide for copying, moving and deleting remote paths



