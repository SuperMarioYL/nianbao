"""Session-log adapters.

Each adapter owns the mapping from one harness's local JSONL format onto
:class:`nianbao.schema.SessionRecord`. :func:`parse_file` sniffs a file's
format from its first classifiable record and dispatches to the owning
adapter, so the CLI can point ``--logs-dir`` at any mix of harness log
directories.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..schema import SessionRecord

#: Prefixes of "user" content that the harness injected rather than the human
#: typed (slash-command expansion, reminders, task notifications, interrupts,
#: IDE events, skill prompt expansion). Shared by all line-per-message formats.
INJECTED_PREFIXES: tuple[str, ...] = (
    "<command-message>",
    "<command-name>",
    "<local-command",
    "<system-reminder>",
    "<task-notification>",
    "<ide_opened_file",
    "[Request interrupted",
    "Base directory for this skill:",
)


def is_injected(text: str) -> bool:
    """True if the whole message is harness-injected noise."""
    stripped = text.lstrip()
    return any(stripped.startswith(prefix) for prefix in INJECTED_PREFIXES)


def iter_records(path: Path, limit: int | None = None):
    """Yield parsable JSON object lines from a JSONL file.

    Unparsable lines are skipped; ``OSError`` and non-object lines end the
    iteration (returns nothing for an unreadable file).
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as fp:
            yielded = 0
            for line in fp:
                if limit is not None and yielded >= limit:
                    return
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(record, dict):
                    yielded += 1
                    yield record
    except OSError:
        return


def read_first_record(path: Path) -> dict | None:
    """First parsable JSON object in the file, or None if unreadable/empty."""
    return next(iter_records(path), None)


def sniff(path: Path, max_records: int = 50) -> str | None:
    """Identify the log format: 'claude-code' | 'zcode' | 'chat' | None.

    Harnesses prepend non-message bookkeeping records (mode switches, file
    snapshots, queue operations, summaries) before the first real message, so
    detection scans until the first *classifiable* record — never just line 1.
    """
    for record in iter_records(path, limit=max_records):
        if record.get("type") == "model_io":
            return "zcode"
        if record.get("type") in ("user", "assistant") or isinstance(
            record.get("message"), dict
        ):
            return "claude-code"
        if "role" in record and ("content" in record or "text" in record):
            return "chat"
    return None


# Imported below the shared helpers above: the submodules import
# ``is_injected`` from this package, so the package must define it first.
from . import claude_code, generic_jsonl  # noqa: E402


def parse_file(path: Path) -> SessionRecord | None:
    """Parse one JSONL session file with the adapter that owns its format."""
    path = Path(path)
    kind = sniff(path)
    if kind == "claude-code":
        return claude_code.parse_session_file(path)
    if kind == "zcode":
        return generic_jsonl.parse_model_io_file(path)
    if kind == "chat":
        return generic_jsonl.parse_chat_file(path)
    return None
