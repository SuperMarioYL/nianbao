"""Command-line interface — argument parsing and orchestration only.

The bare ``nianbao`` invocation runs the plan's minimum happy path end to
end: discover logs → parse with a progress bar → print the rich TUI summary →
render the PNG card set into ``./nianbao-out/``. The ``summary`` and ``cards``
subcommands run the individual stages (m1 / m2) on their own.
"""

from __future__ import annotations

import importlib.resources
import sys
from pathlib import Path
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table

from .adapters import parse_file
from .cards import FontNotFoundError, build_card_specs, render_card_set
from .metrics import compute_yearbook
from .schema import YearbookReport
from .themes import DEFAULT_THEME, THEMES

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    help=(
        "把本地 Coding Agent 会话日志，变成能晒的「AI 协作年报」。"
        " / Turn local coding-agent session logs into a shareable yearbook."
    ),
)
console = Console()

DEFAULT_LOGS_DIR = Path.home() / ".claude" / "projects"
DEFAULT_OUT_DIR = Path("nianbao-out")
DEMO_FIXTURE = "sample_session.jsonl"

_ACCENT = "#e13e3e"


def _fail(message: str) -> None:
    console.print(f"[bold {_ACCENT}]错误：[/]{message}")
    raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def run(
    ctx: typer.Context,
    logs_dir: Optional[Path] = typer.Option(
        None, "--logs-dir",
        help="要扫描的会话日志目录（默认 ~/.claude/projects；格式自动识别，可混放）。",
    ),
    lang: str = typer.Option("zh", "--lang", help="卡片文案语言：zh 或 en。"),
    theme: str = typer.Option(
        DEFAULT_THEME, "--theme", help=f"卡片配色：{'/'.join(THEMES)}。",
    ),
    font: Optional[Path] = typer.Option(
        None, "--font", help="指定 CJK 字体文件（.ttf/.ttc），覆盖内置字体链。",
    ),
    out_dir: Path = typer.Option(
        DEFAULT_OUT_DIR, "--out-dir", help="卡片输出目录。",
    ),
    demo: bool = typer.Option(
        False, "--demo", help="用内置示例会话数据跑完整流程（无需本地日志）。",
    ),
) -> None:
    """完整流程：解析日志 → 年报摘要 → 生成可分享的 PNG 卡片。"""
    if ctx.invoked_subcommand is not None:
        return
    report = _load_report(logs_dir, demo)
    _print_summary(report)
    _render_cards(report, lang=lang, theme=theme, font=font, out_dir=out_dir)


@app.command()
def summary(
    logs_dir: Optional[Path] = typer.Option(
        None, "--logs-dir", help="要扫描的会话日志目录（默认 ~/.claude/projects）。",
    ),
    demo: bool = typer.Option(False, "--demo", help="用内置示例会话数据。"),
) -> None:
    """只打印终端年报摘要（m1 指标，不生成卡片）。"""
    _print_summary(_load_report(logs_dir, demo))


@app.command()
def cards(
    logs_dir: Optional[Path] = typer.Option(
        None, "--logs-dir", help="要扫描的会话日志目录（默认 ~/.claude/projects）。",
    ),
    lang: str = typer.Option("zh", "--lang", help="卡片文案语言：zh 或 en。"),
    theme: str = typer.Option(
        DEFAULT_THEME, "--theme", help=f"卡片配色：{'/'.join(THEMES)}。",
    ),
    font: Optional[Path] = typer.Option(
        None, "--font", help="指定 CJK 字体文件（.ttf/.ttc），覆盖内置字体链。",
    ),
    out_dir: Path = typer.Option(DEFAULT_OUT_DIR, "--out-dir", help="卡片输出目录。"),
    demo: bool = typer.Option(False, "--demo", help="用内置示例会话数据。"),
) -> None:
    """只生成可分享的 PNG 卡片组（9:16 + 1:1，m2）。"""
    report = _load_report(logs_dir, demo)
    _render_cards(report, lang=lang, theme=theme, font=font, out_dir=out_dir)


# -- pipeline ---------------------------------------------------------------


def _resolve_logs_dir(logs_dir: Optional[Path], demo: bool) -> Path:
    if not demo:
        return logs_dir or DEFAULT_LOGS_DIR
    fixture = _demo_fixture_dir()
    if fixture is None:
        _fail("找不到内置示例日志——请在仓库内运行，或安装带 fixtures 的包。")
    console.print("[dim]--demo：使用内置示例会话数据[/]")
    return fixture


def _demo_fixture_dir() -> Optional[Path]:
    """Bundled demo logs: wheel copy first, repo checkout second."""
    try:
        bundled = importlib.resources.files("nianbao").joinpath("fixtures")
        if (bundled / DEMO_FIXTURE).is_file():
            return Path(str(bundled))
    except (ModuleNotFoundError, FileNotFoundError, TypeError):
        pass
    repo = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
    if (repo / DEMO_FIXTURE).is_file():
        return repo
    return None


def _load_report(logs_dir: Optional[Path], demo: bool) -> YearbookReport:
    root = _resolve_logs_dir(logs_dir, demo)
    files = sorted(root.rglob("*.jsonl")) if root.is_dir() else []
    if not files:
        _fail(
            f"在 {root} 下没有找到 .jsonl 会话日志。\n"
            "用 --logs-dir 指向你的 Agent 日志目录，或先 --demo 看示例。"
        )

    records = []
    with Progress(
        TextColumn("{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("解析会话日志", total=len(files))
        for path in files:
            record = parse_file(path)
            if record is not None:
                records.append(record)
            progress.advance(task)

    if not records:
        _fail(f"{root} 下没有解析出包含用户消息的会话。")
    try:
        return compute_yearbook(records)
    except ValueError as err:
        _fail(str(err))


def _print_summary(report: YearbookReport) -> None:
    period = f"{report.period_start:%Y-%m-%d} → {report.period_end:%Y-%m-%d}"
    console.print()
    console.print(
        Panel.fit(
            f"[bold]Nianbao · AI 协作年报[/]\n[dim]{period} · {report.period_days} 天[/]",
            border_style=_ACCENT,
        )
    )

    totals = Table(box=box.SIMPLE, expand=False)
    totals.add_column("会话", justify="right")
    totals.add_column("你发出的消息", justify="right")
    totals.add_column("助手回复", justify="right")
    totals.add_column("项目", justify="right")
    totals.add_row(
        f"{report.total_sessions:,}",
        f"{report.total_user_messages:,}",
        f"{report.total_assistant_messages:,}",
        f"{report.total_projects:,}",
    )
    console.print(totals)

    console.print(
        Panel(
            f"[bold][{_ACCENT}]{report.correction_rate * 100:.0f}%[/][/] "
            f"的消息是在纠正它 —— {report.correction_count} 次纠偏"
        )
    )

    if report.worst_week is not None:
        month, week, weight, count = report.worst_week
        worst = (
            f"吐槽 {report.complaint_count} 次 · "
            f"火力最猛的一周 {month[:4]}年{int(month[5:])}月 第{week + 1}周"
            f"（强度 {weight:g} · {count} 条）"
        )
    else:
        worst = "一次吐槽都没有，脾气真好"
    console.print(Panel(worst))

    if report.project_survival:
        projects = Table(box=box.SIMPLE, expand=False)
        projects.add_column("项目")
        projects.add_column("会话", justify="right")
        projects.add_column("首次出现", justify="right")
        projects.add_column("最近一次", justify="right")
        projects.add_column("存活", justify="right")
        for p in report.project_survival[:5]:
            projects.add_row(
                p.project,
                str(p.sessions),
                f"{p.first_seen:%Y-%m-%d}",
                f"{p.last_seen:%Y-%m-%d}",
                f"{p.days} 天",
            )
        console.print(projects)

    if report.topic_drift:
        drift = Table(box=None, expand=False, show_header=False)
        drift.add_column("月份", style=_ACCENT, justify="right")
        drift.add_column("关键词")
        for month, kws in report.topic_drift.items():
            drift.add_row(month, " · ".join(kws) if kws else "—")
        console.print(drift)
    console.print()


def _render_cards(
    report: YearbookReport,
    *,
    lang: str,
    theme: str,
    font: Optional[Path],
    out_dir: Path,
) -> None:
    if lang not in ("zh", "en"):
        _fail(f"--lang 只支持 zh 或 en，收到 {lang!r}。")
    if theme not in THEMES:
        _fail(f"--theme 只支持 {'/'.join(THEMES)}，收到 {theme!r}。")
    try:
        report.cards = build_card_specs(report, lang)
        paths = render_card_set(
            report.cards, out_dir, theme=theme, lang=lang, font_path=font
        )
    except FontNotFoundError as err:
        _fail(str(err))

    opener = "open" if sys.platform == "darwin" else "xdg-open"
    console.print()
    console.print(
        Panel.fit(
            f"[bold]{len(report.cards)} 张卡片 × 2 种比例已写入 "
            f"[{_ACCENT}]{out_dir}[/][/]（共 {len(paths)} 个 PNG）\n"
            f"[dim]预览：{opener} {out_dir}[/]",
            border_style=_ACCENT,
        )
    )


if __name__ == "__main__":
    app()
