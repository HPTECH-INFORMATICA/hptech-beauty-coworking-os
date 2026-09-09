"""Database runtime configuration for the BCOS worker."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseSettings:
    """Runtime configuration for the BCOS PostgreSQL database."""

    url: str

    @classmethod
    def from_env(cls) -> "DatabaseSettings":
        database_url = os.getenv("DATABASE_URL")

        if database_url is None or not database_url.strip():
            raise RuntimeError(
                "DATABASE_URL is required to connect to the BCOS database."
            )

        return cls(url=database_url.strip())
