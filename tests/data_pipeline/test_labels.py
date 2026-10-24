"""Spec 01-ingest-and-labels: crew-note cleaning and cause labels."""
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from data_pipeline.labeler import LABELS, label_note, label_report, load_rules, rule_label
from data_pipeline.llm import BedrockLabeler, make_labeler, parse_answer
from data_pipeline.notes import is_excluded, split_closure

NOTE_WORDS = st.sampled_from([
    "cleaned", "cb", "takes water", "taking water", "debris", "leaves", "private", "pwd",
    "high tide", "tidal", "no flooding", "jet", "vactor", "grading", "low spot", "removed",
    "test", "invalid", "duplicate", "unclear", "clear on arrival", "&amp;", "CB'S", "1/9",
])
NOTES = st.one_of(st.text(max_size=200), st.lists(NOTE_WORDS, max_size=8).map(" ".join))


class FakeLLM:
    """Records every note it is asked about and returns a fixed answer."""

    def __init__(self, answer: object = "clogged_basin") -> None:
        self.answer = answer
        self.seen: list[str] = []

    def label(self, note: str) -> object:
        self.seen.append(note)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


# Feature: 01-ingest-and-labels, Property 1: every label is one of the four values
@settings(max_examples=300)
@given(note=NOTES, exclude=st.booleans(), answer=st.one_of(st.sampled_from(LABELS), st.text(max_size=20)))
def test_label_is_always_valid(note: str, exclude: bool, answer: str) -> None:
    label, source = label_note(note, exclude, FakeLLM(answer))
    assert label in LABELS
    assert source in ("rule", "llm")
    assert label_report(note) in LABELS


# Feature: 01-ingest-and-labels, Property 2: the same note always gets the same label
@settings(max_examples=300)
@given(note=NOTES, exclude=st.booleans())
def test_same_note_same_label(note: str, exclude: bool) -> None:
    assert label_note(note, exclude) == label_note(note, exclude)
    assert label_note(note.upper(), exclude) == label_note(note, exclude)


# Feature: 01-ingest-and-labels, Property 4: the AI is asked only about undecided notes,
# and anything but a valid label becomes unclear from the rules
@settings(max_examples=300)
@given(note=NOTES, exclude=st.booleans(),
       answer=st.one_of(st.sampled_from(LABELS), st.text(max_size=20), st.just(RuntimeError("boom"))))
def test_llm_only_for_undecided_notes(note: str, exclude: bool, answer: object) -> None:
    llm = FakeLLM(answer)
    label, source = label_note(note, exclude, llm)
    undecided = bool(note.strip()) and not exclude and rule_label(note) is None
    assert bool(llm.seen) == undecided
    if source == "llm":
        assert undecided and label == answer and answer in LABELS
    elif undecided or exclude or not note.strip():
        assert label == "unclear"  # blank, excluded, or the LLM gave no valid answer
    else:
        assert label == rule_label(note)  # decided by the rules, never by the LLM


def test_negative_rules_come_first() -> None:
    assert [r.label for r in load_rules()] == ["unclear", "grading_capacity", "coastal_tide", "clogged_basin"]
    assert label_note("Cleaned CB, cb taking water", False)[0] == "unclear"
    assert label_note("cleaned private cb not bwsc", False)[0] == "grading_capacity"
    assert label_note("relieved flood due to high tide", False)[0] == "coastal_tide"
    assert label_note("CLEANED AND REMOVED DEBRIS FROM CB 1/9", False)[0] == "clogged_basin"
    assert label_note("unclear what happened", False)[0] == "unclear"  # "clear" must not match "unclear"


def test_blank_and_excluded_notes_are_unclear_and_skip_llm() -> None:
    llm = FakeLLM("clogged_basin")
    assert label_note("", False, llm) == ("unclear", "rule")
    assert label_note("   ", False, llm) == ("unclear", "rule")
    assert label_note("pothole", True, llm) == ("unclear", "rule")
    assert llm.seen == []


@pytest.mark.parametrize("raw, note, status", [
    ("Case Closed. Closed date : 2026-01-20 17:24:17.87 Case Resolved Cleaned and removed debris from (2) cb's. 1/9",
     "Cleaned and removed debris from (2) cb's. 1/9", "Case Resolved"),
    ("Case Closed. Closed date : Tue Oct 21 10:00:00 EDT 2014 Resolved cleaned cb", "cleaned cb", "Resolved"),
    ("Case Closed Case Resolved Cleared", "Cleared", "Case Resolved"),
    ("Case Closed Case Resolved", "", "Case Resolved"),
    ("Case Closed", "", ""),
    ("", "", ""),
    ("Case Closed. Closed date : 2015-08-11 12:09:31.05 Case Resolved Case Closed. Fixing Technical Issue "
     "Original Closed date : 2015-07-15 11:48:17.803 Case Resolved CLEANED CB 7/4", "CLEANED CB 7/4", "Case Resolved"),
    ("Case Closed. Closed date : 2026-01-09 17:20:28.377 Case Resolved Cleaned &amp; flushed",
     "Cleaned & flushed", "Case Resolved"),
])
def test_split_closure(raw: str, note: str, status: str) -> None:
    assert split_closure(raw) == (note, status)


def test_exclusions() -> None:
    assert is_excluded("test", "")
    assert is_excluded("", "Case Invalid")
    assert is_excluded("several duplicates", "")
    assert is_excluded("wrong e-form", "")
    assert is_excluded("", "Duplicate of Existing Case")
    assert not is_excluded("cleaned cb, contest area", "Case Resolved")


def test_parse_answer() -> None:
    assert parse_answer(" clogged_basin\n") == "clogged_basin"
    assert parse_answer("`unclear`.") == "unclear"
    assert parse_answer("clogged_basin because leaves") is None
    assert parse_answer("") is None


def test_no_bedrock_in_fallback(tmp_path) -> None:
    assert make_labeler(tmp_path / "cache.json") is None


def test_bedrock_labeler_uses_cache_and_never_raises(tmp_path) -> None:
    class Client:
        calls = 0

        def converse(self, **_kwargs: object) -> dict:
            Client.calls += 1
            if Client.calls > 1:
                raise RuntimeError("throttled")
            return {"output": {"message": {"content": [{"text": "grading_capacity"}]}}}

    lab = BedrockLabeler("model", tmp_path / "cache.json", client=Client())
    assert lab.label("street has a low area") == "grading_capacity"
    assert lab.label("street has a low area") == "grading_capacity"  # cached, no new call
    assert Client.calls == 1
    for i in range(5):
        assert lab.label(f"note {i}") is None  # errors become None, then calls stop
    assert Client.calls == 4
    lab.save_cache()
    assert BedrockLabeler("model", tmp_path / "cache.json", client=Client()).cache == {
        "street has a low area": "grading_capacity"
    }
