"""Get per-cell factor contributions from model.service.score_cells, or a fallback.

The model owner (B) exposes score_cells(as_of, rain_in, high_tide). Its exact return
type is not frozen in contracts, so this adapter accepts a pandas DataFrame or a list
of dicts/objects with `cell_id` and per-feature contributions given either as a
`contributions` mapping or as columns named `contrib_<feature>` / `<feature>_contribution`.
If the model is missing or fails, a history-only scorer is used (no future data).
"""
import logging
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Iterable, Optional

from backend.config import weights
from contracts.schemas import CauseLabel, FactorContribution, Report

log = logging.getLogger(__name__)

PLAIN_NAMES = {
    "past_fixable_count": "Past clogged-drain reports",
    "past_fixable_365d": "Clogged-drain reports in the last year",
    "past_total_reports": "All past reports",
    "days_since_last_fixable": "Days since the last clogged drain",
    "leaf_season": "Leaf season",
    "rain_in": "Forecast rain",
    "high_tide": "High tide",
    "intercept": "Baseline",
}
RAIN_FACTORS = {"Forecast rain", "Rain on clogged-drain history"}


@dataclass(frozen=True)
class CellScore:
    cell_id: str
    factors: tuple[FactorContribution, ...]


def plain_name(feature: str) -> str:
    """Plain-language label for a model feature name."""
    return PLAIN_NAMES.get(feature, feature.replace("_", " ").capitalize())


_RAIN_WORD = re.compile(r"\brain\b", re.IGNORECASE)  # "rain", but not "drain"


def is_rain_factor(f: FactorContribution) -> bool:
    """True for factors that depend on rain (dropped from the backlog score)."""
    return f.factor in RAIN_FACTORS or bool(_RAIN_WORD.search(f.factor))


def _rows(result: Any) -> Iterable[dict[str, Any]]:
    if hasattr(result, "to_dict"):
        return result.to_dict(orient="records")
    return [r if isinstance(r, dict) else vars(r) for r in result]


def _contributions(row: dict[str, Any]) -> list[tuple[str, float]]:
    c = row.get("contributions")
    if isinstance(c, dict):
        return [(k, float(v)) for k, v in c.items()]
    if isinstance(c, list):
        return [(x["factor"] if isinstance(x, dict) else x.factor,
                 float(x["contribution"] if isinstance(x, dict) else x.contribution)) for x in c]
    out = []
    for k, v in row.items():
        if k.startswith("contrib_"):
            out.append((k[len("contrib_"):], float(v)))
        elif k.endswith("_contribution"):
            out.append((k[: -len("_contribution")], float(v)))
    return out


def normalize_model_output(result: Any) -> dict[str, CellScore]:
    """Convert score_cells output into {cell_id: CellScore} with plain factor names."""
    scores: dict[str, CellScore] = {}
    for row in _rows(result):
        cid = str(row["cell_id"])
        factors = []
        for feat, contrib in sorted(_contributions(row)):
            if not math.isfinite(contrib):
                continue
            raw = row.get(feat, contrib)
            value = float(raw) if isinstance(raw, (int, float, bool)) and math.isfinite(float(raw)) else contrib
            factors.append(FactorContribution(factor=plain_name(feat), value=value, contribution=contrib))
        if factors:
            scores[cid] = CellScore(cid, tuple(factors))
    return scores


def fallback_scores(reports: list[Report], as_of: date, rain_in: float) -> dict[str, CellScore]:
    """History-only scorer. Uses ONLY reports opened strictly before as_of."""
    w = weights()["fallback_model"]
    cutoff = as_of
    year_ago = as_of - timedelta(days=365)
    leaf = as_of.month in (10, 11)
    counts: dict[str, list[int]] = {}
    for r in reports:
        day = r.opened_at.date() if isinstance(r.opened_at, datetime) else r.opened_at
        if day >= cutoff:
            continue
        c = counts.setdefault(r.cell_id, [0, 0, 0])  # clogged, other, clogged last 365 d
        if r.cause_label == CauseLabel.clogged_basin:
            c[0] += 1
            if day >= year_ago:
                c[2] += 1
        else:
            c[1] += 1
    out: dict[str, CellScore] = {}
    for cid, (clogged, other, recent) in counts.items():
        hist = math.log1p(clogged)
        factors = [
            FactorContribution(factor="Past clogged-drain reports", value=clogged, contribution=w["past_clogged"] * hist),
            FactorContribution(factor="Other past reports", value=other, contribution=w["past_other"] * math.log1p(other)),
            FactorContribution(factor="Clogged-drain reports in the last year", value=recent,
                               contribution=w["recent_clogged"] * math.log1p(recent)),
            FactorContribution(factor="Rain on clogged-drain history", value=rain_in,
                               contribution=w["rain_x_history"] * rain_in * hist),
            FactorContribution(factor="Leaf season", value=1.0 if leaf else 0.0,
                               contribution=w["leaf_season"] * hist if leaf else 0.0),
        ]
        out[cid] = CellScore(cid, tuple(factors))
    return out


def score(reports: list[Report], as_of: date, rain_in: float, high_tide: bool,
          use_model: bool = True) -> tuple[dict[str, CellScore], bool]:
    """Return ({cell_id: CellScore}, used_fallback_scorer)."""
    if use_model:
        try:
            from model.service import score_cells  # public API of module B
            scores = normalize_model_output(score_cells(as_of, rain_in, high_tide))
            if scores:
                return scores, False
            log.warning("model.service.score_cells returned no usable rows; using fallback scorer")
        except ImportError:
            log.info("model.service not available yet; using fallback scorer")
        except Exception as e:
            log.warning("model.service.score_cells failed (%s); using fallback scorer", e)
    return fallback_scores(reports, as_of, rain_in), True
