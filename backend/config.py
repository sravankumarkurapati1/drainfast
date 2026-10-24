"""Environment settings and weights for the backend. Read at call time, never cached globally."""
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from backend.paths import DEMO_DIR, FIXTURES_DIR

WEIGHTS_PATH = Path(__file__).resolve().parent / "weights.yaml"


def fallback_on() -> bool:
    """True when DRAINFAST_FALLBACK=1: no network calls and no Bedrock calls."""
    return os.environ.get("DRAINFAST_FALLBACK", "0").strip() == "1"


def demo_dir() -> Path:
    """Directory holding pipeline outputs. DRAINFAST_DEMO_DIR overrides it (tests only)."""
    override = os.environ.get("DRAINFAST_DEMO_DIR")
    return Path(override) if override else DEMO_DIR


def fixtures_dir() -> Path:
    """Directory holding the contract fixtures used when a demo file is missing."""
    return FIXTURES_DIR


def user_agent() -> str:
    """User-Agent for NWS and NOAA requests, built from DRAINFAST_CONTACT."""
    contact = os.environ.get("DRAINFAST_CONTACT", "team@example.edu")
    return f"DrainFast/1.0 ({contact})"


def frontend_origin() -> str:
    """Origin allowed by CORS."""
    return os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")


@lru_cache(maxsize=1)
def weights() -> dict[str, Any]:
    """Priority weights from backend/weights.yaml."""
    with WEIGHTS_PATH.open() as f:
        return yaml.safe_load(f)
