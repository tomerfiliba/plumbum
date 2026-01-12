#!/usr/bin/env python3
"""Hybrid sync/async usage examples."""

import asyncio

from plumbum import async_local, local
from plumbum.commands.modifiers import BG


async def example_bg_vs_async() -> None:
    """BG (sync) vs async execution."""
    print("\n=== BG (Sync) vs Async Execution ===\n")

    # Sync BG: for sync code
    print("Sync BG:")
    future = local["echo"]["sync"] & BG
    future.wait()
    stdout_data = future.stdout
    result_str = stdout_data.decode() if isinstance(stdout_data, bytes) else stdout_data
    print(f"  Result: {result_str.strip()}")

    # Async: for async code
    print("\nAsync:")
    result = await async_local["echo"]("async")
    print(f"  Result: {result.strip()}")


async def example_concurrent_execution() -> None:
    """Concurrent execution comparison."""
    print("\n=== Concurrent Execution ===\n")

    # Sync BG
    futures = [local["echo"][f"task{i}"] & BG for i in range(3)]
    for f in futures:
        f.wait()
    print(f"Sync BG: {len(futures)} processes")

    # Async gather
    results = await asyncio.gather(
        async_local["echo"]("task1"),
        async_local["echo"]("task2"),
        async_local["echo"]("task3"),
    )
    print(f"Async: {len(results)} tasks")


async def example_mixing_in_same_workflow() -> None:
    """Mixing sync and async."""
    print("\n=== Mixing Sync and Async ===\n")

    # Sync for setup
    local["mkdir"]["-p", "/tmp/hybrid_test"]()
    print("Setup: sync")

    # Async for concurrent I/O
    await asyncio.gather(
        async_local["touch"]("/tmp/hybrid_test/file1"),
        async_local["touch"]("/tmp/hybrid_test/file2"),
    )
    print("Processing: async")

    # Sync for cleanup
    local["rm"]["-rf", "/tmp/hybrid_test"]()
    print("Cleanup: sync")


async def example_bg_with_async() -> None:
    """Combining BG and async."""
    print("\n=== Combining BG and Async ===\n")

    # Start background process
    daemon = local["sh"]["-c", "sleep 1; echo done"] & BG

    # Run async tasks meanwhile
    await async_local["echo"]("async task")

    # Wait for background process
    daemon.wait()
    print("Both completed")


async def main() -> None:
    print("Hybrid Sync/Async Examples")
    await example_bg_vs_async()
    await example_concurrent_execution()
    await example_mixing_in_same_workflow()
    await example_bg_with_async()
    print("\nKey: Use BG in sync code, async in async code")


if __name__ == "__main__":
    asyncio.run(main())
