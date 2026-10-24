"""Training examples (storm day x cell) and the logistic regression risk model."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from model.features import FEATURES, build_features

RANDOM_STATE = 42
LABEL_WINDOW_DAYS = 2  # a report belongs to storm S if opened on S or up to 2 days after


def window_end(storm_day: date) -> date:
    """Return the last day whose reports still count for the storm on storm_day."""
    return storm_day + timedelta(days=LABEL_WINDOW_DAYS)


def storm_reports(reports: pd.DataFrame, storm_day: date, fixable_only: bool = True) -> pd.DataFrame:
    """Return the reports opened on storm_day or within the label window after it."""
    start = pd.Timestamp(storm_day)
    end = pd.Timestamp(window_end(storm_day))
    mask = (reports["day"] >= start) & (reports["day"] <= end)
    if fixable_only:
        mask &= reports["fixable"]
    return reports[mask]


def trainable_storms(storms: pd.DataFrame, reports: pd.DataFrame, before: date | None = None) -> list[date]:
    """Storm days usable as training examples.

    A storm qualifies when its label window ends on or before the last report day
    (later storms would get false zero labels), and, when before is given, strictly
    before that day (so no training label uses reports from the held-out storm).
    """
    last_report_day = reports["day"].max().date()
    days = [d for d in storms.loc[storms["is_storm_day"], "storm_day"] if window_end(d) <= last_report_day]
    if before is not None:
        days = [d for d in days if window_end(d) < before]
    return sorted(days)


def build_training_set(storm_days: list[date], storms: pd.DataFrame, reports: pd.DataFrame,
                       cell_ids: list[str] | tuple[str, ...]) -> pd.DataFrame:
    """One row per (storm day, cell): storm_day, cell_id, FEATURES and label.

    label is 1 when the cell has at least one clogged_basin report for the storm.
    Features use only reports opened strictly before the storm day.
    """
    by_day = storms.set_index("storm_day")
    frames = []
    for day in storm_days:
        row = by_day.loc[day]
        feats = build_features(day, float(row["rain_total_in"]), bool(row["high_tide_flag"]),
                               reports=reports, cell_ids=cell_ids)
        positive = set(storm_reports(reports, day)["cell_id"])
        feats["label"] = feats["cell_id"].isin(positive).astype(int)
        feats.insert(0, "storm_day", day)
        frames.append(feats)
    if not frames:
        raise ValueError("no storm days to train on")
    return pd.concat(frames, ignore_index=True)


def fit_model(training: pd.DataFrame) -> dict:
    """Fit standardized logistic regression (class_weight balanced, random_state 42).

    Returns a bundle dict: pipeline, features, trained_storms and row counts.
    """
    if training["label"].nunique() < 2:
        raise ValueError("training data needs both positive and negative examples")
    pipeline = Pipeline([
        ("scale", StandardScaler()),
        ("logreg", LogisticRegression(class_weight="balanced", random_state=RANDOM_STATE, max_iter=1000)),
    ])
    pipeline.fit(training[list(FEATURES)].to_numpy(dtype=float), training["label"].to_numpy())
    storm_days = sorted(set(training["storm_day"]))
    return {
        "pipeline": pipeline,
        "features": FEATURES,
        "trained_storms": [d.isoformat() for d in storm_days],
        "trained_through": storm_days[-1].isoformat(),
        "label_window_days": LABEL_WINDOW_DAYS,
        "n_rows": int(len(training)),
        "n_positive": int(training["label"].sum()),
    }


def train(storm_days: list[date], storms: pd.DataFrame, reports: pd.DataFrame,
          cell_ids: list[str] | tuple[str, ...]) -> dict:
    """Build the training set for storm_days and fit the model bundle."""
    return fit_model(build_training_set(storm_days, storms, reports, cell_ids))
