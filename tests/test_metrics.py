"""Tests for the metrics layer: hand-computed expectations.

The bundled sample session is the plan's 33%-corrections repro — 6 typed
messages of which 2 contain a correction lexicon hit.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from nianbao import cards, lexicons
from nianbao.adapters import claude_code
from nianbao.metrics import compute_yearbook
from nianbao.schema import SessionRecord, UserMessage

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = FIXTURES / "sample_session.jsonl"


def _ts(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


def _session(
    project: str,
    session_id: str,
    started: str,
    messages: list[tuple[str, str]],
) -> SessionRecord:
    """Build a record the way adapters do: user msgs + lexicon annotation."""
    record = SessionRecord(
        harness="claude-code",
        project=project,
        session_id=session_id,
        started_at=_ts(started),
        turns=len(messages),
        user_msgs=[UserMessage(_ts(ts), text) for ts, text in messages],
    )
    lexicons.annotate(record)
    return record


# -- correction rate ---------------------------------------------------------


def test_correction_rate_counts_messages_not_lexicon_hits():
    # One message carrying two correction hits still counts once.
    record = _session("p", "s1", "2026-06-03T09:00", [
        ("2026-06-03T09:00", "帮我看下这个报错"),
        ("2026-06-03T09:05", "不对，重新生成一遍"),
        ("2026-06-03T09:10", "谢谢，可以了"),
    ])
    report = compute_yearbook([record])
    assert report.total_user_messages == 3
    assert report.correction_count == 1
    assert report.correction_rate == pytest.approx(1 / 3)


def test_sample_session_reproduces_33_percent():
    record = claude_code.parse_session_file(SAMPLE)
    assert record is not None
    report = compute_yearbook([record])

    assert report.total_sessions == 1
    assert report.total_user_messages == 6
    assert report.total_assistant_messages == 8
    assert report.correction_count == 2
    assert report.correction_rate == pytest.approx(2 / 6)
    assert round(report.correction_rate * 100) == 33
    assert report.complaint_count == 1
    assert report.total_projects == 1
    assert report.project_survival[0].project == "api-server"
    assert report.period_start == _ts("2026-06-03T09:12:30.116Z")


# -- complaint heatmap + worst week ------------------------------------------


def test_complaint_heatmap_and_worst_week():
    records = [
        _session("p", "s1", "2026-07-02T10:00", [
            ("2026-07-02T10:00", "我从来没让你改这个文件"),
        ]),
        _session("p", "s2", "2026-07-15T11:00", [
            ("2026-07-15T11:00", "服了，又来"),
        ]),
        _session("p", "s3", "2026-08-20T12:00", [
            ("2026-08-20T12:00", "唉，算了"),
        ]),
    ]
    report = compute_yearbook(records)
    # day 2 -> week slot 0, day 15 -> slot 2, day 20 -> slot 2; weights = severity.
    assert report.complaint_heatmap == {
        "2026-07": [3, 0, 2, 0, 0],
        "2026-08": [0, 0, 1, 0, 0],
    }
    assert report.worst_week == ("2026-07", 0, 3.0, 1)


def test_no_complaints_leaves_heatmap_empty():
    record = _session("p", "s1", "2026-06-03T09:00", [
        ("2026-06-03T09:00", "帮我看下这个报错"),
    ])
    report = compute_yearbook([record])
    assert report.complaint_heatmap == {}
    assert report.worst_week is None
    assert report.complaint_count == 0


# -- project survival ---------------------------------------------------------


def test_project_survival_ranges_and_ordering():
    records = [
        _session("web", "s1", "2026-03-01T09:00", [("2026-03-01T09:00", "加个登录页")]),
        _session("web", "s2", "2026-03-10T09:00", [("2026-03-10T09:00", "修一下样式")]),
        _session("web", "s3", "2026-04-02T09:00", [("2026-04-02T09:00", "上线前检查")]),
        _session("cli", "s4", "2026-05-01T09:00", [("2026-05-01T09:00", "写个脚本")]),
    ]
    report = compute_yearbook(records)
    assert [p.project for p in report.project_survival] == ["web", "cli"]
    web = report.project_survival[0]
    assert web.sessions == 3
    assert web.first_seen == _ts("2026-03-01T09:00")
    assert web.last_seen == _ts("2026-04-02T09:00")
    assert web.days == 32


# -- topic drift ---------------------------------------------------------------


def test_topic_drift_covers_every_month_with_keywords():
    records = [
        _session("p", "s1", "2026-05-06T09:00", [
            ("2026-05-06T09:00", "优化一下数据库查询，加个索引"),
            ("2026-05-06T09:30", "数据库连接池配置也要调"),
        ]),
        _session("p", "s2", "2026-06-10T09:00", [
            ("2026-06-10T09:00", "把路由拆成蓝图，再写部署脚本"),
            ("2026-06-10T09:30", "部署到测试环境跑一遍"),
        ]),
    ]
    report = compute_yearbook(records)
    assert set(report.topic_drift) == {"2026-05", "2026-06"}
    for kws in report.topic_drift.values():
        assert kws and len(kws) <= 8


def test_records_without_user_messages_are_rejected():
    with pytest.raises(ValueError):
        compute_yearbook([])


# -- card specs + rendering -----------------------------------------------------


def test_build_card_specs_binds_copy_and_payload():
    report = compute_yearbook([claude_code.parse_session_file(SAMPLE)])
    keys = ["hero", "correction", "complaints", "projects", "topics", "closing"]
    for lang in ("zh", "en"):
        specs = cards.build_card_specs(report, lang)
        assert [s.key for s in specs] == keys
        assert all(s.title and s.headline and s.subline for s in specs)
        assert all(s.data.get("period") for s in specs)
    zh = cards.build_card_specs(report, "zh")
    assert zh[0].headline == "6"  # hero: total typed messages
    assert zh[1].headline == "33%"  # the hero number
    assert zh[1].data["share"] == pytest.approx(2 / 6)
    assert zh[2].data["heatmap"] == [["2026-06", [3, 0, 0, 0, 0]]]
    assert zh[3].data["bars"] == [("api-server", 1)]
    drift = zh[4].data["drift"]
    assert [month for month, _kws in drift] == ["2026-06"]
    assert all(len(kws) <= 3 for _month, kws in drift)
    with pytest.raises(ValueError):
        cards.build_card_specs(report, "ja")


def test_render_card_set_writes_both_ratios(tmp_path):
    try:
        cards.load_font(32)
    except cards.FontNotFoundError:
        pytest.skip("no CJK font available on this machine")
    report = compute_yearbook([claude_code.parse_session_file(SAMPLE)])
    specs = cards.build_card_specs(report, "zh")
    paths = cards.render_card_set(specs, tmp_path, theme="midnight", lang="zh")
    assert len(paths) == 12
    assert {p.name for p in paths} >= {"hero-9x16.png", "hero-1x1.png"}
    from PIL import Image

    for path in paths:
        assert path.is_file()
        with Image.open(path) as img:
            assert img.size in (cards.SIZE_9X16, cards.SIZE_1X1)


def test_font_error_names_candidates_and_flag(monkeypatch):
    monkeypatch.setattr(cards, "FONT_CHAIN", ())
    with pytest.raises(cards.FontNotFoundError) as exc:
        cards.load_font(32)
    assert "--font" in str(exc.value)
