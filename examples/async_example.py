#!/usr/bin/env python3
"""Plumbum async support examples."""

import asyncio

from plumbum import async_local


async def main() -> None:
    print("Plumbum Async Examples\n")

    # Basic command
    result = await async_local["echo"]("Hello, async!")
    print(f"Basic: {result.strip()}")

    # Pipeline
    result = await (async_local["echo"]["hello"] | async_local["grep"]["hello"])()
    print(f"Pipeline: {result.strip()}")

    # Concurrent execution
    results = await asyncio.gather(
        async_local["echo"]("task1"),
        async_local["echo"]("task2"),
        async_local["echo"]("task3"),
    )
    print(f"Concurrent: {len(results)} tasks completed")

    # Error handling
    result = await async_local["false"].run(retcode=None)
    print(f"Error handling: exit code = {result.returncode}")

    print("\nAll examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
