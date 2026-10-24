"""Shared DrainFast data shapes (frozen contract). Import these; never redefine them.

Implements .kiro/specs/shared-contracts (Requirements 1-11). Changes go through a
pull request titled "contract: ...".
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------- constants

STORM_DAY_THRESHOLD_IN: float = 1.0
STATUS_UNCLEAR: str = "Status unclear"
FACTOR_SUM_TOLERANCE: float = 1e-6


# ---------------------------------------------------------------- enums


class CauseLabel(str, Enum):
    clogged_basin = "clogged_basin"
    grading_capacity = "grading_capacity"
    coastal_tide = "coastal_tide"
    unclear = "unclear"


class LabelSource(str, Enum):
    rule = "rule"
    llm = "llm"


class ReportStatus(str, Enum):
    open = "open"
    closed = "closed"


class BasinOwner(str, Enum):
    BWSC = "BWSC"
    City = "City"
    Private = "Private"
    Mixed = "Mixed"
    Unknown = "Unknown"


# ---------------------------------------------------------------- shared types


def _not_blank(value: str) -> str:
    """Reject empty or whitespace-only strings; return the value unchanged."""
    if value.strip() == "":
        raise ValueError("must not be blank")
    return value


NonBlankStr = Annotated[str, AfterValidator(_not_blank)]
Latitude = Annotated[float, Field(ge=-90.0, le=90.0, allow_inf_nan=False)]
Longitude = Annotated[float, Field(ge=-180.0, le=180.0, allow_inf_nan=False)]
Rate = Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
RainInches = Annotated[float, Field(ge=0.0, le=30.0, allow_inf_nan=False)]
NonNegFloat = Annotated[float, Field(ge=0.0, allow_inf_nan=False)]
FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
TicketIdList = Annotated[list[NonBlankStr], Field(min_length=1)]


class ContractModel(BaseModel):
    """Base for every contract model: unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------- models


class Report(ContractModel):
    """One storm-related 311 report after cleaning and labeling."""

    ticket_id: NonBlankStr
    opened_at: AwareDatetime
    closed_at: AwareDatetime | None = None
    status: ReportStatus
    lat: Latitude
    lon: Longitude
    cell_id: NonBlankStr
    text: str
    closing_note: str | None = None
    note_blank: bool
    cause_label: CauseLabel
    label_source: LabelSource
    storm_day: date | None = None
    neighborhood: NonBlankStr
    ej_flag: bool
    duplicate_of: str | None = None

    @model_validator(mode="after")
    def _check_consistency(self) -> Report:
        if self.closed_at is not None and self.closed_at < self.opened_at:
            raise ValueError("closed_at must not be earlier than opened_at")
        if self.status == ReportStatus.open and self.closed_at is not None:
            raise ValueError("status open requires closed_at to be None")
        if self.duplicate_of is not None and self.duplicate_of == self.ticket_id:
            raise ValueError("duplicate_of must differ from ticket_id")
        return self


class Cell(ContractModel):
    """One ~100 m grid cell (see contracts/cells.py)."""

    cell_id: NonBlankStr
    lat: Latitude
    lon: Longitude
    neighborhood: NonBlankStr
    basin_count: int = Field(ge=0)
    basin_owner: BasinOwner
    ej_flag: bool
    flood_area_flag: bool
    tree_density: NonNegFloat | None = None


class Storm(ContractModel):
    """Daily rainfall at Boston Logan, with the high-tide flag."""

    storm_day: date
    rain_total_in: RainInches
    max_hourly_in: RainInches
    high_tide_flag: bool

    @model_validator(mode="after")
    def _check_rain(self) -> Storm:
        if self.max_hourly_in > self.rain_total_in:
            raise ValueError("max_hourly_in must not exceed rain_total_in")
        return self

    def is_storm_day(self, threshold: float = STORM_DAY_THRESHOLD_IN) -> bool:
        """True when the day's rain total meets the storm threshold."""
        return self.rain_total_in >= threshold


class FactorContribution(ContractModel):
    """One named term of a priority score. Negative and zero contributions are allowed."""

    factor: NonBlankStr
    value: FiniteFloat
    contribution: FiniteFloat


def _check_factor_sum(priority_score: float, factors: list[FactorContribution]) -> None:
    """Raise when priority_score is not the sum of its factor contributions."""
    total = sum(f.contribution for f in factors)
    if abs(priority_score - total) > FACTOR_SUM_TOLERANCE:
        raise ValueError(f"priority_score ({priority_score}) must equal the sum of factors ({total})")


class BriefItem(ContractModel):
    """One ranked cell in the pre-storm crew brief."""

    rank: int = Field(ge=1)
    cell_id: NonBlankStr
    lat: Latitude
    lon: Longitude
    priority_score: FiniteFloat
    factors: list[FactorContribution] = Field(min_length=1)
    reason: NonBlankStr
    evidence_ticket_ids: TicketIdList

    @model_validator(mode="after")
    def _check_score(self) -> BriefItem:
        _check_factor_sum(self.priority_score, self.factors)
        return self


class BriefResponse(ContractModel):
    """The crew brief for one date and crew count."""

    date: date
    forecast_rain_in: NonNegFloat
    high_tide_flag: bool
    crews: int = Field(ge=1)
    capacity_per_crew: int = Field(default=30, ge=1)
    items: list[BriefItem]
    fallback_mode: bool

    @model_validator(mode="after")
    def _check_items(self) -> BriefResponse:
        limit = self.crews * self.capacity_per_crew
        if len(self.items) > limit:
            raise ValueError(f"items ({len(self.items)}) exceed crews x capacity_per_crew ({limit})")
        ranks = [item.rank for item in self.items]
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError("item ranks must be 1, 2, ..., n in list order")
        return self


class BacklogItem(ContractModel):
    """One open storm-related case, ranked by backlog priority."""

    ticket_id: NonBlankStr
    cell_id: NonBlankStr
    opened_at: AwareDatetime
    age_days: NonNegFloat
    cause_label: CauseLabel
    note_blank: bool
    status_label: NonBlankStr
    priority_score: FiniteFloat
    factors: list[FactorContribution] = Field(min_length=1)
    evidence_ticket_ids: TicketIdList

    @model_validator(mode="after")
    def _check_item(self) -> BacklogItem:
        _check_factor_sum(self.priority_score, self.factors)
        if self.note_blank and self.status_label != STATUS_UNCLEAR:
            raise ValueError(f"note_blank requires status_label == {STATUS_UNCLEAR!r}")
        return self


class BacktestResult(ContractModel):
    """Hit rates on one held-out storm for DrainFast and both baselines."""

    storm_day: date
    n_fixable_reports: int = Field(ge=0)
    n_cells: int = Field(ge=1)
    hit_rate_top100: Rate
    hit_rate_top200: Rate
    random_top100: Rate
    random_top200: Rate
    most_complaints_top100: Rate
    most_complaints_top200: Rate

    @model_validator(mode="after")
    def _check_order(self) -> BacktestResult:
        for method in ("hit_rate", "random", "most_complaints"):
            a = getattr(self, f"{method}_top100")
            b = getattr(self, f"{method}_top200")
            if a > b:
                raise ValueError(f"{method}: top100 ({a}) > top200 ({b})")
        return self


class RainTrendPoint(ContractModel):
    """Heavy-rain days in one year at Boston Logan."""

    year: int = Field(ge=1900, le=2100)
    heavy_rain_days: int = Field(ge=0, le=366)


ALL_MODELS: tuple[type[ContractModel], ...] = (
    Report, Cell, Storm, FactorContribution, BriefItem, BriefResponse,
    BacklogItem, BacktestResult, RainTrendPoint,
)
ALL_ENUMS: tuple[type[Enum], ...] = (CauseLabel, LabelSource, ReportStatus, BasinOwner)
