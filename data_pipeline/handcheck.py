"""The 50-ticket hand check: sample notes for a human to label, then score the labels."""
from __future__ import annotations

import pandas as pd

from data_pipeline.labeler import LABELS

HAND_CHECK_SIZE = 50
SEED = 42
HAND_CHECK_COLUMNS: tuple[str, ...] = (
    "ticket_id", "text", "closing_note", "cause_label", "label_source", "human_label",
)


def sample_hand_check(reports: pd.DataFrame, n: int = HAND_CHECK_SIZE, seed: int = SEED) -> pd.DataFrame:
    """Pick n non-blank, non-excluded labeled rows (seeded) with an empty human_label."""
    pool = reports.loc[~reports["note_blank"] & ~reports["exclude"]]
    pool = pool.sort_values("ticket_id", kind="stable")
    sample = pool.sample(n=min(n, len(pool)), random_state=seed).sort_values("ticket_id")
    out = sample.loc[:, ["ticket_id", "text", "closing_note", "cause_label", "label_source"]].copy()
    out["human_label"] = ""
    return out.reset_index(drop=True)


def has_human_labels(df: pd.DataFrame) -> bool:
    """True when any row of an existing hand-check file has a human_label filled in."""
    if "human_label" not in df.columns:
        return False
    return bool(df["human_label"].fillna("").astype(str).str.strip().ne("").any())


def score_hand_check(df: pd.DataFrame) -> dict[str, object]:
    """Accuracy of cause_label against human_label, overall and by label_source, with n."""
    human = df["human_label"].fillna("").astype(str).str.strip().str.lower()
    filled = df.loc[human.ne("")].assign(human_label=human[human.ne("")])
    if filled.empty:
        raise ValueError("hand_check.csv has no human_label values filled in yet")
    bad = sorted(set(filled["human_label"]) - set(LABELS))
    if bad:
        raise ValueError(f"human_label must be one of {list(LABELS)}; found {bad}")

    def _acc(part: pd.DataFrame) -> dict[str, object]:
        n = int(len(part))
        correct = int((part["cause_label"] == part["human_label"]).sum())
        return {"n": n, "correct": correct, "accuracy": round(correct / n, 4) if n else None}

    by_label = {lab: _acc(filled.loc[filled["human_label"] == lab]) for lab in LABELS}
    return {
        "overall": _acc(filled),
        "by_label_source": {
            src: _acc(part) for src, part in sorted(filled.groupby("label_source"), key=lambda x: x[0])
        },
        "by_human_label": {k: v for k, v in by_label.items() if v["n"]},
        "n_rows_in_file": int(len(df)),
        "n_unfilled": int(len(df) - len(filled)),
    }
