"""Data paths for the backend.

contracts/paths.py does not exist on main yet (same as data_pipeline/paths.py). When it
lands, switch these to imports from contracts.paths so no module hard-codes a data path.
"""
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
RAW_DIR: Path = PROJECT_ROOT / "data" / "raw"
DEMO_DIR: Path = PROJECT_ROOT / "data" / "demo"
# Backend-owned fallback data in contract shapes, used when a data/demo file is missing.
# Switch to contracts/fixtures once those are committed.
FIXTURES_DIR: Path = Path(__file__).resolve().parent / "fixtures"
