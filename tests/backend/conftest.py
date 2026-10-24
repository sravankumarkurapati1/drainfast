"""Backend tests run offline with DRAINFAST_FALLBACK=1 and no network access."""
import os
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ["DRAINFAST_FALLBACK"] = "1"


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_a: object, **_k: object) -> None:
        raise OSError("network disabled in tests")
    monkeypatch.setattr(socket.socket, "connect", refuse)


@pytest.fixture
def empty_demo_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the backend at an empty data/demo so it must fall back to fixtures."""
    monkeypatch.setenv("DRAINFAST_DEMO_DIR", str(tmp_path))
    return tmp_path
