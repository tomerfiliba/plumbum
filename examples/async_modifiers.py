#!/usr/bin/env python3
"""Async execution modifiers examples."""

import asyncio

from plumbum import async_local
from plumbum.commands.async_ import AsyncRETCODE, AsyncTEE, AsyncTF


async def example_async_tf() -> None:
    """AsyncTF - returns True/False based on exit code."""
    print("\n=== AsyncTF Examples ===\n")

    # Check if command succeeds
    success = await (async_local["true"] & AsyncTF)
    print(f"Command succeeded: {success}")

    # Check if command fails
    failed = await (async_local["false"] & AsyncTF)
    print(f"Command failed: {failed}")


async def example_async_retcode() -> None:
    """AsyncRETCODE - returns only the exit code."""
    print("\n=== AsyncRETCODE Examples ===\n")

    code = await (async_local["true"] & AsyncRETCODE)
    print(f"Success exit code: {code}")

    code = await (async_local["false"] & AsyncRETCODE)
    print(f"Failure exit code: {code}")


async def example_async_tee() -> None:
    """AsyncTEE - shows output in real-time and returns it."""
    print("\n=== AsyncTEE Examples ===\n")

    print("Running with TEE:")
    _retcode, stdout, _stderr = await (async_local["echo"]["hello"] & AsyncTEE)
    print(f"Captured: {stdout.strip()}")


async def main() -> None:
    print("Async Modifiers Examples")
    await example_async_tf()
    await example_async_retcode()
    await example_async_tee()
    print("\nAll examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
