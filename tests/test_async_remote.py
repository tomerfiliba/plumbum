"""Tests for async remote command execution."""

from __future__ import annotations

import asyncio

import pytest

from plumbum import SshMachine
from plumbum.commands import ProcessExecutionError
from plumbum.commands.async_ import AsyncRemoteCommand
from plumbum.machines.ssh_machine import AsyncSshMachine

pytestmark = pytest.mark.ssh

TEST_HOST = "127.0.0.1"


class TestAsyncRemoteCommand:
    """Tests for AsyncRemoteCommand."""

    @pytest.mark.asyncio
    async def test_simple_command(self):
        """Test basic async remote command execution."""
        async with AsyncSshMachine(TEST_HOST) as rem:
            ls = rem["ls"]
            result = await ls.run(["-la"])
            assert result.returncode == 0
            assert result.stdout
            assert isinstance(result.stdout, str)

    @pytest.mark.asyncio
    async def test_command_call_shortcut(self):
        """Test calling command directly returns stdout."""
        async with AsyncSshMachine(TEST_HOST) as rem:
            echo = rem["echo"]
            output = await echo("hello")
            assert "hello" in output

    @pytest.mark.asyncio
    async def test_command_with_args(self):
        """Test command with bound arguments."""
        async with AsyncSshMachine(TEST_HOST) as rem:
            ls = rem["ls"]["-l", "-a"]
            result = await ls.run()
            assert result.returncode == 0
            assert result.stdout

    @pytest.mark.asyncio
    async def test_return_code_validation(self):
        """Test that non-zero return codes raise exceptions."""
        async with AsyncSshMachine(TEST_HOST) as rem:
            false_cmd = rem["false"]

            with pytest.raises(ProcessExecutionError) as exc_info:
                await false_cmd.run()

            assert exc_info.value.retcode != 0

    @pytest.mark.asyncio
    async def test_return_code_none(self):
        """Test disabling return code validation."""
        async with AsyncSshMachine(TEST_HOST) as rem:
            false_cmd = rem["false"]
            result = await false_cmd.run(retcode=None)
            assert result.returncode != 0

    @pytest.mark.asyncio
    async def test_concurrent_commands(self):
        """Test running multiple remote commands concurrently."""
        async with AsyncSshMachine(TEST_HOST) as rem:
            echo = rem["echo"]

            results = await asyncio.gather(
                echo("test1"),
                echo("test2"),
                echo("test3"),
            )

            assert len(results) == 3
            assert "test1" in results[0]
            assert "test2" in results[1]
            assert "test3" in results[2]


class TestAsyncRemotePipeline:
    """Tests for async remote command pipelines."""

    @pytest.mark.asyncio
    async def test_simple_pipeline(self):
        """Test basic remote pipeline."""
        async with AsyncSshMachine(TEST_HOST) as rem:
            ls = rem["ls"]
            grep = rem["grep"]

            pipeline = ls | grep["test"]
            result = await pipeline.run()

            assert result.returncode == 0

    @pytest.mark.asyncio
    async def test_pipeline_call_shortcut(self):
        """Test calling remote pipeline directly."""
        async with AsyncSshMachine(TEST_HOST) as rem:
            echo = rem["echo"]
            grep = rem["grep"]

            output = await (echo["hello world"] | grep["hello"])()
            assert "hello" in output


class TestAsyncSshMachine:
    """Tests for AsyncSshMachine."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test AsyncSshMachine as async context manager."""
        async with AsyncSshMachine(TEST_HOST) as rem:
            assert rem is not None
            ls = rem["ls"]
            result = await ls.run()
            assert result.returncode == 0

    @pytest.mark.asyncio
    async def test_getitem(self):
        """Test getting remote commands via []."""
        async with AsyncSshMachine(TEST_HOST) as rem:
            ls = rem["ls"]
            assert isinstance(ls, AsyncRemoteCommand)

    @pytest.mark.asyncio
    async def test_contains(self):
        """Test checking if remote command exists."""
        async with AsyncSshMachine(TEST_HOST) as rem:
            assert "ls" in rem
            assert "nonexistent_command_xyz" not in rem

    @pytest.mark.asyncio
    async def test_env(self):
        """Test remote environment access."""
        async with AsyncSshMachine(TEST_HOST) as rem:
            assert rem.env is not None

    @pytest.mark.asyncio
    async def test_cwd(self):
        """Test remote working directory access."""
        async with AsyncSshMachine(TEST_HOST) as rem:
            assert rem.cwd is not None


class TestAsyncRemoteModifiers:
    """Tests for async modifiers with remote commands."""

    @pytest.mark.asyncio
    async def test_async_tf_remote(self):
        """Test AsyncTF with remote command."""
        from plumbum.commands.async_ import AsyncTF

        async with AsyncSshMachine(TEST_HOST) as rem:
            true_cmd = rem["true"]
            result = await (true_cmd & AsyncTF)
            assert result is True

    @pytest.mark.asyncio
    async def test_async_retcode_remote(self):
        """Test AsyncRETCODE with remote command."""
        from plumbum.commands.async_ import AsyncRETCODE

        async with AsyncSshMachine(TEST_HOST) as rem:
            true_cmd = rem["true"]
            retcode = await (true_cmd & AsyncRETCODE)
            assert retcode == 0

    @pytest.mark.asyncio
    async def test_async_tee_remote(self):
        """Test AsyncTEE with remote command."""
        from plumbum.commands.async_ import AsyncTEE

        async with AsyncSshMachine(TEST_HOST) as rem:
            echo = rem["echo"]
            retcode, stdout, _stderr = await (echo["hello"] & AsyncTEE)
            assert retcode == 0
            assert "hello" in stdout


class TestAsyncRemoteIntegration:
    """Integration tests for async remote functionality."""

    @pytest.mark.asyncio
    async def test_sync_async_coexist(self):
        """Test that sync and async remote can coexist."""
        # Sync remote
        with SshMachine(TEST_HOST) as sync_rem:
            sync_result = sync_rem["echo"]("sync")

        # Async remote
        async with AsyncSshMachine(TEST_HOST) as async_rem:
            async_result = await async_rem["echo"]("async")

        assert "sync" in sync_result
        assert "async" in async_result

    @pytest.mark.asyncio
    async def test_concurrent_remote_machines(self):
        """Test multiple concurrent remote connections."""

        async def run_on_remote(host: str, message: str) -> str:
            async with AsyncSshMachine(host) as rem:
                return await rem["echo"](message)

        results = await asyncio.gather(
            run_on_remote(TEST_HOST, "msg1"),
            run_on_remote(TEST_HOST, "msg2"),
            run_on_remote(TEST_HOST, "msg3"),
        )

        assert len(results) == 3
        assert "msg1" in results[0]
        assert "msg2" in results[1]
        assert "msg3" in results[2]
