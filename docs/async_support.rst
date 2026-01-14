Async Support
=============

.. versionadded:: 2.0

Plumbum includes full support for asyncio, allowing you to run commands
asynchronously using Python's ``async``/``await`` syntax.

Basic Usage
-----------

There are three ways to use async commands in Plumbum:

**Method 1: Direct import (most convenient)**::

    from plumbum.async_cmd import ls, grep, echo
    import asyncio

    async def main():
        # Simple command execution
        result = await ls("-la")
        print(result)

        # Get full result object
        result_obj = await ls.run(["-la"])
        print(f"Return code: {result_obj.returncode}")
        print(f"Output: {result_obj.stdout}")

    asyncio.run(main())

**Method 2: Using async_local**::

    from plumbum import async_local
    import asyncio

    async def main():
        # Simple command execution
        result = await async_local["ls"]("-la")
        print(result)

        # Get full result object
        ls = async_local["ls"]
        result_obj = await ls.run(["-la"])
        print(f"Return code: {result_obj.returncode}")

    asyncio.run(main())

**Method 3: Dynamic access** (for runtime command names)::

    import plumbum.async_cmd as async_cmd

    async def main():
        cmd_name = "ls"
        cmd = getattr(async_cmd, cmd_name)
        result = await cmd("-la")

The ``async_cmd`` module uses the same import pattern as ``plumbum.cmd`` for
synchronous commands. Choose the method that best fits your use case:

- Use **async_cmd** when you know command names at import time
- Use **async_local** when you need more control or dynamic command lookup
- Use **dynamic access** when command names are determined at runtime

Pipelines
---------

Async commands support pipelines just like synchronous commands. Works with both
``async_cmd`` and ``async_local``::

    from plumbum.async_cmd import ls, grep, echo, wc

    async def pipeline_example():
        # Simple pipeline
        result = await (ls | grep["py"])()
        print(result)

        # Multi-stage pipeline
        result = await (
            echo["line1\\nline2\\nline3"] |
            grep["line"] |
            wc["-l"]
        )()
        print(f"Line count: {result.strip()}")

Concurrent Execution
--------------------

One of the main benefits of async support is the ability to run multiple
commands concurrently::

    from plumbum.async_cmd import echo

    async def concurrent_example():
        # Run multiple commands at once
        results = await asyncio.gather(
            echo("task1"),
            echo("task2"),
            echo("task3"),
        )

        for i, result in enumerate(results, 1):
            print(f"Task {i}: {result.strip()}")

Error Handling
--------------

Async commands raise the same exceptions as synchronous commands::

    from plumbum.async_cmd import false
    from plumbum.commands import ProcessExecutionError

    async def error_example():
        try:
            # This will fail
            await false.run()
        except ProcessExecutionError as e:
            print(f"Command failed with code {e.retcode}")
            print(f"Stderr: {e.stderr}")

        # Disable error checking
        result = await false.run(retcode=None)
        print(f"Exit code: {result.returncode}")

        # Accept multiple return codes
        result = await false.run(retcode=(0, 1))

If you try to import a command that doesn't exist, you'll get an ``AttributeError``::

    try:
        from plumbum.async_cmd import nonexistent_command
    except AttributeError:
        print("Command not found")

Timeouts
--------

Async commands support timeouts::

    from plumbum.async_cmd import sleep

    async def timeout_example():
        try:
            # Timeout after 1 second
            await sleep.run(["10"], timeout=1.0)
        except asyncio.TimeoutError:
            print("Command timed out!")

Process Interaction
-------------------

For more complex scenarios, you can use ``popen`` to interact with
a process's stdin/stdout/stderr::

    from plumbum.async_cmd import cat

    async def interactive_example():
        proc = await cat.popen()

        # Write to stdin
        proc.stdin.write(b"Hello, world!\\n")
        await proc.stdin.drain()
        proc.stdin.close()

        # Read from stdout
        output = await proc.stdout.read()
        await proc.wait()

        print(output.decode())

Execution Modifiers
-------------------

Async commands support three execution modifiers:

AsyncTF
~~~~~~~

Returns ``True`` or ``False`` based on the command's exit code::

    from plumbum.async_cmd import test, grep
    from plumbum.commands.async_ import AsyncTF

    # Check if a file exists
    exists = await (test["-f", "file.txt"] & AsyncTF)
    print(f"File exists: {exists}")

    # Check for specific exit code
    result = await (grep["pattern", "file.txt"] & AsyncTF(retcode=(0, 1)))

AsyncRETCODE
~~~~~~~~~~~~

Returns only the exit code, ignoring stdout/stderr::

    from plumbum.async_cmd import ls
    from plumbum.commands.async_ import AsyncRETCODE

    # Get exit code
    code = await (ls["/nonexistent"] & AsyncRETCODE)
    print(f"Exit code: {code}")

AsyncTEE
~~~~~~~~

Displays output in real-time while also capturing it::

    from plumbum.async_cmd import npm
    from plumbum.commands.async_ import AsyncTEE

    # Run command and see output in real-time
    retcode, stdout, stderr = await (npm["install"] & AsyncTEE)
    print(f"Installation completed with code {retcode}")

Why No BG, FG, NOHUP?
~~~~~~~~~~~~~~~~~~~~~

The sync modifiers ``BG``, ``FG``, and ``NOHUP`` are not available in async mode:

* **BG (Background)**: Not needed because async commands are already non-blocking by nature.
  Use ``asyncio.create_task()`` or ``asyncio.gather()`` for concurrent execution.

* **FG (Foreground)**: Not applicable because async I/O handles stdin/stdout/stderr differently.
  For interactive programs, use sync commands with the ``FG`` modifier.

* **NOHUP**: Not needed because async processes are already detached from the parent process.
  For true daemon processes, use sync commands with the ``NOHUP`` modifier.

Remote Machines
---------------

Async support includes remote command execution via SSH::

    from plumbum.machines.ssh_machine import AsyncSshMachine

    async def remote_example():
        async with AsyncSshMachine("hostname") as rem:
            # Simple command
            result = await rem["ls"]("-la")
            print(result)

            # Pipeline
            result = await (rem["ls"] | rem["grep"]["py"])()
            print(result)

            # Concurrent execution
            results = await asyncio.gather(
                rem["echo"]("task1"),
                rem["echo"]("task2"),
            )

Multiple Remote Hosts
~~~~~~~~~~~~~~~~~~~~~

Connect to multiple hosts concurrently::

    async def multi_host_example():
        async def get_hostname(host):
            async with AsyncSshMachine(host) as rem:
                return await rem["hostname"]()

        results = await asyncio.gather(
            get_hostname("host1"),
            get_hostname("host2"),
            get_hostname("host3"),
        )

        for hostname in results:
            print(hostname.strip())

Mixing Sync and Async
----------------------

Sync and async commands can coexist in the same program::

    from plumbum.cmd import echo as sync_echo
    from plumbum.async_cmd import echo as async_echo

    async def mixed_example():
        # Synchronous command
        sync_result = sync_echo("sync")
        print(f"Sync: {sync_result}")

        # Asynchronous command
        async_result = await async_echo("async")
        print(f"Async: {async_result}")

When to Use Sync vs Async
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Use sync commands when:**

* Running simple, one-off commands
* Using background processes (``BG`` modifier)
* Running interactive programs (``FG`` modifier)
* Creating daemon processes (``NOHUP`` modifier)

**Use async commands when:**

* Running multiple commands concurrently
* Building async applications (web servers, APIs, etc.)
* Performing I/O-bound operations
* Integrating with async frameworks (aiohttp, FastAPI, etc.)

API Reference
-------------

AsyncCommand
~~~~~~~~~~~~

.. class:: AsyncCommand(cmd, args=(), encoding=None)

   Represents an async command that can be executed.

   .. method:: __call__(*args, **kwargs)

      Execute the command and return stdout as a string.
      Returns a coroutine that must be awaited.

   .. method:: run(args=(), retcode=0, timeout=None, cwd=None, env=None)

      Execute the command asynchronously.

      :param args: Additional arguments to pass
      :param retcode: Expected return code(s), or None to disable checking
      :param timeout: Maximum execution time in seconds
      :param cwd: Working directory
      :param env: Environment variables
      :return: AsyncResult object

   .. method:: popen(args=(), cwd=None, env=None)

      Create an async subprocess without waiting for completion.

      :return: asyncio.subprocess.Process instance

AsyncResult
~~~~~~~~~~~

.. class:: AsyncResult(returncode, stdout, stderr)

   Result of an async command execution.

   .. attribute:: returncode

      The exit code of the process.

   .. attribute:: stdout

      Standard output as a string.

   .. attribute:: stderr

      Standard error as a string.

AsyncLocalMachine
~~~~~~~~~~~~~~~~~

.. class:: AsyncLocalMachine()

   Async version of LocalMachine. Provides access to async commands.

   .. method:: __getitem__(cmd)

      Get an async command by name or path.

      :param cmd: Command name or LocalPath
      :return: AsyncLocalCommand instance

.. data:: async_local

   Singleton instance of AsyncLocalMachine.

   Can be imported from::

       from plumbum import async_local
       # or
       from plumbum.machines.local import async_local

Async CMD Module
~~~~~~~~~~~~~~~~

The ``async_cmd`` module provides convenient direct imports, similar to ``plumbum.cmd``
for synchronous commands::

    from plumbum.async_cmd import ls, grep, echo

This is equivalent to using ``async_local["command"]`` but more concise. The module
uses Python's ``__getattr__`` mechanism to dynamically look up commands and return
``AsyncLocalCommand`` instances.

**Comparison with sync commands**::

    # Sync version
    from plumbum.cmd import echo
    result = echo("hello")  # Executes immediately

    # Async version
    from plumbum.async_cmd import echo
    result = await echo("hello")  # Must be awaited

All features work the same way: pipelines, modifiers, argument binding, and
concurrent execution. The imported commands are properly typed as ``AsyncLocalCommand``
for type checkers.

AsyncSshMachine
~~~~~~~~~~~~~~~

.. class:: AsyncSshMachine(host, user=None, port=None, keyfile=None, ...)

   Async version of SshMachine. Provides async SSH command execution.

   :param host: The host name to connect to
   :param user: The user to connect as
   :param port: The server's port
   :param keyfile: Path to the identity file
   :param password: Password to use (requires sshpass)
   :param encoding: Remote machine's encoding (default: utf8)
   :param connect_timeout: Connection timeout in seconds

   .. method:: __getitem__(cmd)

      Get an async remote command by name or path.

      :param cmd: Command name or RemotePath
      :return: AsyncRemoteCommand instance

   Use as an async context manager::

       async with AsyncSshMachine("host") as rem:
           result = await rem["ls"]()

Execution Modifiers
~~~~~~~~~~~~~~~~~~~

.. data:: AsyncTF

   Execution modifier that returns True/False based on exit code.

   Usage::

       result = await (async_local["test"]["-f", "file.txt"] & AsyncTF)

.. data:: AsyncRETCODE

   Execution modifier that returns only the exit code.

   Usage::

       code = await (async_local["ls"]["/nonexistent"] & AsyncRETCODE)

.. data:: AsyncTEE

   Execution modifier that displays output in real-time and returns it.

   Usage::

       retcode, stdout, stderr = await (async_local["echo"]["hello"] & AsyncTEE)
