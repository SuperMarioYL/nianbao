"""Normalized session-behavior schema.

Every adapter projects a heterogeneous harness log onto :class:`SessionRecord`,
and :func:`nianbao.metrics.compute_yearbook` folds records into a
:class:`YearbookReport`. These two shapes are the product's owned primitives:
the behavioral metric definitions live downstream of them, the card format
(:class:`CardSpec`) downstream of the report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

#: Number of week slots per month in the complaint heatmap (day // 7, capped).
WEEKS_PER_MONTH = 5


@dataclass
class UserMessage:
    """One message the human actually typed (tool results and harness
    injections are filtered out by the adapters)."""

    ts: datetime
    text: str


@dataclass
class Correction:
    """A lexicon hit marking "I am steering the agent back on course"."""

    ts: datetime
    kind: str  # lexicon category: negation / redo / clarify / revert


@dataclass
class Complaint:
    """A lexicon hit marking frustration, severity 1 (mild) to 3 (serious)."""

    ts: datetime
    severity: int


@dataclass
class SessionRecord:
    """Normalized projection of one agent session log."""

    harness: str  # e.g. "claude-code", "zcode", "chat"
    project: str
    session_id: str
    started_at: datetime
    turns: int
    assistant_msgs: int = 0  # assistant-side messages (for the message total)
    user_msgs: list[UserMessage] = field(default_factory=list)
    corrections: list[Correction] = field(default_factory=list)
    complaints: list[Complaint] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)


@dataclass
class ProjectSurvival:
    """How long a project stayed alive in the logs."""

    project: str
    first_seen: datetime
    last_seen: datetime
    sessions: int

    @property
    def days(self) -> int:
        return max((self.last_seen - self.first_seen).days, 0)


@dataclass
class CardSpec:
    """Bind one yearbook metric to a card layout and copy.

    ``key`` selects the renderer layout in :mod:`nianbao.cards`; ``data``
    carries the metric payload the layout draws (e.g. the heatmap grid).
    """

    key: str  # hero / correction / complaints / projects / topics / closing
    title: str
    headline: str
    subline: str
    data: dict = field(default_factory=dict)


@dataclass
class YearbookReport:
    """Aggregated yearbook over a set of session records."""

    period_start: datetime
    period_end: datetime
    total_sessions: int
    total_user_messages: int
    total_assistant_messages: int
    total_projects: int
    correction_count: int
    correction_rate: float  # corrections / typed user messages, 0..1
    complaint_count: int
    #: "YYYY-MM" -> WEEKS_PER_MONTH severity-weighted complaint slots.
    complaint_heatmap: dict[str, list[float]] = field(default_factory=dict)
    worst_week: tuple[str, int, float, int] | None = None  # (month, week, weight, count)
    project_survival: list[ProjectSurvival] = field(default_factory=list)
    #: "YYYY-MM" -> top keywords (topic drift).
    topic_drift: dict[str, list[str]] = field(default_factory=dict)
    cards: list[CardSpec] = field(default_factory=list)

    @property
    def period_days(self) -> int:
        return max((self.period_end - self.period_start).days, 1)
