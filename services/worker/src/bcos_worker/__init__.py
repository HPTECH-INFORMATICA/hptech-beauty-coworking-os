"""HPTECH Beauty Coworking OS worker package."""

# BCOS_LOCAL_ENV
from pathlib import Path

from dotenv import load_dotenv

_BCOS_LOCAL_ENV = Path(__file__).resolve().parents[4] / ".env.local"

load_dotenv(
    dotenv_path=_BCOS_LOCAL_ENV,
    override=False,
)
