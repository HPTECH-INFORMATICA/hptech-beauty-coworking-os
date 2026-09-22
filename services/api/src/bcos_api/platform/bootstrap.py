"""Controlled bootstrap for the first BCOS HPTECH platform administrator."""

from __future__ import annotations

import argparse
import asyncio
import os

from sqlalchemy import text

from bcos_api.db.session import get_async_session


async def bootstrap(external_user_id: str) -> None:
    identity = external_user_id.strip()
    if not identity:
        raise SystemExit("external_user_id must not be blank")

    sessions = get_async_session()
    try:
        session = await anext(sessions)
        count = await session.scalar(text("SELECT count(*) FROM platform_operators"))
        if count != 0:
            raise SystemExit("Bootstrap refused: platform operator already exists.")

        await session.execute(
            text(
                """INSERT INTO platform_operators
                (external_user_id, role, status)
                VALUES (:external_user_id, 'PLATFORM_ADMIN', 'ACTIVE')"""
            ),
            {"external_user_id": identity},
        )
        await session.execute(
            text(
                """INSERT INTO platform_audit_logs
                (actor_external_user_id, action, entity_type, metadata)
                VALUES (
                    :external_user_id,
                    'PLATFORM_OPERATOR_BOOTSTRAPPED',
                    'platform_operator',
                    CAST(:metadata AS jsonb)
                )"""
            ),
            {
                "external_user_id": identity,
                "metadata": '{"role":"PLATFORM_ADMIN","status":"ACTIVE","bootstrap":true}',
            },
        )
        await session.commit()
    finally:
        await sessions.aclose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-user-id", required=True)
    parser.add_argument(
        "--confirmation",
        required=True,
        help="Must equal BOOTSTRAP_BCOS_PLATFORM_ADMIN",
    )
    args = parser.parse_args()
    if args.confirmation != "BOOTSTRAP_BCOS_PLATFORM_ADMIN":
        raise SystemExit("Explicit bootstrap confirmation is required.")
    if os.getenv("DATABASE_URL", "").strip() == "":
        raise SystemExit("DATABASE_URL is required.")
    asyncio.run(bootstrap(args.external_user_id))


if __name__ == "__main__":
    main()
