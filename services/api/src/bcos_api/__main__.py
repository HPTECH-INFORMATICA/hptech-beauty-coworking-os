"""Executable entrypoint for the BCOS API."""

from __future__ import annotations

import asyncio
import selectors
import sys

import uvicorn


def _windows_selector_loop() -> asyncio.AbstractEventLoop:
    """Create the Windows-compatible event loop required by psycopg async."""

    return asyncio.SelectorEventLoop(
        selectors.SelectSelector()
    )


async def _serve() -> None:
    """Run the BCOS ASGI application."""

    config = uvicorn.Config(
        "bcos_api.main:app",
        host="127.0.0.1",
        port=8010,
        log_level="info",
        access_log=True,
        loop="none",
    )

    server = uvicorn.Server(config)

    await server.serve()


def main() -> int:
    """Run the API using a psycopg-compatible loop on Windows."""

    if sys.platform == "win32":
        with asyncio.Runner(
            loop_factory=_windows_selector_loop
        ) as runner:
            runner.run(_serve())

        return 0

    asyncio.run(_serve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())