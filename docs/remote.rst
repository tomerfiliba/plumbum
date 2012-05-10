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

Only the ``hostname`` parameter is required, all other parameters are optional. If the host has
your ``idrsa.pub`` key in its ``authorized_keys`` file, or if you've set up your ``~/.ssh/config``
to login with some user and ``keyfile``, you can simply use ``rem = SshMachine("hostname")``.

Much like the :ref:`local object <guide-local-machine>`, remote machines expose ``which()``,
``path()``, ``python``, ``cwd`` and ``env``. You can also run remote commands, create SSH tunnels, 
upload/download files, etc. You may also refer to :class:`the full API  
<plumbum.remote_machine.SshMachine>`, as this guide will only survey the features.

Working Directory and Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The ``cwd`` and ``env`` attributes can be used to inspect and manipulate the remote machine's
working directory and environment variables, respectively.

Tunneling
^^^^^^^^^
SSH tunneling is a very useful feature of the SSH protocol. It allows you to connect from your
machine to a remote server process, while having your connection authenticated and encrypted
out-of-the-box. Say you run on ``machine-A``, and you wish to connect to a server program
running on ``machine-B``. That server program binds to ``localhost:8888`` (where ``localhost`` 
refers naturally to to ``machine-B``). Using Plumbum, you can easily set up a tunnel from
port 6666 on ``machine-A`` to port 8888 on ``machine-B``::

    >>> tun = rem.tunnel(6666, 8888)

Now you can connect a socket to ``localhost:6666`` (on ``machine-A``, that is), and it will 
be magically forwarded to ``machine-B:8888`` over SSH.

    >>> import socket
    >>> s = socket.socket()
    >>> s.connect(("" 




.. _guide-remote-commands:

Remote Commands
---------------


.. _guide-remote-paths:

Remote Paths
------------

