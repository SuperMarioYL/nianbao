"""Tests for the session-log adapters.

The ZCode tests pin the plan's critical contract: model-io lines repeat the
whole conversation in cumulative ``request.messages`` windows, so messages
must be deduplicated by index and never counted per line.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from nianbao.adapters import claude_code, generic_jsonl, parse_file, sniff
from nianbao.metrics import compute_yearbook

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = FIXTURES / "sample_session.jsonl"


def _write(path: Path, records: list[dict]) -> Path:
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    return path


def _model_io(
    started_at: str,
    messages: list[dict],
    *,
    offset: int = 0,
    kind: str = "full",
    session_id: str = "sess-zc-0001",
) -> dict:
    return {
        "type": "model_io",
        "sessionId": session_id,
        "turnId": f"turn-{offset}-{len(messages)}",
        "startedAt": started_at,
        "completedAt": started_at,
        "model": "glm-4.7",
        "request": {
            "messages": messages,
            "messageCount": offset + len(messages),
            "messageOffset": offset,
            "messagesKind": kind,
        },
        "response": {"id": "resp"},
    }


def _msg(role: str, text: str) -> dict:
    return {"role": role, "content": text}


# -- format sniffing ----------------------------------------------------------


def test_sniff_skips_leading_bookkeeping_records(tmp_path):
    path = _write(tmp_path / "sess.jsonl", [
        {"type": "queue-operation", "op": "enqueue", "sessionId": "s1"},
        {"type": "file-history-snapshot", "snapshot": {}},
        {"type": "user", "message": {"role": "user", "content": "hi"}, "timestamp": "2026-06-03T09:00:00Z"},
    ])
    assert sniff(path) == "claude-code"


def test_sniff_returns_none_without_classifiable_records(tmp_path):
    path = _write(tmp_path / "noise.jsonl", [
        {"type": "mode", "mode": "normal"},
        {"type": "summary", "summary": "earlier work", "leafUuid": "x"},
    ])
    assert sniff(path) is None
    assert parse_file(path) is None


# -- Claude Code ---------------------------------------------------------------


def test_claude_code_fixture_counts():
    record = claude_code.parse_session_file(SAMPLE)
    assert record is not None
    assert record.harness == "claude-code"
    assert record.project == "api-server"
    assert record.session_id == "3f2a9c1e-7b4d-4e8a-9c2f-5d6e7f8a9b0c"
    assert record.started_at == datetime(2026, 6, 3, 9, 12, 30, 116000, tzinfo=timezone.utc)
    # 6 typed user messages; tool_results, sidechain, isMeta and injections dropped.
    assert len(record.user_msgs) == 6
    assert record.assistant_msgs == 8
    assert all(not m.text.lstrip().startswith(("<system-reminder>", "<command-name>"))
               for m in record.user_msgs)
    # 2 corrections (不对 / 重新), 1 severity-3 complaint (他妈).
    assert [c.kind for c in record.corrections] == ["negation", "redo"]
    assert [c.severity for c in record.complaints] == [3]


def test_claude_code_filters_harness_noise(tmp_path):
    path = _write(tmp_path / "s.jsonl", [
        {"type": "user", "message": {"role": "user", "content": "开始"},
         "timestamp": "2026-06-03T09:00:00Z"},
        {"type": "user", "isMeta": True,
         "message": {"role": "user", "content": [{"type": "text", "text": "<command-name>/status</command-name>"}]},
         "timestamp": "2026-06-03T09:00:05Z"},
        {"type": "user", "isCompactSummary": True,
         "message": {"role": "user", "content": "This session is being continued from a previous conversation."},
         "timestamp": "2026-06-03T09:00:10Z"},
        {"type": "user", "message": {"role": "user", "content": [{"tool_use_id": "t1", "type": "tool_result", "content": "ok"}]},
         "timestamp": "2026-06-03T09:00:15Z"},
        {"type": "user", "isSidechain": True,
         "message": {"role": "user", "content": "查找路由定义"},
         "timestamp": "2026-06-03T09:00:20Z"},
        {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "<system-reminder>waiting</system-reminder>"}]},
         "timestamp": "2026-06-03T09:00:25Z"},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "好的"}]},
         "timestamp": "2026-06-03T09:00:30Z"},
    ])
    record = claude_code.parse_session_file(path)
    assert record is not None
    assert [m.text for m in record.user_msgs] == ["开始"]
    assert record.assistant_msgs == 1


# -- ZCode / GLM model-io --------------------------------------------------------


def test_model_io_cumulative_arrays_never_double_count(tmp_path):
    # Three calls; every line repeats the conversation so far, full kind.
    path = _write(tmp_path / "model-io-sess-zc-0001.jsonl", [
        _model_io("2026-06-03T02:00:00Z", [_msg("user", "把日志解析成 JSONL")]),
        _model_io("2026-06-03T02:01:00Z", [
            _msg("user", "把日志解析成 JSONL"),
            _msg("assistant", "已实现逐行解析。"),
        ]),
        _model_io("2026-06-03T02:02:00Z", [
            _msg("user", "把日志解析成 JSONL"),
            _msg("assistant", "已实现逐行解析。"),
            _msg("user", "不对，边界情况漏了空行"),
            _msg("assistant", "已补上空行处理。"),
        ]),
        # Terminal delta record: offset == messageCount, no messages.
        _model_io("2026-06-03T02:02:30Z", [], offset=4, kind="delta"),
    ])
    record = generic_jsonl.parse_model_io_file(path)
    assert record is not None
    assert record.harness == "zcode"
    assert record.session_id == "sess-zc-0001"
    assert record.started_at == datetime(2026, 6, 3, 2, 0, 0, tzinfo=timezone.utc)
    assert len(record.user_msgs) == 2  # NOT 1 + 1 + 2 counted per line
    assert record.assistant_msgs == 2
    assert record.user_msgs[0].text == "把日志解析成 JSONL"
    assert record.user_msgs[1].text == "不对，边界情况漏了空行"
    # Best-effort dating: the startedAt of the call that first carried the msg.
    assert record.user_msgs[0].ts == datetime(2026, 6, 3, 2, 0, 0, tzinfo=timezone.utc)
    assert record.user_msgs[1].ts == datetime(2026, 6, 3, 2, 2, 0, tzinfo=timezone.utc)
    assert [c.kind for c in record.corrections] == ["negation"]


def test_model_io_tail_windows_are_stitched(tmp_path):
    # Rolling 3-message windows at offsets 0 and 2; index 2 overlaps.
    path = _write(tmp_path / "model-io-sess-zc-0002.jsonl", [
        _model_io("2026-06-03T03:00:00Z", [
            _msg("system", "你是一个编程助手"),
            _msg("user", "第一条"),
            _msg("assistant", "收到"),
        ], offset=0, kind="tail", session_id="sess-zc-0002"),
        _model_io("2026-06-03T03:05:00Z", [
            _msg("assistant", "收到"),
            _msg("user", "第二条"),
            _msg("tool", "tool output"),
        ], offset=2, kind="tail", session_id="sess-zc-0002"),
    ])
    record = generic_jsonl.parse_model_io_file(path)
    assert record is not None
    assert [m.text for m in record.user_msgs] == ["第一条", "第二条"]
    assert record.assistant_msgs == 1
    # Overlapping window did not duplicate the assistant message.
    assert record.turns == 2


def test_model_io_subagent_files_are_skipped(tmp_path):
    path = _write(tmp_path / "model-io-sess_subagent_agent_7d0d.jsonl", [
        _model_io("2026-06-03T04:00:00Z", [_msg("user", "子任务：检索文件")]),
    ])
    assert generic_jsonl.parse_model_io_file(path) is None
    assert parse_file(path) is None


def test_model_io_system_role_and_injections_dropped(tmp_path):
    path = _write(tmp_path / "model-io-sess-zc-0003.jsonl", [
        _model_io("2026-06-03T05:00:00Z", [
            _msg("system", "system prompt"),
            _msg("user", "<system-reminder>injected</system-reminder>"),
            _msg("user", "真实输入"),
        ]),
    ])
    record = generic_jsonl.parse_model_io_file(path)
    assert record is not None
    assert [m.text for m in record.user_msgs] == ["真实输入"]


# -- plain chat exports -----------------------------------------------------------


def test_chat_file_counts_per_line(tmp_path):
    path = _write(tmp_path / "chat.jsonl", [
        {"role": "user", "content": "不对，重来", "timestamp": "2026-06-03T06:00:00Z"},
        {"role": "assistant", "content": "好的"},
        {"role": "user", "content": "<system-reminder>x</system-reminder>", "timestamp": "2026-06-03T06:01:00Z"},
        {"role": "user", "content": "谢谢", "timestamp": "2026-06-03T06:02:00Z"},
    ])
    record = generic_jsonl.parse_chat_file(path)
    assert record is not None
    assert record.harness == "chat"
    assert len(record.user_msgs) == 2
    assert record.assistant_msgs == 1
    assert record.started_at == datetime(2026, 6, 3, 6, 0, 0, tzinfo=timezone.utc)
    assert [c.kind for c in record.corrections] == ["negation"]


# -- dispatch ----------------------------------------------------------------------


def test_parse_file_dispatches_by_sniffed_format(tmp_path):
    claude = _write(tmp_path / "a.jsonl", [
        {"type": "user", "message": {"role": "user", "content": "hi"},
         "timestamp": "2026-06-03T07:00:00Z"},
    ])
    zcode = _write(tmp_path / "b.jsonl", [
        _model_io("2026-06-03T07:00:00Z", [_msg("user", "你好")]),
    ])
    chat = _write(tmp_path / "c.jsonl", [
        {"role": "user", "content": "hello", "timestamp": "2026-06-03T07:00:00Z"},
    ])
    harnesses = {parse_file(p).harness for p in (claude, zcode, chat)}
    assert harnesses == {"claude-code", "zcode", "chat"}


# -- cross-file timestamp normalization ---------------------------------------------


def test_mixed_naive_aware_chat_files_compute_together(tmp_path):
    # One export wrote naive local stamps, another UTC "Z" stamps; pre-fix the
    # metrics fold crashed comparing them (uncaught TypeError).
    naive = _write(tmp_path / "naive.jsonl", [
        {"role": "user", "content": "帮我看下这个报错", "timestamp": "2026-06-03T06:00:00"},
    ])
    aware = _write(tmp_path / "aware.jsonl", [
        {"role": "user", "content": "加个登录页", "timestamp": "2026-06-04T06:00:00Z"},
    ])
    records = [parsed for parsed in (parse_file(naive), parse_file(aware))
               if parsed is not None]
    assert len(records) == 2
    report = compute_yearbook(records)
    assert report.total_user_messages == 2
    assert report.total_sessions == 2
