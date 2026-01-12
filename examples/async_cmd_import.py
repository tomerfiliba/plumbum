#!/usr/bin/env python3
"""Example demonstrating async_cmd import mechanism."""

import asyncio

from plumbum.async_cmd import echo, grep, ls


async def main() -> None:
    print("Async CMD Import Examples\n")

    # Direct import and usage
    result = await echo("Hello from async_cmd!")
    print(f"Echo: {result.strip()}")

    # With arguments
    result = await ls("-la")
    print(f"Files listed: {len(result.splitlines())} lines")

    # Pipeline
    result = await (echo["test line"] | grep["test"])()
    print(f"Pipeline: {result.strip()}")

    # Multiple commands
    results = await asyncio.gather(
        echo("task1"),
        echo("task2"),
        echo("task3"),
    )
    print(f"Concurrent: {len(results)} tasks completed")

    print("\nAll examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
