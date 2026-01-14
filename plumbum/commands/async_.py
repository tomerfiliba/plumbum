"""Asyncio support for Plumbum commands.

This module provides async versions of Plumbum commands that can be used with
Python's asyncio framework. Commands can be awaited directly or used with
async context managers.

For async machines (AsyncLocalMachine, AsyncSshMachine), see plumbum.machines.async_

Design Philosophy
-----------------
This implementation uses **delegation over inheritance** to wrap existing sync
commands rather than reimplementing their functionality. This approach:

- Maximizes code reuse (~100 lines of logic delegated to sync commands)
- Ensures consistency between sync and async APIs
- Reduces maintenance burden (changes to sync code automatically apply)
- Enables automatic support for features like `with_env()` and `with_cwd()`

Why Delegation Instead of Inheritance?
---------------------------------------
Sync and async methods are fundamentally incompatible in Python:

- Sync methods return values directly: `def run() -> tuple[int, str, str]`
- Async methods return coroutines: `async def run() -> AsyncResult`

You cannot override a sync method with an async one in the same class hierarchy.
Therefore, we use separate classes that wrap and delegate to sync commands,
reusing all their formulation, binding, and pipeline logic.

Example Usage
-------------
::

    from plumbum import async_local

    async def main():
        # Simple command execution
        result = await async_local["ls"]("-la")
        print(result)

        # With explicit run method
        ls = async_local["ls"]
        result = await ls.run(["-la"])
        print(result.stdout)

        # Pipeline support
        result = await (async_local["ls"] | async_local["grep"]["py"])()
        print(result)

.. versionadded:: 2.0
"""

from __future__ import annotations

import asyncio
import sys
import typing
from typing import TYPE_CHECKING, Any

from plumbum.commands.processes import ProcessExecutionError
from plumbum.machines.local import local

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Container, Sequence

    from plumbum.commands.base import BaseCommand
    from plumbum.path.local import LocalPath


class AsyncResult:
    """Result of an async command execution.

    Attributes:
        returncode: The exit code of the process
        stdout: Standard output as a string
        stderr: Standard error as a string
    """

    __slots__ = ("returncode", "stderr", "stdout")

    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self) -> str:
        return self.stdout

    def __repr__(self) -> str:
        return f"AsyncResult(returncode={self.returncode}, stdout={self.stdout!r}, stderr={self.stderr!r})"


class AsyncCommandMixin:
    """Mixin that adds async execution capabilities to BaseCommand.

    This mixin wraps a sync BaseCommand and provides async execution methods
    while reusing all the existing formulation, binding, and pipeline logic.

    The delegation pattern allows us to:
    - Reuse BaseCommand.formulate() for command-to-argv conversion
    - Reuse BaseCommand.__getitem__() for argument binding
    - Reuse BaseCommand.__or__() for pipeline creation
    - Reuse BoundEnvCommand for environment and cwd handling
    - Maintain consistency with the sync API
    """

    __slots__ = ("_base_cmd",)

    _base_cmd: BaseCommand

    def __init__(self, base_cmd: BaseCommand):
        """Initialize with a sync BaseCommand to wrap.

        Args:
            base_cmd: The sync command to wrap and delegate to
        """
        self._base_cmd = base_cmd

    def __getitem__(self, args: Any) -> AsyncCommand:
        """Bind arguments using the base command's logic.

        This delegates to the sync command's __getitem__ method, which handles
        all the argument binding logic, then wraps the result in an AsyncCommand.
        """
        bound = self._base_cmd[args]
        return AsyncCommand(bound)

    def __call__(self, *args: Any, **kwargs: Any) -> typing.Coroutine[Any, Any, str]:
        """Execute the command asynchronously and return stdout.

        This is a shortcut for run() that returns only stdout, matching the
        behavior of the sync API's __call__ method.
        """

        async def _run() -> str:
            result = await self.run(args, **kwargs)
            return result.stdout

        return _run()

    def __or__(self, other: AsyncCommandMixin) -> AsyncPipeline:
        """Create a pipeline using the base command's logic.

        This delegates to the sync command's __or__ method to create a sync
        Pipeline, then wraps it in an AsyncPipeline.
        """
        sync_pipeline = self._base_cmd | other._base_cmd
        return AsyncPipeline(sync_pipeline)

    def formulate(self, level: int = 0, args: Sequence[Any] = ()) -> list[str]:
        """Delegate formulation to the base command.

        This reuses the sync command's formulation logic, which handles:
        - Converting the command to an argv list
        - Proper shell quoting based on nesting level
        - Handling of bound arguments
        - Support for nested commands
        """
        return self._base_cmd.formulate(level, args)

    async def run(
        self,
        args: Sequence[Any] = (),
        retcode: int | Container[int] | None = 0,
        timeout: float | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> AsyncResult:
        """Run the command asynchronously.

        Args:
            args: Additional arguments to pass to the command
            retcode: Expected return code(s). None to disable checking.
            timeout: Maximum time to wait for command completion
            cwd: Working directory for the command
            env: Environment variables for the command

        Returns:
            AsyncResult with returncode, stdout, and stderr

        Raises:
            ProcessExecutionError: If return code doesn't match expected
            asyncio.TimeoutError: If timeout is exceeded
        """
        # Use base command's formulate method
        argv = self._base_cmd.formulate(0, args)

        # Get encoding from base command
        encoding = self._base_cmd._get_encoding() or local.custom_encoding

        # Merge environment - reuse base command's env if set
        full_env = dict(local.env.getdict())
        base_env = getattr(self._base_cmd, "env", None)
        if base_env:
            full_env.update(base_env)
        if env:
            full_env.update(env)

        # Use base command's cwd if set
        base_cwd = getattr(self._base_cmd, "cwd", None)
        working_dir = cwd or base_cwd or str(local.cwd)

        # Create subprocess
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
            env=full_env,
        )

        # Wait for completion with timeout
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise

        # Decode output
        stdout = stdout_bytes.decode(encoding, errors="ignore") if stdout_bytes else ""
        stderr = stderr_bytes.decode(encoding, errors="ignore") if stderr_bytes else ""

        # Check return code - reuse the same logic as sync commands
        if retcode is not None:
            expected_codes: set[int] = (
                {retcode} if isinstance(retcode, int) else set(retcode)  # type: ignore[call-overload]
            )

            if proc.returncode not in expected_codes:
                raise ProcessExecutionError(
                    argv=argv,
                    retcode=proc.returncode,
                    stdout=stdout,
                    stderr=stderr,
                )

        return AsyncResult(proc.returncode or 0, stdout, stderr)

    async def popen(
        self,
        args: Sequence[Any] = (),
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> asyncio.subprocess.Process:
        """Create an async subprocess without waiting for it to complete.

        This is useful for long-running processes or when you need to
        interact with stdin/stdout/stderr.

        Args:
            args: Additional arguments to pass to the command
            cwd: Working directory for the command
            env: Environment variables for the command

        Returns:
            asyncio.subprocess.Process instance
        """
        # Use base command's formulate method
        argv = self._base_cmd.formulate(0, args)

        # Merge environment - reuse base command's env if set
        full_env = dict(local.env.getdict())
        base_env = getattr(self._base_cmd, "env", None)
        if base_env:
            full_env.update(base_env)
        if env:
            full_env.update(env)

        # Use base command's cwd if set
        base_cwd = getattr(self._base_cmd, "cwd", None)
        working_dir = cwd or base_cwd or str(local.cwd)

        # Create subprocess
        return await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
            cwd=working_dir,
            env=full_env,
        )


class AsyncCommand(AsyncCommandMixin):
    """Async wrapper for BaseCommand.

    This class wraps any BaseCommand and provides async execution capabilities.
    It reuses all the formulation, binding, and pipeline logic from the base command.

    Example::

        # The sync command is looked up and wrapped
        async_cmd = async_local["ls"]

        # Binding works via delegation to sync command
        bound_cmd = async_cmd["-la"]

        # Execution is async
        result = await bound_cmd.run()
    """

    __slots__ = ()


class AsyncPipeline(AsyncCommandMixin):
    """Async wrapper for Pipeline.

    This class wraps a sync Pipeline and provides async execution capabilities.
    It reuses the pipeline's formulation logic, which already includes the pipe
    symbols and proper command chaining.

    Example::

        # Pipeline creation delegates to sync commands
        pipeline = async_local["ls"] | async_local["grep"]["py"]

        # Execution is async
        result = await pipeline.run()
    """

    __slots__ = ()

    def __or__(self, other: AsyncCommandMixin) -> AsyncPipeline:
        """Add another command to the pipeline using base pipeline logic."""
        # Create a new sync pipeline, then wrap it
        sync_pipeline = self._base_cmd | other._base_cmd
        return AsyncPipeline(sync_pipeline)

    def __call__(self, *args: Any, **kwargs: Any) -> typing.Coroutine[Any, Any, str]:
        """Execute the pipeline and return stdout."""

        async def _run() -> str:
            result = await self.run(args, **kwargs)
            return result.stdout

        return _run()

    async def run(
        self,
        args: Sequence[Any] = (),
        retcode: int | Container[int] | None = 0,
        timeout: float | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> AsyncResult:
        """Run the pipeline asynchronously.

        Args:
            args: Additional arguments for the last command in the pipeline
            retcode: Expected return code(s) for the last command
            timeout: Maximum time to wait for pipeline completion
            cwd: Working directory
            env: Environment variables

        Returns:
            AsyncResult from the last command in the pipeline
        """
        # Use base pipeline's formulate method to build the command
        argv = self._base_cmd.formulate(0, args)

        # Build shell command from formulated args
        # The formulate method already includes the pipe symbols
        shell_cmd = " ".join(argv)

        # Get encoding from base command
        encoding = self._base_cmd._get_encoding() or local.custom_encoding

        # Merge environment - reuse base command's env if set
        full_env = dict(local.env.getdict())
        base_env = getattr(self._base_cmd, "env", None)
        if base_env:
            full_env.update(base_env)
        if env:
            full_env.update(env)

        # Use base command's cwd if set
        base_cwd = getattr(self._base_cmd, "cwd", None)
        working_dir = cwd or base_cwd or str(local.cwd)

        # Execute via shell
        proc = await asyncio.create_subprocess_shell(
            shell_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
            env=full_env,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise

        # Decode output
        stdout = stdout_bytes.decode(encoding, errors="ignore") if stdout_bytes else ""
        stderr = stderr_bytes.decode(encoding, errors="ignore") if stderr_bytes else ""

        # Check return code - reuse the same logic as sync commands
        if retcode is not None:
            expected_codes: set[int] = (
                {retcode} if isinstance(retcode, int) else set(retcode)  # type: ignore[call-overload]
            )

            if proc.returncode not in expected_codes:
                raise ProcessExecutionError(
                    argv=argv,
                    retcode=proc.returncode,
                    stdout=stdout,
                    stderr=stderr,
                )

        return AsyncResult(proc.returncode or 0, stdout, stderr)


class AsyncLocalCommand(AsyncCommand):
    """Async version of LocalCommand.

    This class wraps a LocalCommand and provides async execution methods.
    It reuses all the LocalCommand logic for formulation, binding, etc.
    """

    __slots__ = ()

    @property
    def executable(self) -> Any:
        """The path to the executable."""
        # Access the executable attribute from the base command
        # This is safe because LocalCommand has this attribute
        return self._base_cmd.executable  # type: ignore[attr-defined]


class AsyncLocalMachine:
    """Async version of LocalMachine.

    This class provides async access to local commands and utilities.
    It delegates to the sync LocalMachine for command lookup and wraps
    the results in AsyncLocalCommand.

    Example::

        from plumbum import async_local

        # Command lookup delegates to sync local machine
        ls = async_local["ls"]

        # Execution is async
        result = await ls("-la")
    """

    __slots__ = ()

    def __getitem__(self, cmd: str | LocalPath) -> AsyncLocalCommand:
        """Get an async command by name or path.

        This delegates to local[cmd] to get the sync command, then wraps it.

        Args:
            cmd: Command name (will be looked up in PATH) or LocalPath

        Returns:
            AsyncLocalCommand instance

        Raises:
            CommandNotFound: If command is not found in PATH
        """
        # Delegate to sync local machine for command lookup
        sync_cmd = local[cmd]
        return AsyncLocalCommand(sync_cmd)

    def __contains__(self, cmd: str) -> bool:
        """Check if a command exists in PATH."""
        # Delegate to sync local machine
        return cmd in local

    @property
    def cwd(self) -> Any:
        """Current working directory."""
        return local.cwd

    @property
    def env(self) -> Any:
        """Environment variables."""
        return local.env

    def path(self, *parts: str) -> Any:
        """Create a LocalPath from parts."""
        return local.path(*parts)


class AsyncRemoteCommand(AsyncCommand):
    """Async wrapper for RemoteCommand.

    This class wraps a RemoteCommand and provides async execution capabilities.
    It reuses all the RemoteCommand logic for formulation, binding, etc.

    Example::

        async with AsyncSshMachine("host") as rem:
            ls = rem["ls"]
            result = await ls("-la")

    .. versionadded:: 2.0
    """

    __slots__ = ()

    @property
    def remote(self) -> Any:
        """The remote machine this command belongs to."""
        return self._base_cmd.remote  # type: ignore[attr-defined]


# ===================================================================================================
# Async execution modifiers
# ===================================================================================================


class AsyncExecutionModifier:
    """Base class for async execution modifiers."""

    __slots__ = ("__weakref__",)

    def __repr__(self) -> str:
        """Automatically creates a representation for given subclass with slots."""
        slots = {}
        for cls in self.__class__.__mro__:
            slots_list = getattr(cls, "__slots__", ())
            if isinstance(slots_list, str):
                slots_list = (slots_list,)
            for prop in slots_list:
                if prop[0] != "_":
                    slots[prop] = getattr(self, prop)
        mystrs = (f"{name} = {value}" for name, value in slots.items())
        mystrs_str = ", ".join(mystrs)
        return f"{self.__class__.__name__}({mystrs_str})"

    @classmethod
    def __call__(cls, *args: Any, **kwargs: Any) -> Self:
        return cls(*args, **kwargs)


class _AsyncTF(AsyncExecutionModifier):
    """Async execution modifier that returns True/False based on return code.

    This is the async equivalent of the sync TF modifier. It runs the command
    and returns True if the exit code matches the expected value, False otherwise.

    Unlike the sync version, there is no FG parameter because async commands
    don't have a concept of foreground/background execution - they're all
    non-blocking by nature.

    Example::

        # Check if a file exists
        exists = await (async_local["test"]["-f", "file.txt"] & AsyncTF)

        # Check for specific exit code
        result = await (async_local["grep"]["pattern", "file.txt"] & AsyncTF(retcode=(0, 1)))

    .. versionadded:: 2.0
    """

    __slots__ = ("retcode", "timeout")

    def __init__(
        self,
        retcode: int | Container[int] = 0,
        timeout: float | None = None,
    ) -> None:
        """Initialize AsyncTF modifier.

        Args:
            retcode: Expected return code(s). Default is 0.
            timeout: Maximum time to wait for command completion.
        """
        self.retcode = retcode
        self.timeout = timeout

    async def __rand__(self, cmd: AsyncCommandMixin) -> bool:
        """Execute command and return True/False based on return code."""
        try:
            await cmd.run(retcode=self.retcode, timeout=self.timeout)
        except ProcessExecutionError:
            return False
        return True


class _AsyncRETCODE(AsyncExecutionModifier):
    """Async execution modifier that returns only the exit code.

    This is the async equivalent of the sync RETCODE modifier. It runs the
    command and returns only the exit code, ignoring stdout/stderr.

    Unlike the sync version, there is no FG parameter because async commands
    don't have a concept of foreground/background execution.

    Example::

        # Get exit code
        code = await (async_local["ls"]["/nonexistent"] & AsyncRETCODE)
        print(f"Exit code: {code}")

    .. versionadded:: 2.0
    """

    __slots__ = ("timeout",)

    def __init__(self, timeout: float | None = None) -> None:
        """Initialize AsyncRETCODE modifier.

        Args:
            timeout: Maximum time to wait for command completion.
        """
        self.timeout = timeout

    async def __rand__(self, cmd: AsyncCommandMixin) -> int:
        """Execute command and return exit code."""
        result = await cmd.run(retcode=None, timeout=self.timeout)
        return result.returncode


class _AsyncTEE(AsyncExecutionModifier):
    """Async execution modifier that displays output in real-time and returns it.

    This is the async equivalent of the sync TEE modifier. It runs the command,
    displays stdout/stderr to the console in real-time, and also returns them.

    Unlike the sync version, buffering is always enabled because async I/O
    handles buffering differently.

    Example::

        # Run command and see output in real-time
        retcode, stdout, stderr = await (async_local["npm"]["install"] & AsyncTEE)

        # With custom expected return code
        retcode, stdout, stderr = await (async_local["grep"]["pattern"] & AsyncTEE(retcode=(0, 1)))

    .. versionadded:: 2.0
    """

    __slots__ = ("retcode", "timeout")

    def __init__(
        self,
        retcode: int | Container[int] = 0,
        timeout: float | None = None,
    ) -> None:
        """Initialize AsyncTEE modifier.

        Args:
            retcode: Expected return code(s). Default is 0.
            timeout: Maximum time to wait for command completion.
        """
        self.retcode = retcode
        self.timeout = timeout

    async def __rand__(self, cmd: AsyncCommandMixin) -> tuple[int, str, str]:
        """Execute command, display output, and return (retcode, stdout, stderr)."""
        # Get encoding from base command
        encoding = cmd._base_cmd._get_encoding() or local.custom_encoding

        # Merge environment
        full_env = dict(local.env.getdict())
        base_env = getattr(cmd._base_cmd, "env", None)
        if base_env:
            full_env.update(base_env)

        # Use base command's cwd if set
        base_cwd = getattr(cmd._base_cmd, "cwd", None)
        working_dir = base_cwd or str(local.cwd)

        # Formulate command
        argv = cmd._base_cmd.formulate(0, ())

        # Create subprocess
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
            env=full_env,
        )

        # Collect output while displaying it
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        async def read_stream(
            stream: asyncio.StreamReader | None, output_list: list[str], target: Any
        ) -> None:
            """Read from stream, display, and collect output."""
            if stream is None:
                return

            while True:
                line = await stream.readline()
                if not line:
                    break

                text = line.decode(encoding, errors="ignore")
                output_list.append(text)
                target.write(text)
                target.flush()

        # Read stdout and stderr concurrently
        try:
            await asyncio.wait_for(
                asyncio.gather(
                    read_stream(proc.stdout, stdout_lines, sys.stdout),
                    read_stream(proc.stderr, stderr_lines, sys.stderr),
                ),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise

        # Wait for process to complete
        await proc.wait()

        # Combine output
        stdout = "".join(stdout_lines)
        stderr = "".join(stderr_lines)

        # Check return code
        if self.retcode is not None:
            expected_codes: set[int] = (
                {self.retcode} if isinstance(self.retcode, int) else set(self.retcode)  # type: ignore[call-overload]
            )

            if proc.returncode not in expected_codes:
                raise ProcessExecutionError(
                    argv=argv,
                    retcode=proc.returncode,
                    stdout=stdout,
                    stderr=stderr,
                )

        return proc.returncode or 0, stdout, stderr


# Singleton instances
AsyncTF = _AsyncTF()
AsyncRETCODE = _AsyncRETCODE()
AsyncTEE = _AsyncTEE()


__all__ = (
    "AsyncCommand",
    "AsyncLocalCommand",
    "AsyncPipeline",
    "AsyncRETCODE",
    "AsyncRemoteCommand",
    "AsyncResult",
    "AsyncTEE",
    "AsyncTF",
)
