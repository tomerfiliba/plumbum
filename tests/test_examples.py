"""Tests that verify example files execute successfully.

This ensures examples stay up-to-date and functional.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


class TestExamples:
    """Tests for example files."""

    def test_async_example_runs(self):
        """Test that async_example.py runs without errors."""
        example_file = EXAMPLES_DIR / "async_example.py"
        if not example_file.exists():
            pytest.skip(f"Example file not found: {example_file}")

        result = subprocess.run(
            [sys.executable, str(example_file)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Example failed with stderr: {result.stderr}"
        assert "Async Examples" in result.stdout

    def test_async_modifiers_example_runs(self):
        """Test that async_modifiers.py runs without errors."""
        example_file = EXAMPLES_DIR / "async_modifiers.py"
        if not example_file.exists():
            pytest.skip(f"Example file not found: {example_file}")

        result = subprocess.run(
            [sys.executable, str(example_file)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Example failed with stderr: {result.stderr}"
        assert "AsyncTF Examples" in result.stdout
        assert "AsyncRETCODE Examples" in result.stdout
        assert "AsyncTEE Examples" in result.stdout

    def test_async_hybrid_example_runs(self):
        """Test that async_hybrid.py runs without errors."""
        example_file = EXAMPLES_DIR / "async_hybrid.py"
        if not example_file.exists():
            pytest.skip(f"Example file not found: {example_file}")

        result = subprocess.run(
            [sys.executable, str(example_file)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Example failed with stderr: {result.stderr}"
        assert "BG (Sync) vs Async Execution" in result.stdout
        assert "Concurrent Execution" in result.stdout
        assert "Mixing Sync and Async" in result.stdout

    @pytest.mark.ssh
    def test_async_remote_example_runs(self):
        """Test that async_remote.py runs without errors.

        This test is marked with 'ssh' and will be skipped if SSH is not configured.
        """
        example_file = EXAMPLES_DIR / "async_remote.py"
        if not example_file.exists():
            pytest.skip(f"Example file not found: {example_file}")

        result = subprocess.run(
            [sys.executable, str(example_file)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # The example might fail if SSH is not configured, which is OK
        # We just check that it doesn't crash with a Python error
        if result.returncode != 0:
            # Check if it's an SSH error (expected) vs a Python error (not expected)
            if "Error:" in result.stdout and "SSH" in result.stdout:
                pytest.skip("SSH not configured for localhost")
            else:
                pytest.fail(f"Example failed with unexpected error: {result.stderr}")

        assert "Async Remote Examples" in result.stdout


class TestExampleContent:
    """Tests that verify example content is correct."""

    def test_async_modifiers_demonstrates_all_modifiers(self):
        """Test that async_modifiers.py demonstrates all three modifiers."""
        example_file = EXAMPLES_DIR / "async_modifiers.py"
        if not example_file.exists():
            pytest.skip(f"Example file not found: {example_file}")

        content = example_file.read_text()

        # Check that all modifiers are imported and used
        assert "AsyncTF" in content
        assert "AsyncRETCODE" in content
        assert "AsyncTEE" in content

        # Check that examples exist for each
        assert "example_async_tf" in content
        assert "example_async_retcode" in content
        assert "example_async_tee" in content

    def test_async_hybrid_demonstrates_bg_vs_async(self):
        """Test that async_hybrid.py demonstrates BG vs async."""
        example_file = EXAMPLES_DIR / "async_hybrid.py"
        if not example_file.exists():
            pytest.skip(f"Example file not found: {example_file}")

        content = example_file.read_text()

        # Check that BG modifier is imported and used
        assert "from plumbum.commands.modifiers import BG" in content
        assert "& BG" in content

        # Check that async is used
        assert "async_local" in content
        assert "await" in content

        # Check that key examples exist
        assert "example_bg_vs_async" in content
        assert "example_bg_with_async" in content

    def test_async_remote_demonstrates_ssh(self):
        """Test that async_remote.py demonstrates SSH usage."""
        example_file = EXAMPLES_DIR / "async_remote.py"
        if not example_file.exists():
            pytest.skip(f"Example file not found: {example_file}")

        content = example_file.read_text()

        # Check that AsyncSshMachine is imported and used
        assert "AsyncSshMachine" in content
        assert "async with AsyncSshMachine" in content
        assert "from plumbum.machines.ssh_machine import AsyncSshMachine" in content

        # Check that key examples exist
        assert "example_basic_remote" in content
        assert "example_remote_pipeline" in content
        assert "example_concurrent_remote" in content
