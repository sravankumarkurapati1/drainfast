"""Input and output paths for the data pipeline.

contracts/paths.py does not exist yet. When it lands, switch these to imports from
contracts.paths so no module hard-codes a data path.
"""
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
RAW_DIR: Path = PROJECT_ROOT / "data" / "raw"
DEMO_DIR: Path = PROJECT_ROOT / "data" / "demo"

RAW_311_PATH: Path = RAW_DIR / "311" / "boston_311_catchbasin_flooding.csv"
RAW_BASINS_PATH: Path = RAW_DIR / "basins" / "boston_catch_basins.csv"
RAW_EJ_PATH: Path = RAW_DIR / "ej" / "ej_block_groups_boston.geojson"
RAW_FLOOD_PATH: Path = RAW_DIR / "flood" / "stormwater_flood_extent_near_9in.json"

REPORTS_PATH: Path = DEMO_DIR / "reports.parquet"
CELLS_PATH: Path = DEMO_DIR / "cells.parquet"
FLOOD_AREA_GEOJSON_PATH: Path = DEMO_DIR / "flood_area.geojson"
HAND_CHECK_PATH: Path = DEMO_DIR / "hand_check.csv"
LABEL_ACCURACY_PATH: Path = DEMO_DIR / "label_accuracy.json"
LLM_CACHE_PATH: Path = DEMO_DIR / "llm_cache.json"
