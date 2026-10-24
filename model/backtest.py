"""Backtest on past storms against random and "most past complaints" rankings."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from contracts.schemas import BacktestResult
from model.features import build_features
from model.service import score_cells
from model.train import RANDOM_STATE, storm_reports, train, trainable_storms, window_end

BACKTEST_SINCE = date(2023, 1, 1)
N_BACKTEST_STORMS = 3
N_RANDOM_RANKINGS = 200
TOP_N = (100, 200)


def choose_backtest_storms(storms: pd.DataFrame, reports: pd.DataFrame, n: int = N_BACKTEST_STORMS,
                           since: date = BACKTEST_SINCE) -> list[date]:
    """Pick the n storm days since `since` with the most clogged_basin reports.

    Only storms whose label window is fully covered by the report data count. Ties
    go to the earlier day. Returns the chosen days in date order.
    """
    last_report_day = reports["day"].max().date()
    candidates = [d for d in storms.loc[storms["is_storm_day"], "storm_day"]
                  if d >= since and window_end(d) <= last_report_day]
    counted = sorted(((len(storm_reports(reports, d)), d) for d in candidates), key=lambda t: (-t[0], t[1]))
    return sorted(d for _, d in counted[:n])


def hit_rate(ranked_cells: list[str] | np.ndarray, report_cells: list[str], top_n: int) -> float:
    """Share of the storm's fixable reports whose cell is in the first top_n ranked cells."""
    if not report_cells:
        return 0.0
    top = set(list(ranked_cells)[:top_n])
    return sum(c in top for c in report_cells) / len(report_cells)


def random_hit_rates(cell_ids: list[str], report_cells: list[str], top_ns: tuple[int, ...] = TOP_N,
                     n_rankings: int = N_RANDOM_RANKINGS, seed: int = RANDOM_STATE) -> dict[int, float]:
    """Average hit rate over n_rankings seeded random orderings of the cells."""
    rng = np.random.default_rng(seed)
    cells = np.array(sorted(cell_ids))
    totals = {n: 0.0 for n in top_ns}
    for _ in range(n_rankings):
        order = cells[rng.permutation(len(cells))]
        for n in top_ns:
            totals[n] += hit_rate(order, report_cells, n)
    return {n: totals[n] / n_rankings for n in top_ns}


def most_complaints_ranking(storm_day: date, reports: pd.DataFrame, cell_ids: list[str]) -> list[str]:
    """Rank cells by past_total_reports before storm_day (highest first), then cell_id."""
    feats = build_features(storm_day, 0.0, False, reports=reports, cell_ids=cell_ids)
    order = np.lexsort((feats["cell_id"].to_numpy(), -feats["past_total_reports"].to_numpy()))
    return feats["cell_id"].to_numpy()[order].tolist()


def backtest_storm(storm_day: date, storms: pd.DataFrame, reports: pd.DataFrame,
                   cell_ids: list[str]) -> tuple[BacktestResult, dict]:
    """Retrain on earlier storms only, rank cells for storm_day and score all three methods.

    Returns the BacktestResult and a dict of training details for the printed table.
    """
    train_days = trainable_storms(storms, reports, before=storm_day)
    bundle = train(train_days, storms, reports, cell_ids)
    row = storms.set_index("storm_day").loc[storm_day]
    ranked = score_cells(storm_day, float(row["rain_total_in"]), bool(row["high_tide_flag"]),
                         bundle=bundle, reports=reports, cell_ids=cell_ids)["cell_id"].tolist()
    report_cells = storm_reports(reports, storm_day)["cell_id"].tolist()
    complaints = most_complaints_ranking(storm_day, reports, cell_ids)
    rand = random_hit_rates(list(cell_ids), report_cells)
    result = BacktestResult(
        storm_day=storm_day,
        n_fixable_reports=len(report_cells),
        n_cells=len(cell_ids),
        hit_rate_top100=hit_rate(ranked, report_cells, 100),
        hit_rate_top200=hit_rate(ranked, report_cells, 200),
        random_top100=rand[100],
        random_top200=rand[200],
        most_complaints_top100=hit_rate(complaints, report_cells, 100),
        most_complaints_top200=hit_rate(complaints, report_cells, 200),
    )
    details = {
        "rain_in": float(row["rain_total_in"]),
        "high_tide": bool(row["high_tide_flag"]),
        "n_train_storms": len(train_days),
        "n_train_positive": bundle["n_positive"],
    }
    return result, details


def format_table(rows: list[tuple[BacktestResult, dict]]) -> str:
    """Render backtest results as a plain-text table with sample sizes."""
    head = (f"{'storm day':10}  {'rain':>5}  {'tide':4}  {'fixable':>7}  {'cells':>5}  {'train':>5}  "
            f"{'model@100':>9}  {'model@200':>9}  {'random@100':>10}  {'random@200':>10}  "
            f"{'complaints@100':>14}  {'complaints@200':>14}")
    lines = [head, "-" * len(head)]
    for r, d in rows:
        lines.append(
            f"{r.storm_day.isoformat():10}  {d['rain_in']:5.2f}  {'yes' if d['high_tide'] else 'no':4}  "
            f"{r.n_fixable_reports:7d}  {r.n_cells:5d}  {d['n_train_storms']:5d}  "
            f"{r.hit_rate_top100:9.1%}  {r.hit_rate_top200:9.1%}  {r.random_top100:10.1%}  "
            f"{r.random_top200:10.1%}  {r.most_complaints_top100:14.1%}  {r.most_complaints_top200:14.1%}"
        )
    if rows:
        total = sum(r.n_fixable_reports for r, _ in rows)

        def pooled(attr: str) -> float:
            return sum(getattr(r, attr) * r.n_fixable_reports for r, _ in rows) / total if total else 0.0

        lines.append("-" * len(head))
        lines.append(
            f"{'pooled':10}  {'':5}  {'':4}  {total:7d}  {'':5}  {'':5}  "
            f"{pooled('hit_rate_top100'):9.1%}  {pooled('hit_rate_top200'):9.1%}  "
            f"{pooled('random_top100'):10.1%}  {pooled('random_top200'):10.1%}  "
            f"{pooled('most_complaints_top100'):14.1%}  {pooled('most_complaints_top200'):14.1%}"
        )
    return "\n".join(lines)
