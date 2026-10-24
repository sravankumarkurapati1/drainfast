"""Cause labels for crew notes: ordered keyword rules first, optional LLM for the rest."""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import yaml

from data_pipeline.notes import normalize_text, split_closure

RULES_PATH: Path = Path(__file__).with_name("label_rules.yaml")
LABELS: tuple[str, ...] = ("clogged_basin", "grading_capacity", "coastal_tide", "unclear")
UNCLEAR = "unclear"
RULE = "rule"
LLM = "llm"


class NoteLabeler(Protocol):
    """Anything that can label an undecided note; returns a valid label or None."""

    def label(self, note: str) -> str | None: ...


@dataclass(frozen=True)
class Rule:
    label: str
    pattern: re.Pattern[str]


def _keyword_regex(keyword: str) -> str:
    """Match a keyword at the start of a word, allowing any whitespace between words."""
    words = [re.escape(w) for w in keyword.lower().split()]
    return r"\b" + r"\s+".join(words)


@lru_cache(maxsize=4)
def load_rules(path: Path = RULES_PATH) -> tuple[Rule, ...]:
    """Load the ordered rule groups from label_rules.yaml."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    rules: list[Rule] = []
    for group in data["rules"]:
        label = group["label"]
        if label not in LABELS:
            raise ValueError(f"label_rules.yaml: unknown label {label!r}")
        alternation = "|".join(_keyword_regex(k) for k in group["keywords"])
        rules.append(Rule(label, re.compile(f"(?:{alternation})", re.IGNORECASE)))
    return tuple(rules)


def rule_label(note: str) -> str | None:
    """Return the first matching rule group's label, or None when no rule matches."""
    text = normalize_text(note).lower()
    if not text:
        return None
    for rule in load_rules():
        if rule.pattern.search(text):
            return rule.label
    return None


def label_note(note: str, exclude: bool, llm: NoteLabeler | None = None) -> tuple[str, str]:
    """Label one crew note. Returns (cause_label, label_source).

    Blank or excluded notes are unclear. Rules decide next. Only notes no rule matches
    go to the LLM, and only a valid LLM answer is accepted; anything else is unclear.
    """
    text = normalize_text(note)
    if not text or exclude:
        return UNCLEAR, RULE
    decided = rule_label(text)
    if decided is not None:
        return decided, RULE
    if llm is not None:
        try:
            answer = llm.label(text)
        except Exception:  # the AI step must never break labeling
            answer = None
        if answer in LABELS:
            return answer, LLM
    return UNCLEAR, RULE


def label_report(text: str, llm: NoteLabeler | None = None) -> str:
    """Public helper for the backend: label free text or a raw closure_reason.

    Rule-based unless an LLM labeler is passed in.
    """
    note, _status = split_closure(text)
    return label_note(note, exclude=False, llm=llm)[0]
