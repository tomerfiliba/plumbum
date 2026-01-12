"""Tests for async command execution."""

from __future__ import annotations

import asyncio
import sys

import pytest

from plumbum import async_local, local
from plumbum._testtools import skip_on_windows
from plumbum.commands import ProcessExecutionError
from plumbum.commands.async_ import AsyncLocalCommand
from plumbum.machines.local import AsyncLocalMachine


class TestAsyncImports:
    """Tests for async module imports."""

    def test_import_from_plumbum(self):
        """Test that async_local can be imported from plumbum."""
        from plumbum import async_local as al

        assert isinstance(al, AsyncLocalMachine)

    def test_import_from_machines_local(self):
        """Test that async_local can be imported from plumbum.machines.local."""
        from plumbum.machines.local import async_local as al

        assert isinstance(al, AsyncLocalMachine)

    def test_both_imports_same_instance(self):
        """Test that both import paths return the same singleton instance."""
        from plumbum import async_local as al1
        from plumbum.machines.local import async_local as al2

        assert al1 is al2


class TestAsyncCmdImport:
    """Tests for async_cmd module import mechanism."""

    @pytest.mark.asyncio
    async def test_import_command(self):
        """Test importing a command from async_cmd."""
        from plumbum.async_cmd import echo

        assert isinstance(echo, AsyncLocalCommand)
        result = await echo("test")
        assert "test" in result

    @pytest.mark.asyncio
    async def test_import_multiple_commands(self):
        """Test importing multiple commands."""
        from plumbum.async_cmd import echo, ls

        assert isinstance(echo, AsyncLocalCommand)
        assert isinstance(ls, AsyncLocalCommand)

        result = await echo("hello")
        assert "hello" in result

    @pytest.mark.asyncio
    async def test_command_with_args(self):
        """Test using imported command with arguments."""
        from plumbum.async_cmd import echo

        result = await echo["hello", "world"]()
        assert "hello world" in result

    @pytest.mark.asyncio
    async def test_pipeline(self):
        """Test pipeline with imported commands."""
        if sys.platform == "win32":
            pytest.skip("Pipeline test requires Unix-like system")

        from plumbum.async_cmd import echo, grep

        result = await (echo["test line"] | grep["test"])()
        assert "test" in result

    @pytest.mark.asyncio
    async def test_concurrent_execution(self):
        """Test concurrent execution with imported commands."""
        from plumbum.async_cmd import echo

        results = await asyncio.gather(
            echo("task1"),
            echo("task2"),
            echo("task3"),
        )

        assert len(results) == 3
        assert "task1" in results[0]
        assert "task2" in results[1]
        assert "task3" in results[2]

    def test_nonexistent_command_raises_attribute_error(self):
        """Test that importing nonexistent command raises ImportError."""
        with pytest.raises(ImportError):
            from plumbum.async_cmd import nonexistent_command_xyz_123  # noqa: F401

    @pytest.mark.asyncio
    async def test_command_binding(self):
        """Test that command binding works with imported commands."""
        from plumbum.async_cmd import echo

        # Bind arguments
        bound = echo["hello"]
        result = await bound()
        assert "hello" in result

        # Chain binding
        bound2 = bound["world"]
        result2 = await bound2()
        assert "hello" in result2
        assert "world" in result2

    @pytest.mark.asyncio
    async def test_sync_vs_async_import(self):
        """Test that async_cmd returns async commands, not sync."""
        from plumbum.async_cmd import echo as async_echo
        from plumbum.cmd import echo as sync_echo

        # They should be different types
        assert type(async_echo) is not type(sync_echo)
        assert isinstance(async_echo, AsyncLocalCommand)

        # Async version requires await
        result = await async_echo("test")
        assert "test" in result

        # Sync version doesn't
        sync_result = sync_echo("test")
        assert "test" in sync_result

    @pytest.mark.asyncio
    async def test_import_from_plumbum_module(self):
        """Test that async_cmd is accessible from plumbum module."""
        import plumbum

        assert hasattr(plumbum, "async_cmd")

        # Can use it to get commands
        echo = plumbum.async_cmd.echo
        assert isinstance(echo, AsyncLocalCommand)
        result = await echo("test")
        assert "test" in result

    @pytest.mark.asyncio
    async def test_dynamic_import(self):
        """Test dynamic command import."""
        from plumbum import async_cmd

        # Get command dynamically
        echo = async_cmd.echo
        assert isinstance(echo, AsyncLocalCommand)
        result = await echo("test")
        assert "test" in result

    @pytest.mark.asyncio
    async def test_modifiers_with_imported_commands(self):
        """Test execution modifiers with imported commands."""
        from plumbum.commands.async_ import AsyncRETCODE, AsyncTEE, AsyncTF

        if sys.platform == "win32":
            from plumbum.async_cmd import cmd

            true_cmd = cmd["/c", "exit 0"]
            echo_cmd = cmd["/c", "echo hello"]
        else:
            try:
                from plumbum.async_cmd import echo, true

                true_cmd = true
                echo_cmd = echo["hello"]
            except ImportError:
                from plumbum.async_cmd import sh

                true_cmd = sh["-c", "exit 0"]
                echo_cmd = sh["-c", "echo hello"]

        # AsyncTF
        result = await (true_cmd & AsyncTF)
        assert result is True

        # AsyncRETCODE
        retcode = await (true_cmd & AsyncRETCODE)
        assert retcode == 0

        # AsyncTEE
        retcode, stdout, _stderr = await (echo_cmd & AsyncTEE)
        assert retcode == 0
        assert "hello" in stdout

    @pytest.mark.asyncio
    async def test_command_execution_methods(self):
        """Test that imported commands have all execution methods."""
        from plumbum.async_cmd import echo

        # Test run method
        result = await echo.run(["test"])
        assert result.returncode == 0
        assert "test" in result.stdout

        # Test call method
        output = await echo("test")
        assert "test" in output

    @pytest.mark.asyncio
    async def test_error_handling_with_imported_commands(self):
        """Test error handling with imported commands."""
        from plumbum.commands import ProcessExecutionError

        if sys.platform == "win32":
            from plumbum.async_cmd import cmd

            false_cmd = cmd["/c", "exit 1"]
        else:
            # Import false command (or use sh -c)
            try:
                from plumbum.async_cmd import false as false_cmd
            except AttributeError:
                from plumbum.async_cmd import sh

                false_cmd = sh["-c", "exit 1"]

        with pytest.raises(ProcessExecutionError):
            await false_cmd.run()

    def test_module_has_docstring(self):
        """Test that async_cmd module has documentation."""
        import plumbum.async_cmd

        assert plumbum.async_cmd.__doc__ is not None
        assert "async" in plumbum.async_cmd.__doc__.lower()

    def test_getattr_has_docstring(self):
        """Test that __getattr__ has documentation."""
        import plumbum.async_cmd

        assert plumbum.async_cmd.__getattr__.__doc__ is not None


class TestAsyncLocalCommand:
    """Tests for AsyncLocalCommand."""

    @pytest.mark.asyncio
    async def test_simple_command(self):
        """Test basic async command execution."""
        ls = async_local["ls"]
        result = await ls.run(["-la"])
        assert result.returncode == 0
        assert result.stdout
        assert isinstance(result.stdout, str)

    @pytest.mark.asyncio
    async def test_command_call_shortcut(self):
        """Test calling command directly returns stdout."""
        ls = async_local["ls"]
        output = await ls("-la")
        assert isinstance(output, str)
        assert output  # Should have some output

    @pytest.mark.asyncio
    async def test_command_with_args(self):
        """Test command with bound arguments."""
        ls = async_local["ls"]["-l", "-a"]
        result = await ls.run()
        assert result.returncode == 0
        assert result.stdout

    @pytest.mark.asyncio
    async def test_command_getitem(self):
        """Test binding arguments with []."""
        echo = async_local["echo"]
        result = await echo["hello", "world"]()
        assert "hello world" in result

    @pytest.mark.asyncio
    async def test_return_code_validation(self):
        """Test that non-zero return codes raise exceptions."""
        false_cmd = (
            async_local["false"]
            if "false" in local
            else async_local["cmd"]["/c", "exit 1"]
        )

        with pytest.raises(ProcessExecutionError) as exc_info:
            await false_cmd.run()

        assert exc_info.value.retcode != 0

    @pytest.mark.asyncio
    async def test_return_code_none(self):
        """Test disabling return code validation."""
        false_cmd = (
            async_local["false"]
            if "false" in local
            else async_local["cmd"]["/c", "exit 1"]
        )

        result = await false_cmd.run(retcode=None)
        assert result.returncode != 0

    @pytest.mark.asyncio
    async def test_return_code_multiple(self):
        """Test accepting multiple return codes."""
        false_cmd = (
            async_local["false"]
            if "false" in local
            else async_local["cmd"]["/c", "exit 1"]
        )

        result = await false_cmd.run(retcode=(0, 1))
        assert result.returncode in (0, 1)

    @pytest.mark.asyncio
    async def test_timeout(self):
        """Test command timeout."""
        sleep = async_local["sleep"] if "sleep" in local else async_local["timeout"]

        if "sleep" in local:
            with pytest.raises(asyncio.TimeoutError):
                await sleep.run(["5"], timeout=0.5)
        else:
            # Windows timeout command
            with pytest.raises(asyncio.TimeoutError):
                await sleep.run(["5"], timeout=0.5)

    @pytest.mark.asyncio
    async def test_stderr_capture(self):
        """Test that stderr is captured."""
        # Use a command that writes to stderr
        if sys.platform == "win32":
            cmd = async_local["cmd"]["/c", "echo error 1>&2"]
        else:
            cmd = async_local["sh"]["-c", "echo error >&2"]

        result = await cmd.run()
        assert "error" in result.stderr

    @pytest.mark.asyncio
    async def test_async_popen(self):
        """Test async_popen for process interaction."""
        echo = async_local["cat"] if "cat" in local else async_local["findstr"][".*"]

        proc = await echo.popen()
        assert proc.stdin is not None
        assert proc.stdout is not None

        # Write to stdin
        proc.stdin.write(b"hello\\n")
        await proc.stdin.drain()
        proc.stdin.close()

        # Read from stdout
        output = await proc.stdout.read()
        await proc.wait()

        assert b"hello" in output

    @pytest.mark.asyncio
    async def test_concurrent_commands(self):
        """Test running multiple commands concurrently."""
        echo = async_local["echo"]

        # Run multiple commands concurrently
        results = await asyncio.gather(
            echo("test1"),
            echo("test2"),
            echo("test3"),
        )

        assert len(results) == 3
        assert "test1" in results[0]
        assert "test2" in results[1]
        assert "test3" in results[2]


@skip_on_windows
class TestAsyncPipeline:
    """Tests for async command pipelines."""

    @pytest.mark.asyncio
    async def test_simple_pipeline(self):
        """Test basic pipeline."""
        ls = async_local["ls"]
        grep = async_local["grep"]

        pipeline = ls | grep["test"]
        result = await pipeline.run()

        assert result.returncode == 0
        # Should contain files with 'test' in the name
        assert "test" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_pipeline_call_shortcut(self):
        """Test calling pipeline directly."""
        echo = async_local["echo"]
        grep = async_local["grep"]

        output = await (echo["hello world"] | grep["hello"])()
        assert "hello" in output

    @pytest.mark.asyncio
    async def test_multi_stage_pipeline(self):
        """Test pipeline with multiple stages."""
        # Create a simple multi-stage pipeline
        # List files, filter for .py, count them
        ls = async_local["ls"]
        grep = async_local["grep"]
        wc = async_local["wc"]

        pipeline = ls | grep["\\.py"] | wc["-l"]
        result = await pipeline.run()

        assert result.returncode == 0
        # Should have at least one .py file (this test file)
        count = int(result.stdout.strip())
        assert count >= 1

    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self):
        """Test error handling in pipelines."""
        ls = async_local["ls"]
        grep = async_local["grep"]

        # Grep with invalid option should fail
        pipeline = ls | grep["--invalid-option-xyz"]

        with pytest.raises(ProcessExecutionError):
            await pipeline.run()

    @pytest.mark.asyncio
    async def test_pipeline_timeout(self):
        """Test pipeline timeout."""
        # Use yes command which produces infinite output, piped to a slow consumer
        yes_cmd = async_local["yes"]
        sleep_cmd = async_local["sleep"]["10"]

        # This pipeline will timeout because sleep takes 10 seconds
        pipeline = yes_cmd | sleep_cmd

        with pytest.raises(asyncio.TimeoutError):
            await pipeline.run(timeout=0.5)


class TestAsyncLocalMachine:
    """Tests for AsyncLocalMachine."""

    @pytest.mark.asyncio
    async def test_getitem(self):
        """Test getting commands via []."""
        ls = async_local["ls"]
        assert isinstance(ls, AsyncLocalCommand)

    @pytest.mark.asyncio
    async def test_contains(self):
        """Test checking if command exists."""
        assert "ls" in async_local or "dir" in async_local
        assert "nonexistent_command_xyz" not in async_local

    @pytest.mark.asyncio
    async def test_cwd(self):
        """Test accessing current working directory."""
        assert async_local.cwd == local.cwd

    @pytest.mark.asyncio
    async def test_env(self):
        """Test accessing environment."""
        assert async_local.env == local.env

    @pytest.mark.asyncio
    async def test_path(self):
        """Test path creation."""
        p = async_local.path("/tmp")
        assert str(p) == str(local.path("/tmp"))


class TestAsyncResult:
    """Tests for AsyncResult."""

    @pytest.mark.asyncio
    async def test_result_attributes(self):
        """Test AsyncResult attributes."""
        echo = async_local["echo"]
        result = await echo.run(["hello"])

        assert hasattr(result, "returncode")
        assert hasattr(result, "stdout")
        assert hasattr(result, "stderr")
        assert result.returncode == 0
        assert "hello" in result.stdout

    @pytest.mark.asyncio
    async def test_result_str(self):
        """Test AsyncResult string representation."""
        echo = async_local["echo"]
        result = await echo.run(["test"])

        assert "test" in str(result)

    @pytest.mark.asyncio
    async def test_result_repr(self):
        """Test AsyncResult repr."""
        echo = async_local["echo"]
        result = await echo.run(["test"])

        repr_str = repr(result)
        assert "AsyncResult" in repr_str
        assert "returncode" in repr_str


class TestAsyncModifiers:
    """Tests for async execution modifiers."""

    @pytest.mark.asyncio
    async def test_async_tf_success(self):
        """Test AsyncTF returns True on expected retcode."""
        from plumbum.commands.async_ import AsyncTF

        true_cmd = (
            async_local["true"]
            if "true" in local
            else async_local["cmd"]["/c", "exit 0"]
        )
        result = await (true_cmd & AsyncTF)
        assert result is True

    @pytest.mark.asyncio
    async def test_async_tf_failure(self):
        """Test AsyncTF returns False on unexpected retcode."""
        from plumbum.commands.async_ import AsyncTF

        false_cmd = (
            async_local["false"]
            if "false" in local
            else async_local["cmd"]["/c", "exit 1"]
        )
        result = await (false_cmd & AsyncTF)
        assert result is False

    @pytest.mark.asyncio
    async def test_async_tf_custom_retcode(self):
        """Test AsyncTF with custom expected retcode."""
        from plumbum.commands.async_ import AsyncTF

        if sys.platform == "win32":
            cmd = async_local["cmd"]["/c", "exit 5"]
        else:
            cmd = async_local["sh"]["-c", "exit 5"]

        result = await (cmd & AsyncTF(5))
        assert result is True

        result = await (cmd & AsyncTF(0))
        assert result is False

    @pytest.mark.asyncio
    async def test_async_retcode_success(self):
        """Test AsyncRETCODE returns exit code."""
        from plumbum.commands.async_ import AsyncRETCODE

        true_cmd = (
            async_local["true"]
            if "true" in local
            else async_local["cmd"]["/c", "exit 0"]
        )
        retcode = await (true_cmd & AsyncRETCODE)
        assert retcode == 0

    @pytest.mark.asyncio
    async def test_async_retcode_failure(self):
        """Test AsyncRETCODE returns non-zero exit code."""
        from plumbum.commands.async_ import AsyncRETCODE

        false_cmd = (
            async_local["false"]
            if "false" in local
            else async_local["cmd"]["/c", "exit 1"]
        )
        retcode = await (false_cmd & AsyncRETCODE)
        assert retcode != 0

    @pytest.mark.asyncio
    async def test_async_retcode_custom(self):
        """Test AsyncRETCODE with custom exit code."""
        from plumbum.commands.async_ import AsyncRETCODE

        if sys.platform == "win32":
            cmd = async_local["cmd"]["/c", "exit 42"]
        else:
            cmd = async_local["sh"]["-c", "exit 42"]

        retcode = await (cmd & AsyncRETCODE)
        assert retcode == 42

    @pytest.mark.asyncio
    async def test_async_tee_output(self):
        """Test AsyncTEE returns output and displays it."""
        from plumbum.commands.async_ import AsyncTEE

        echo = async_local["echo"]
        retcode, stdout, stderr = await (echo["hello world"] & AsyncTEE)

        assert retcode == 0
        assert "hello world" in stdout
        assert isinstance(stdout, str)
        assert isinstance(stderr, str)
        assert len(stdout) > 0

    @pytest.mark.asyncio
    async def test_async_tee_error(self):
        """Test AsyncTEE with command that produces stderr."""
        from plumbum.commands.async_ import AsyncTEE

        if sys.platform == "win32":
            cmd = async_local["cmd"]["/c", "echo error 1>&2"]
        else:
            cmd = async_local["sh"]["-c", "echo error >&2"]

        retcode, stdout, stderr = await (cmd & AsyncTEE)
        assert retcode == 0
        assert "error" in stderr
        assert isinstance(stdout, str)
        assert isinstance(stderr, str)

    @pytest.mark.asyncio
    async def test_async_tee_both_streams(self):
        """Test AsyncTEE captures both stdout and stderr."""
        from plumbum.commands.async_ import AsyncTEE

        if sys.platform == "win32":
            cmd = async_local["cmd"]["/c", "echo stdout && echo stderr 1>&2"]
        else:
            cmd = async_local["sh"]["-c", "echo stdout; echo stderr >&2"]

        retcode, stdout, stderr = await (cmd & AsyncTEE)
        assert retcode == 0
        assert "stdout" in stdout
        assert "stderr" in stderr
        assert isinstance(stdout, str)
        assert isinstance(stderr, str)

    @pytest.mark.asyncio
    async def test_async_tee_failure(self):
        """Test AsyncTEE with failing command."""
        from plumbum.commands.async_ import AsyncTEE

        false_cmd = (
            async_local["false"]
            if "false" in local
            else async_local["cmd"]["/c", "exit 1"]
        )

        with pytest.raises(ProcessExecutionError):
            await (false_cmd & AsyncTEE)

    @pytest.mark.asyncio
    async def test_async_tee_custom_retcode(self):
        """Test AsyncTEE with custom expected retcode."""
        from plumbum.commands.async_ import AsyncTEE

        if sys.platform == "win32":
            cmd = async_local["cmd"]["/c", "exit 5"]
        else:
            cmd = async_local["sh"]["-c", "exit 5"]

        retcode, _stdout, _stderr = await (cmd & AsyncTEE(5))
        assert retcode == 5


class TestAsyncIntegration:
    """Integration tests for async functionality."""

    @pytest.mark.asyncio
    async def test_basic_command_manual(self):
        """Test basic async command execution (from manual tests)."""
        if sys.platform == "win32":
            result = await async_local["cmd"]["/c", "echo hello"]()
        else:
            result = await async_local["echo"]("hello")
        assert "hello" in result

    @pytest.mark.asyncio
    @skip_on_windows
    async def test_pipeline_manual(self):
        """Test pipeline execution (from manual tests)."""
        result = await (
            async_local["echo"]["test line"] | async_local["grep"]["test"]
        )()
        assert "test" in result

    @pytest.mark.asyncio
    async def test_concurrent_manual(self):
        """Test concurrent execution (from manual tests)."""
        if sys.platform == "win32":
            cmd = async_local["cmd"]["/c", "echo"]
        else:
            cmd = async_local["echo"]

        results = await asyncio.gather(
            cmd("test1"),
            cmd("test2"),
            cmd("test3"),
        )

        assert len(results) == 3
        assert "test1" in results[0]
        assert "test2" in results[1]
        assert "test3" in results[2]

    @pytest.mark.asyncio
    async def test_error_handling_manual(self):
        """Test error handling (from manual tests)."""
        if sys.platform == "win32":
            cmd = async_local["cmd"]["/c", "exit 1"]
        else:
            cmd = async_local["false"]

        with pytest.raises(ProcessExecutionError):
            await cmd.run()

    @pytest.mark.asyncio
    async def test_async_result_manual(self):
        """Test AsyncResult object (from manual tests)."""
        if sys.platform == "win32":
            cmd = async_local["cmd"]["/c", "echo test"]
        else:
            cmd = async_local["echo"]["test"]

        result = await cmd.run()
        assert hasattr(result, "returncode")
        assert hasattr(result, "stdout")
        assert hasattr(result, "stderr")
        assert result.returncode == 0
        assert "test" in result.stdout

    @pytest.mark.asyncio
    async def test_sync_async_coexist_manual(self):
        """Test that sync and async can coexist (from manual tests)."""
        # Run sync command
        if sys.platform == "win32":
            sync_result = local["cmd"]["/c", "echo sync"]()
        else:
            sync_result = local["echo"]("sync")

        # Run async command
        if sys.platform == "win32":
            async_result = await async_local["cmd"]["/c", "echo async"]()
        else:
            async_result = await async_local["echo"]("async")

        assert "sync" in sync_result
        assert "async" in async_result

    @pytest.mark.asyncio
    @skip_on_windows
    async def test_real_world_example(self):
        """Test a real-world use case."""
        # List Python files in current directory
        ls = async_local["ls"]
        grep = async_local["grep"]

        result = await (ls | grep[".py"])()

        # Should find at least this test file
        assert "test_async" in result or ".py" in result

    @pytest.mark.asyncio
    async def test_environment_variables(self):
        """Test passing environment variables."""
        printenv = (
            async_local["printenv"]
            if "printenv" in local
            else async_local["sh"]["-c", "echo $TEST_VAR"]
        )

        if "printenv" in local:
            result = await printenv.run(["TEST_VAR"], env={"TEST_VAR": "test_value"})
        else:
            result = await printenv.run(env={"TEST_VAR": "test_value"})

        assert "test_value" in result.stdout

    @pytest.mark.asyncio
    @skip_on_windows
    async def test_working_directory(self):
        """Test changing working directory."""
        pwd = async_local["pwd"]
        result = await pwd.run(cwd="/tmp")
        assert "/tmp" in result.stdout

    @pytest.mark.asyncio
    async def test_mixed_sync_async(self):
        """Test that sync and async can coexist."""
        # Run sync command
        sync_result = local["echo"]("sync")

        # Run async command
        async_result = await async_local["echo"]("async")

        assert "sync" in sync_result
        assert "async" in async_result
