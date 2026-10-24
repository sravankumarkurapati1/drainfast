"""Brief reasons read as plain language (product rule 5)."""
from backend.model_adapter import normalize_model_output
from backend.priority import reason_for
from contracts.schemas import FactorContribution


def test_days_since_last_clog_reads_as_recent_clog():
    scores = normalize_model_output([{"cell_id": "c_1_1", "days_since_last_fixable": 597.0,
                                      "days_since_last_fixable_contribution": 1.0,
                                      "past_total_reports": 19.0, "past_total_reports_contribution": 10.0}])
    reason = reason_for(list(scores["c_1_1"].factors))
    assert reason == ("Ranked high mainly because of all past reports (19) "
                      "and a recent clogged drain (597 days ago).")


def test_flags_have_no_number_and_acronyms_keep_case():
    factors = [FactorContribution(factor="Share of basins run by BWSC", value=1.0, contribution=0.5),
               FactorContribution(factor="Environmental justice area", value=1.0, contribution=0.3)]
    assert reason_for(factors) == ("Ranked high mainly because of share of basins run by BWSC "
                                   "and environmental justice area.")
