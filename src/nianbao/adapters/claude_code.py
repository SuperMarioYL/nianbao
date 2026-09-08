"""Claude Code adapter — ``~/.claude/projects/<munged-cwd>/<sessionId>.jsonl``.

Verified field names (from real logs on this machine, Claude Code 2.1.x):
one JSON object per line; message-bearing records carry ``type``
("user" | "assistant" | ...), ``message.role``, ``message.content`` (a plain
string, or a list of blocks with ``type`` "text" / "tool_result"),
``timestamp`` (ISO-8601 UTC with Z), ``sessionId``, ``cwd``, ``isSidechain``.

What counts as a typed user message:
- ``type == "user"``, ``isSidechain`` falsy (sidechain = sub-agent traffic),
- not a meta record (``isMeta`` / ``isCompactSummary`` flags — harness
  bookkeeping like compact-boundary continuation dumps ride the user channel),
- content is a string or text blocks, and contains no ``tool_result`` block
  (those are tool outputs delivered back on the user channel),
- not a harness injection (slash-command wrappers, system reminders, task
  notifications, interrupts — see :data:`adapters.INJECTED_PREFIXES`).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .. import lexicons
from ..schema import SessionRecord, UserMessage
from . import is_injected


def _parse_ts(raw: str) -> datetime | None:
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _typed_text(content) -> str | None:
    """Extract human-typed text from a user message content, if any."""
    if isinstance(content, str):
        text = content.strip()
        return None if is_injected(text) or not text else text
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        texts = [
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ]
        text = "\n".join(t for t in texts if t and t.strip()).strip()
        return None if is_injected(text) or not text else text
    return None


def parse_session_file(path: Path) -> SessionRecord | None:
    """Project one Claude Code session JSONL onto a SessionRecord."""
    path = Path(path)
    user_msgs: list[UserMessage] = []
    assistant_count = 0
    session_id = path.stem
    project: str | None = None
    started_at: datetime | None = None

    try:
        fp = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return None
    with fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict):
                continue

            ts = _parse_ts(record.get("timestamp", ""))
            if ts is not None and started_at is None:
                started_at = ts
            if record.get("sessionId"):
                session_id = record["sessionId"]
            if not project:
                cwd = record.get("cwd")
                if cwd:
                    project = Path(cwd).name or None
            if record.get("isSidechain"):
                continue
            if record.get("isMeta") or record.get("isCompactSummary"):
                continue

            kind = record.get("type")
            if kind == "user":
                text = _typed_text((record.get("message") or {}).get("content"))
                if text is not None and ts is not None:
                    user_msgs.append(UserMessage(ts, text))
            elif kind == "assistant":
                assistant_count += 1

    if not user_msgs or started_at is None:
        return None
    record_out = SessionRecord(
        harness="claude-code",
        project=project or path.parent.name,
        session_id=session_id,
        started_at=started_at,
        turns=len(user_msgs),
        assistant_msgs=assistant_count,
        user_msgs=user_msgs,
    )
    lexicons.annotate(record_out)
    return record_out
