"""Yearbook computation — fold SessionRecords into a YearbookReport.

Metric definitions (the product's owned behavioral layer):

- **correction rate** — share of typed user messages that contain a
  correction lexicon hit. The "33% of my messages were corrections" number.
- **complaint heatmap** — severity-weighted complaint count per
  (month, week-of-month) cell; weeks are ``(day - 1) // 7`` capped at 4.
- **worst week** — the heatmap cell with the highest severity weight.
- **project survival** — per project: first/last session date, session count.
- **topic drift** — per month TF-IDF top keywords over typed user messages.
"""

from __future__ import annotations

from datetime import datetime

from .schema import (
    ProjectSurvival,
    SessionRecord,
    WEEKS_PER_MONTH,
    YearbookReport,
)
from .topics import extract_keywords

TOP_KEYWORDS = 8


def _month_key(ts: datetime) -> str:
    return f"{ts.year:04d}-{ts.month:02d}"


def _week_slot(ts: datetime) -> int:
    return min((ts.day - 1) // 7, WEEKS_PER_MONTH - 1)


def compute_yearbook(records: list[SessionRecord]) -> YearbookReport:
    """Aggregate session records into a YearbookReport.

    Fills each record's ``topics`` in place (session-level TF-IDF keywords)
    before folding. Records without user messages are ignored.
    """
    records = [r for r in records if r.user_msgs]
    if not records:
        raise ValueError("no sessions with user messages to analyze")

    # Session topics: TF-IDF across sessions.
    session_docs = {
        rec.session_id: "\n".join(m.text for m in rec.user_msgs) for rec in records
    }
    session_topics = extract_keywords(session_docs, top_n=TOP_KEYWORDS)
    for rec in records:
        rec.topics = session_topics.get(rec.session_id, [])

    started = min(rec.started_at for rec in records)
    ended = max(
        max((m.ts for m in rec.user_msgs), default=rec.started_at) for rec in records
    )

    corrections = sum(len(rec.corrections) for rec in records)
    complaints = [c for rec in records for c in rec.complaints]
    user_messages = sum(len(rec.user_msgs) for rec in records)
    assistant_messages = sum(rec.assistant_msgs for rec in records)

    heatmap: dict[str, list[float]] = {}
    for complaint in complaints:
        key = _month_key(complaint.ts)
        slots = heatmap.setdefault(key, [0.0] * WEEKS_PER_MONTH)
        slots[_week_slot(complaint.ts)] += complaint.severity
    heatmap = {key: heatmap[key] for key in sorted(heatmap)}

    worst_week: tuple[str, int, float, int] | None = None
    for key in sorted(heatmap):
        counts = [sum(1 for c in complaints if _month_key(c.ts) == key and _week_slot(c.ts) == w)
                  for w in range(WEEKS_PER_MONTH)]
        for week, weight in enumerate(heatmap[key]):
            if weight > 0 and (worst_week is None or weight > worst_week[2]):
                worst_week = (key, week, weight, counts[week])

    survival: dict[str, ProjectSurvival] = {}
    for rec in records:
        entry = survival.get(rec.project)
        if entry is None:
            survival[rec.project] = ProjectSurvival(rec.project, rec.started_at, rec.started_at, 1)
        else:
            entry.sessions += 1
            entry.first_seen = min(entry.first_seen, rec.started_at)
            entry.last_seen = max(entry.last_seen, rec.started_at)
    project_survival = sorted(survival.values(), key=lambda p: (-p.sessions, p.project))

    month_docs: dict[str, str] = {}
    for rec in records:
        for msg in rec.user_msgs:
            month_docs.setdefault(_month_key(msg.ts), []).append(msg.text)
    topic_drift = extract_keywords(
        {key: "\n".join(texts) for key, texts in month_docs.items()},
        top_n=TOP_KEYWORDS,
    )

    return YearbookReport(
        period_start=started,
        period_end=ended,
        total_sessions=len(records),
        total_user_messages=user_messages,
        total_assistant_messages=assistant_messages,
        total_projects=len(survival),
        correction_count=corrections,
        correction_rate=(corrections / user_messages) if user_messages else 0.0,
        complaint_count=len(complaints),
        complaint_heatmap=heatmap,
        worst_week=worst_week,
        project_survival=project_survival,
        topic_drift=dict(sorted(topic_drift.items())),
    )
