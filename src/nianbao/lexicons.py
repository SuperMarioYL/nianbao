"""Chinese + English correction / complaint lexicons.

Pure data plus two matchers — the single source of truth for what counts as a
correction or a complaint. Terms were chosen from real coding-agent chat logs
(zh + en); matching is intentionally a simple case-insensitive substring scan
so behavior stays auditable and fully offline.

Categories (``Correction.kind``):
    negation  — "that's wrong / not what I said"
    redo      — "do it again / start over"
    clarify   — "what I meant was ..."
    revert    — "put it back / undo"

Complaint severities:
    3 — swearing or "I never asked for this" (the serious bucket)
    2 — visible frustration
    1 — mild sighs
"""

from __future__ import annotations

from .schema import Correction, Complaint, SessionRecord

# (term, kind)
CORRECTIONS_ZH: tuple[tuple[str, str], ...] = (
    ("不对", "negation"),
    ("不是这样", "negation"),
    ("搞错了", "negation"),
    ("理解错了", "negation"),
    ("又错了", "negation"),
    ("还是错", "negation"),
    ("不行", "negation"),
    ("重新", "redo"),
    ("再来一次", "redo"),
    ("重做", "redo"),
    ("我说的是", "clarify"),
    ("我是说", "clarify"),
    ("我的意思是", "clarify"),
    ("回滚", "revert"),
    ("撤销", "revert"),
    ("改回", "revert"),
    ("恢复到", "revert"),
    ("还原", "revert"),
)

CORRECTIONS_EN: tuple[tuple[str, str], ...] = (
    ("not what i asked", "negation"),
    ("that's wrong", "negation"),
    ("that is wrong", "negation"),
    ("wrong", "negation"),
    ("incorrect", "negation"),
    ("still not", "negation"),
    ("try again", "redo"),
    ("redo", "redo"),
    ("start over", "redo"),
    ("regenerate", "redo"),
    ("i said", "clarify"),
    ("i meant", "clarify"),
    ("i was asking", "clarify"),
    ("revert", "revert"),
    ("undo", "revert"),
    ("put it back", "revert"),
    ("go back to", "revert"),
    ("restore", "revert"),
)

# (term, severity)
COMPLAINTS_ZH: tuple[tuple[str, int], ...] = (
    ("我从来没让你", 3),
    ("谁让你", 3),
    ("我操", 3),
    ("他妈", 3),
    ("妈的", 3),
    ("tmd", 3),
    ("垃圾", 3),
    ("废物", 3),
    ("智障", 3),
    ("脑残", 3),
    ("疯了吧", 3),
    ("服了", 2),
    ("无语", 2),
    ("又来", 2),
    ("怎么又", 2),
    ("搞什么", 2),
    ("受不了", 2),
    ("你到底", 2),
    ("烦死", 2),
    ("气死", 2),
    ("什么玩意", 2),
    ("一塌糊涂", 2),
    ("完全跑偏", 2),
    ("算了", 1),
    ("好吧", 1),
    ("唉", 1),
    ("崩溃", 1),
    ("心累", 1),
    ("麻烦", 1),
)

COMPLAINTS_EN: tuple[tuple[str, int], ...] = (
    ("i never asked", 3),
    ("who told you", 3),
    ("are you kidding", 3),
    ("fucking", 3),
    ("fuck", 3),
    ("shit", 3),
    ("wtf", 3),
    ("damn", 3),
    ("useless", 3),
    ("garbage", 3),
    ("piece of junk", 3),
    ("frustrating", 2),
    ("frustrated", 2),
    ("seriously", 2),
    ("come on", 2),
    ("not again", 2),
    ("i give up", 2),
    ("give up", 2),
    ("you keep", 2),
    ("still failing", 2),
    ("sigh", 1),
    ("ugh", 1),
    ("whatever", 1),
    ("fine,", 1),
)


def match_correction(text: str) -> str | None:
    """Return the kind of the first correction term found, else None."""
    lowered = text.lower()
    for terms in (CORRECTIONS_ZH, CORRECTIONS_EN):
        for term, kind in terms:
            if term in text or term in lowered:
                return kind
    return None


def match_complaint(text: str) -> int | None:
    """Return the highest complaint severity found in the text, else None."""
    lowered = text.lower()
    severity = 0
    for terms in (COMPLAINTS_ZH, COMPLAINTS_EN):
        for term, level in terms:
            if term in text or term in lowered:
                severity = max(severity, level)
    return severity or None


def annotate(record: SessionRecord) -> None:
    """Fill ``record.corrections`` / ``record.complaints`` from its user msgs.

    A message counts at most once per list (kind = first matched term,
    severity = max matched level), so rates stay per-message, matching the
    "33% of my messages contained a correction" framing.
    """
    for msg in record.user_msgs:
        kind = match_correction(msg.text)
        if kind is not None:
            record.corrections.append(Correction(msg.ts, kind))
        severity = match_complaint(msg.text)
        if severity is not None:
            record.complaints.append(Complaint(msg.ts, severity))
