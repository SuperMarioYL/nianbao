"""Best-effort generic JSONL adapter for non-Claude-Code harness logs.

Two shapes are handled:

**ZCode / GLM CLI model-io logs** (``~/.zcode/cli/rollout/model-io-sess_*.jsonl``).
Verified against real logs: one record per model call with
``{type: "model_io", sessionId, turnId, startedAt/completedAt, model,
request: {messages, messageCount, messageOffset, messagesKind}, response}``.
The whole conversation rides inside ``request.messages`` — repeated on every
line — so messages are NEVER counted per line. Window modes seen in real
logs:

- ``messagesKind: "full"`` — the array is the whole conversation, so the
  final line's ``request.messages`` already is the session (the plan's
  canonical case);
- ``messagesKind: "tail"`` — a rolling window indexed by ``messageOffset``
  into a longer conversation; windows are stitched by absolute index and
  overlapping/dropped indices are deduplicated;
- ``messagesKind: "delta"`` — an empty carry-over record at the end of a
  turn (``messageOffset == messageCount``); contributes nothing.

Records have no per-message timestamps, so each user message is dated with
the ``startedAt`` of the model call that first carried it — a best-effort,
monotone approximation. Detection keys on ``type == "model_io"``, never on a
Claude-Code-like shape. ``role: "system"`` turns and ``<system-reminder>``
content are skipped; ``role: "tool"`` results are assistant-side traffic.

**Plain chat exports** — one ``{"role", "content", "timestamp"?}`` object per
line, the common denominator of hand-rolled exports. Counted per line (these
are not cumulative).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .. import lexicons
from ..schema import SessionRecord, UserMessage
from . import is_injected


def _parse_ts(raw) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def _message_text(content) -> str | None:
    """Human-typed text of one conversation message, or None."""
    if isinstance(content, str):
        text = content.strip()
    elif isinstance(content, list):
        texts = [
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ]
        text = "\n".join(t for t in texts if t and t.strip()).strip()
    else:
        return None
    if not text or is_injected(text):
        return None
    return text


def _rebuild_conversation(model_io_records: list[dict]) -> list[tuple[datetime | None, dict]]:
    """Deduplicate cumulative/windowed request.messages into one conversation.

    Returns ``(startedAt, message)`` pairs ordered by conversation index; the
    timestamp is the startedAt of the model call that first carried the
    message (best-effort dating — records carry no per-message ts).
    """
    merged: dict[int, tuple[datetime | None, dict]] = {}
    total = 0
    for record in model_io_records:
        request = record.get("request") or {}
        messages = request.get("messages") or []
        offset = request.get("messageOffset") or 0
        count = request.get("messageCount")
        if isinstance(count, int):
            total = max(total, count)
        started = _parse_ts(record.get("startedAt"))
        for i, message in enumerate(messages):
            if isinstance(message, dict) and offset + i not in merged:
                merged[offset + i] = (started, message)
    # Without messageCount metadata, trust whatever indices we saw.
    return [merged[i] for i in sorted(merged) if total <= 0 or i < total]


def parse_model_io_file(path: Path) -> SessionRecord | None:
    """Project a ZCode/GLM model-io JSONL onto a SessionRecord."""
    path = Path(path)
    if "subagent" in path.stem:
        # model-io-sess_subagent_agent_*.jsonl holds sub-agent traffic whose
        # "user" turns are parent-agent prompts, not the human — the
        # sidechain equivalent, excluded for the same reason.
        return None
    model_io_records: list[dict] = []
    try:
        with open(path, encoding="utf-8", errors="replace") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(record, dict) and record.get("type") == "model_io":
                    model_io_records.append(record)
    except OSError:
        return None
    if not model_io_records:
        return None

    conversation = _rebuild_conversation(model_io_records)
    user_msgs: list[UserMessage] = []
    assistant_count = 0
    for started, message in conversation:
        role = message.get("role")
        if role == "user":
            text = _message_text(message.get("content"))
            if text is not None:
                user_msgs.append(UserMessage(started or datetime.now(timezone.utc), text))
        elif role == "assistant":
            assistant_count += 1

    if not user_msgs:
        return None
    first_started = _parse_ts(model_io_records[0].get("startedAt")) or datetime.now(timezone.utc)
    session_id = model_io_records[0].get("sessionId") or path.stem
    record_out = SessionRecord(
        harness="zcode",
        project="zcode",  # model_io records carry no cwd — see module docstring
        session_id=str(session_id),
        started_at=first_started,
        turns=len(user_msgs),
        assistant_msgs=assistant_count,
        user_msgs=user_msgs,
    )
    lexicons.annotate(record_out)
    return record_out


def parse_chat_file(path: Path) -> SessionRecord | None:
    """Project a plain per-line chat JSONL onto a SessionRecord."""
    path = Path(path)
    user_msgs: list[UserMessage] = []
    assistant_count = 0
    started_at: datetime | None = None
    session_id = path.stem
    try:
        fp = open(path, encoding="utf-8", errors="replace")
    except OSError:
        raise
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
            ts = _parse_ts(record.get("timestamp")) or _parse_ts(record.get("ts"))
            if ts is not None and started_at is None:
                started_at = ts
            if record.get("sessionId"):
                session_id = str(record["sessionId"])
            role = record.get("role")
            content = record.get("content", record.get("text", ""))
            if role == "user":
                text = _message_text(content)
                if text is not None:
                    user_msgs.append(UserMessage(ts or started_at or datetime.now(timezone.utc), text))
            elif role == "assistant":
                assistant_count += 1

    if not user_msgs:
        return None
    record_out = SessionRecord(
        harness="chat",
        project=path.parent.name,
        session_id=session_id,
        started_at=started_at or datetime.now(timezone.utc),
        turns=len(user_msgs),
        assistant_msgs=assistant_count,
        user_msgs=user_msgs,
    )
    lexicons.annotate(record_out)
    return record_out
