"""Public model interface: score_cells(as_of, rain_in, high_tide)."""
from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from model import paths
from model.features import FEATURES, build_features

BASE_RATE = "base_rate"


@lru_cache(maxsize=1)
def load_model(model_path: Path = paths.MODEL_PATH) -> dict:
    """Load the saved model bundle (written by `python -m model.run`)."""
    if not model_path.exists():
        raise FileNotFoundError(f"{model_path} missing; run `make model` first")
    return joblib.load(model_path)


def contributions(bundle: dict, features: pd.DataFrame) -> pd.DataFrame:
    """Split each cell's log-odds into named parts.

    Each feature contributes coefficient x standardized value. The intercept is
    returned as base_rate, so risk_score equals base_rate plus the feature
    contributions exactly. Output: one <feature>_contribution column per feature,
    base_rate and risk_score, aligned with features.
    """
    names = list(bundle["features"])
    scaler = bundle["pipeline"].named_steps["scale"]
    logreg = bundle["pipeline"].named_steps["logreg"]
    z = scaler.transform(features[names].to_numpy(dtype=float))
    parts = z * logreg.coef_[0]
    out = pd.DataFrame(parts, columns=[f"{n}_contribution" for n in names], index=features.index)
    out[BASE_RATE] = float(logreg.intercept_[0])
    out["risk_score"] = out[BASE_RATE] + parts.sum(axis=1)
    return out


def rank(scored: pd.DataFrame) -> pd.DataFrame:
    """Sort by risk_score (highest first), then cell_id, so ties are deterministic."""
    order = np.lexsort((scored["cell_id"].to_numpy(), -scored["risk_score"].to_numpy()))
    return scored.iloc[order].reset_index(drop=True)


def score_cells(
    as_of: date | datetime,
    rain_in: float,
    high_tide: bool,
    *,
    bundle: dict | None = None,
    reports: pd.DataFrame | None = None,
    cell_ids: list[str] | tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Score every cell for a storm on as_of.

    Inputs: as_of date, forecast or observed rain_in (inches), high_tide flag, and
    optionally a model bundle, prepared reports and cell ids (default: data/demo).
    Output: one row per cell with cell_id, risk_score (log-odds), base_rate, each
    feature value and its <feature>_contribution, sorted by risk_score then cell_id.
    """
    bundle = load_model() if bundle is None else bundle
    feats = build_features(as_of, rain_in, high_tide, reports=reports, cell_ids=cell_ids)
    parts = contributions(bundle, feats)
    columns = ["cell_id", "risk_score", BASE_RATE]
    for name in FEATURES:
        columns += [name, f"{name}_contribution"]
    return rank(pd.concat([feats, parts], axis=1)[columns])
