import asyncio
import sys

import pytest

from plumbum import async_local, local

echo_cmd_template = "print({!r}\ncat 'test pipe2')"
upper_cmd = """
import sys
for line in sys.stdin:
    print(line.strip().upper())
"""

echo_cmd = "print('test pipe1\\ntest pipe2')"


class TestAsyncPipelineBasic:
    """Test basic async pipeline functionality."""

    @pytest.mark.asyncio
    async def test_async_pipeline_simple(self):
        echo = async_local[sys.executable]["-c", echo_cmd]
        upper = async_local[sys.executable]["-c", upper_cmd]

        command = echo | upper

        proc = await command.popen()
        assert proc.stdout is not None
        lines = []
        while i := await proc.stdout.readline():
            lines.append(i.decode().strip())

        assert len(lines) == 2
        assert lines == ["TEST PIPE1", "TEST PIPE2"]
        await proc.wait()
        assert proc.returncode == 0

    @pytest.mark.asyncio
    async def test_async_pipeline_readline_return_code(self):
        echo = async_local[sys.executable]["-c", echo_cmd]
        upper = async_local[sys.executable]["-c", upper_cmd]

        command = echo | upper

        proc = await command.popen()
        assert proc.stdout is not None
        lines = []
        while i := await proc.stdout.readline():
            lines.append(i.decode().strip())

        assert len(lines) == 2
        assert lines == ["TEST PIPE1", "TEST PIPE2"]
        # Ensure child processes are reaped and return code is checked
        await proc.wait()
        assert proc.returncode == 0

    @pytest.mark.asyncio
    async def test_async_pipeline_empty_output(self):
        empty = async_local[sys.executable]["-c", "pass"]
        upper = async_local[sys.executable]["-c", upper_cmd]

        command = empty | upper

        proc = await command.popen()
        assert proc.stdout is not None
        lines = []
        while i := await proc.stdout.readline():
            lines.append(i.decode().strip())

        assert len(lines) == 0
        await proc.wait()
        assert proc.returncode == 0

    @pytest.mark.asyncio
    async def test_async_pipeline_wait_completes(self):
        echo = async_local[sys.executable]["-c", echo_cmd]
        upper = async_local[sys.executable]["-c", upper_cmd]

        proc = await (echo | upper).popen()
        returncode = await proc.wait()
        assert returncode == 0


class TestAsyncPipelineGetitem:
    """Test argument binding on async pipelines (__getitem__)."""

    @pytest.mark.asyncio
    async def test_async_pipeline_getitem_binds_to_right_command(self):
        """Arguments bound to pipeline should go to destination (right) command."""
        async_local[sys.executable]["-c", "import sys; print(sys.argv[1].lower())"]

        # hello | lower should send "hello" to lower's stdin, not as lower's arg
        # We use cat | python to test: cat pipes input to python script
        cat = async_local["cat"]
        py = async_local[sys.executable]["-c", "import sys; print(sys.argv[1].upper())"]

        # Bind "hello" to the pipeline: should be bound to py, the right side
        bound = (cat | py)["hello"]

        # Send "world" to cat, py should get "hello" as its argument
        proc = await bound.popen()
        proc.stdin.write(b"world\n")
        await proc.stdin.drain()
        proc.stdin.close()
        stdout = await proc.stdout.read()
        stdout_text = stdout.decode().strip()
        await proc.wait()
        assert stdout_text == "HELLO", f"Expected 'HELLO', got {stdout_text!r}"

    @pytest.mark.asyncio
    async def test_async_pipeline_getitem_multi_stage(self):
        """Multi-stage pipeline binding: (a | b | c)[args] == (a | b) | c[args]."""
        cat = async_local["cat"]
        echo = async_local[sys.executable]["-c", "import sys; print(sys.argv[1])"]

        # (cat | cat | echo)["hello"] should bind "hello" to echo
        pipeline = cat | cat | echo
        bound = pipeline["hello"]

        proc = await bound.popen()
        proc.stdin.write(b"world\n")
        await proc.stdin.drain()
        proc.stdin.close()
        stdout = await proc.stdout.read()
        stdout_text = stdout.decode().strip()
        await proc.wait()
        assert stdout_text == "hello", f"Expected 'hello', got {stdout_text!r}"

    @pytest.mark.asyncio
    async def test_async_pipeline_bound_command(self):
        """Test bound_command() method preserves pipeline type."""
        echo = async_local[sys.executable]["-c", echo_cmd]
        upper = async_local[sys.executable]["-c", upper_cmd]

        bound = (echo | upper).bound_command()
        assert isinstance(bound, type(echo | upper))


class TestAsyncPipelineCommunicate:
    """Test AsyncPipelineProcess.communicate() with input."""

    @pytest.mark.asyncio
    async def test_async_pipeline_communicate(self):
        cat1 = async_local["cat"]
        cat2 = async_local["cat"]

        proc = await (cat1 | cat2).popen()
        stdout, _stderr = await proc.communicate(b"hello world\n")
        assert stdout == b"hello world\n"
        assert proc.returncode == 0

    @pytest.mark.asyncio
    async def test_async_pipeline_communicate_multiple_lines(self):
        cat1 = async_local["cat"]
        cat2 = async_local["cat"]

        proc = await (cat1 | cat2).popen()
        input_data = b"line1\nline2\nline3\n"
        stdout, _stderr = await proc.communicate(input_data)
        assert stdout == input_data
        assert proc.returncode == 0

    @pytest.mark.asyncio
    async def test_async_pipeline_communicate_empty_input(self):
        cat1 = async_local["cat"]
        cat2 = async_local["cat"]

        proc = await (cat1 | cat2).popen()
        stdout, _stderr = await proc.communicate(b"")
        assert stdout == b""
        assert proc.returncode == 0

    @pytest.mark.asyncio
    async def test_async_pipeline_communicate_without_input(self):
        """communicate() without input should still work."""
        echo = async_local[sys.executable]["-c", echo_cmd]
        upper = async_local[sys.executable]["-c", upper_cmd]

        proc = await (echo | upper).popen()
        stdout, _stderr = await proc.communicate()
        stdout_text = stdout.decode().strip() if stdout else ""
        lines = [line for line in stdout_text.split("\n") if line.strip()]
        assert lines == ["TEST PIPE1", "TEST PIPE2"]
        assert proc.returncode == 0

    @pytest.mark.asyncio
    async def test_async_pipeline_communicate_transforms_data(self):
        """Input flows through pipeline stages and gets transformed."""
        cat = async_local["cat"]
        upper = async_local[sys.executable]["-c", upper_cmd]

        proc = await (cat | upper).popen()
        stdout, _stderr = await proc.communicate(b"hello world\n")
        assert stdout == b"HELLO WORLD\n"
        assert proc.returncode == 0


class TestAsyncPipelineMultiStage:
    """Test multi-stage async pipelines."""

    @pytest.mark.asyncio
    async def test_three_stage_pipeline(self):
        cat = async_local["cat"]
        upper = async_local[sys.executable]["-c", upper_cmd]
        cat2 = async_local["cat"]

        proc = await (cat | upper | cat2).popen()
        stdout, _stderr = await proc.communicate(b"hello\n")
        assert stdout == b"HELLO\n"
        assert proc.returncode == 0

    @pytest.mark.asyncio
    async def test_three_stage_pipeline_readline(self):
        cat = async_local["cat"]
        upper = async_local[sys.executable]["-c", upper_cmd]
        cat2 = async_local["cat"]

        proc = await (cat | upper | cat2).popen()
        assert proc.stdin is not None
        proc.stdin.write(b"hello\nworld\n")
        await proc.stdin.drain()
        proc.stdin.close()

        lines = []
        while i := await proc.stdout.readline():
            lines.append(i.decode().strip())

        assert lines == ["HELLO", "WORLD"]
        await proc.wait()
        assert proc.returncode == 0


class TestAsyncPipelineReturnCodes:
    """Test error handling and return codes in async pipelines."""

    @pytest.mark.asyncio
    async def test_async_pipeline_with_failing_stage(self):
        echo = async_local[sys.executable]["-c", echo_cmd]
        fail = async_local[sys.executable]["-c", "import sys; sys.exit(1)"]

        proc = await (echo | fail).popen()
        # Wait should return the failing exit code
        returncode = await proc.wait()
        assert returncode == 1

    @pytest.mark.asyncio
    async def test_async_pipeline_first_stage_fails(self):
        fail = async_local[sys.executable]["-c", "import sys; sys.exit(2)"]
        cat = async_local["cat"]

        proc = await (fail | cat).popen()
        returncode = await proc.wait()
        assert returncode == 2

    @pytest.mark.asyncio
    async def test_async_pipeline_middle_stage_fails(self):
        cat = async_local["cat"]
        fail = async_local[sys.executable]["-c", "import sys; sys.exit(3)"]

        proc = await (cat | fail | cat).popen()
        # Close stdin so the first cat gets EOF and terminates
        proc.stdin.close()
        returncode = await proc.wait()
        assert returncode == 3


class TestAsyncPipelineProcessProperties:
    """Test AsyncPipelineProcess properties."""

    @pytest.mark.asyncio
    async def test_async_pipeline_process_pid(self):
        echo = async_local[sys.executable]["-c", echo_cmd]
        cat = async_local["cat"]

        proc = await (echo | cat).popen()
        assert proc.pid > 0
        await proc.wait()

    @pytest.mark.asyncio
    async def test_async_pipeline_process_stdin_stdout_stderr(self):
        echo = async_local[sys.executable]["-c", echo_cmd]
        cat = async_local["cat"]

        proc = await (echo | cat).popen()
        assert proc.stdin is not None
        assert proc.stdout is not None
        assert proc.stderr is not None
        await proc.wait()


class TestAsyncPipelineKilling:
    """Test signal handling in async pipelines."""

    @pytest.mark.asyncio
    async def test_async_pipeline_terminate(self):
        sleep = async_local[sys.executable]["-c", "import time; time.sleep(60)"]
        cat = async_local["cat"]

        proc = await (sleep | cat).popen()
        proc.terminate()
        # Give it time to terminate
        await asyncio.sleep(0.1)
        assert proc._procs[0].returncode is not None

    @pytest.mark.asyncio
    async def test_async_pipeline_kill(self):
        sleep = async_local[sys.executable]["-c", "import time; time.sleep(60)"]
        cat = async_local["cat"]

        proc = await (sleep | cat).popen()
        proc.kill()
        # Give it time to die
        await asyncio.sleep(0.1)
        assert proc._procs[0].returncode is not None

    @pytest.mark.asyncio
    async def test_async_pipeline_send_signal(self):
        sleep = async_local[sys.executable]["-c", "import time; time.sleep(60)"]
        cat = async_local["cat"]

        import signal

        proc = await (sleep | cat).popen()
        proc.send_signal(signal.SIGTERM)
        await asyncio.sleep(0.1)
        assert proc._procs[0].returncode is not None


class TestAsyncPipelineSyncEquivalence:
    """Verify async pipeline matches sync behavior."""

    def test_sync_pipeline(self):
        echo = local[sys.executable]["-c", echo_cmd]
        upper = local[sys.executable]["-c", upper_cmd]

        command = echo | upper

        proc = command.popen()
        assert proc.stdout is not None
        lines = []
        while i := proc.stdout.readline():
            lines.append(i.decode().strip())

        assert len(lines) == 2
        assert lines == ["TEST PIPE1", "TEST PIPE2"]
        # Ensure child processes are reaped and return code is checked
        proc.wait()
        assert proc.returncode == 0

    @pytest.mark.asyncio
    async def test_async_pipeline_equiv_to_sync(self):
        echo = async_local[sys.executable]["-c", echo_cmd]
        upper = async_local[sys.executable]["-c", upper_cmd]

        proc = await (echo | upper).popen()
        lines = []
        while i := await proc.stdout.readline():
            lines.append(i.decode().strip())

        assert len(lines) == 2
        assert lines == ["TEST PIPE1", "TEST PIPE2"]
        await proc.wait()
        assert proc.returncode == 0


class TestAsyncPipelineFormulate:
    """Test pipeline formulation."""

    def test_async_pipeline_formulate(self):
        echo = async_local[sys.executable]["-c", echo_cmd]
        upper = async_local[sys.executable]["-c", upper_cmd]

        pipeline = echo | upper
        formulated = pipeline.formulate()
        assert sys.executable in formulated[0]
        assert "|" in formulated

    def test_async_pipeline_formulate_with_args(self):
        cat = async_local["cat"]
        upper = async_local[sys.executable]["-c", upper_cmd]

        pipeline = (cat | upper).bound_command("extra_arg")
        formulated = pipeline.formulate()
        assert "extra_arg" in formulated


class TestAsyncPipelineOrChaining:
    """Test __or__ chaining with async pipelines."""

    @pytest.mark.asyncio
    async def test_async_pipeline_or_chaining(self):
        cat = async_local["cat"]
        upper = async_local[sys.executable]["-c", upper_cmd]
        cat2 = async_local["cat"]

        # Test that __or__ on a pipeline returns another pipeline
        pipeline = cat | upper | cat2
        proc = await pipeline.popen()
        stdout, _stderr = await proc.communicate(b"hello\n")
        assert stdout == b"HELLO\n"
        assert proc.returncode == 0

    def test_async_pipeline_or_returns_pipeline(self):
        cat = async_local["cat"]
        upper = async_local[sys.executable]["-c", upper_cmd]

        result = cat | upper
        from plumbum.commands.async_ import AsyncPipeline

        assert isinstance(result, AsyncPipeline)

    def test_async_pipeline_nested_or(self):
        cat = async_local["cat"]
        upper = async_local[sys.executable]["-c", upper_cmd]
        cat2 = async_local["cat"]

        result = (cat | upper) | cat2
        from plumbum.commands.async_ import AsyncPipeline

        assert isinstance(result, AsyncPipeline)
