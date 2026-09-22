"""Tests for the guarded platform administrator bootstrap."""

import pytest

from bcos_api.platform.bootstrap import bootstrap


@pytest.mark.asyncio
async def test_bootstrap_rejects_blank_external_identity() -> None:
    with pytest.raises(SystemExit, match="must not be blank"):
        await bootstrap("   ")
