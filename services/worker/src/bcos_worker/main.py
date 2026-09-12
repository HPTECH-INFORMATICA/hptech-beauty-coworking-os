"""Executable BCOS worker entry point."""

from __future__ import annotations

import asyncio
import sys

from bcos_worker.runtime import run_worker
from bcos_worker.session import get_session_factory
from bcos_worker.usage_completed_handler import handle_usage_completed


async def _run() -> None:
    session_factory = get_session_factory()

    await run_worker(
        session_factory=session_factory,
        usage_completed_handler=handle_usage_completed,
    )


def main() -> int:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())