#!/usr/bin/env python3
"""Async remote command execution examples."""

import asyncio

from plumbum.commands.async_ import AsyncTF
from plumbum.machines.ssh_machine import AsyncSshMachine


async def example_basic_remote() -> None:
    """Basic remote command."""
    print("\n=== Basic Remote Command ===\n")

    async with AsyncSshMachine("localhost") as rem:
        result = await rem["echo"]("Hello from remote!")
        print(f"Output: {result.strip()}")


async def example_remote_pipeline() -> None:
    """Remote pipeline."""
    print("\n=== Remote Pipeline ===\n")

    async with AsyncSshMachine("localhost") as rem:
        result = await (rem["echo"]["test"] | rem["grep"]["test"])()
        print(f"Result: {result.strip()}")


async def example_concurrent_remote() -> None:
    """Concurrent remote commands."""
    print("\n=== Concurrent Remote Commands ===\n")

    async with AsyncSshMachine("localhost") as rem:
        results = await asyncio.gather(
            rem["echo"]("task1"),
            rem["echo"]("task2"),
            rem["echo"]("task3"),
        )
        print(f"Completed {len(results)} tasks")


async def example_remote_modifiers() -> None:
    """Remote modifiers."""
    print("\n=== Remote Modifiers ===\n")

    async with AsyncSshMachine("localhost") as rem:
        exists = await (rem["test"]["-f", "/etc/hosts"] & AsyncTF)
        print(f"/etc/hosts exists: {exists}")


async def example_multiple_hosts() -> None:
    """Multiple hosts concurrently."""
    print("\n=== Multiple Hosts ===\n")

    async def get_hostname(host: str) -> str:
        async with AsyncSshMachine(host) as rem:
            result: str = await rem["hostname"]()
            return result

    results = await asyncio.gather(
        get_hostname("localhost"),
        get_hostname("localhost"),
    )
    print(f"Connected to {len(results)} hosts")


async def main() -> None:
    print("Async Remote Examples")
    print("Note: Using localhost. Configure SSH if needed.\n")

    try:
        await example_basic_remote()
        await example_remote_pipeline()
        await example_concurrent_remote()
        await example_remote_modifiers()
        await example_multiple_hosts()
        print("\nAll examples completed!")
    except Exception as e:
        print(f"\nError: {e}")
        print("Configure SSH: ssh-keygen && ssh-copy-id localhost")


if __name__ == "__main__":
    asyncio.run(main())
