"""Input and output paths for the model.

contracts/paths.py does not exist yet, so shared locations come from
data_pipeline.paths (an allowed dependency). Switch to contracts.paths when it lands.
"""
from pathlib import Path

from data_pipeline.paths import CELLS_PATH, DEMO_DIR, PROJECT_ROOT, RAW_DIR, REPORTS_PATH

RAIN_PATH: Path = RAW_DIR / "rain" / "logan_hourly_precip.csv"
TIDE_PATH: Path = RAW_DIR / "tide" / "boston_tide_hourly.csv"
FIXTURE_REPORTS_PATH: Path = PROJECT_ROOT / "contracts" / "fixtures" / "report.json"

STORMS_PATH: Path = DEMO_DIR / "storms.parquet"
TIDE_THRESHOLD_PATH: Path = DEMO_DIR / "tide_threshold.json"
RAIN_TREND_PATH: Path = DEMO_DIR / "rain_trend.json"
BACKTEST_PATH: Path = DEMO_DIR / "backtest.json"
MODEL_PATH: Path = DEMO_DIR / "model.joblib"

__all__ = [
    "PROJECT_ROOT", "RAW_DIR", "DEMO_DIR", "REPORTS_PATH", "CELLS_PATH", "RAIN_PATH",
    "TIDE_PATH", "FIXTURE_REPORTS_PATH", "STORMS_PATH", "TIDE_THRESHOLD_PATH",
    "RAIN_TREND_PATH", "BACKTEST_PATH", "MODEL_PATH",
]
