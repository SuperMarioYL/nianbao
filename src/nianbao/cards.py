"""Pillow renderer for the shareable yearbook card set.

One card = one :class:`~nianbao.schema.CardSpec` (metric + layout + copy
binding, the product's second owned primitive) drawn as a 网易云-style dark
gradient at two aspect ratios: 9:16 (1080x1920, for 朋友圈/即刻 full-screen
posts) and 1:1 (1080x1080, for grid posts). Copy ships in zh and en; the
attribution footer rides every card — the card is the ad.

CJK font selection walks the fallback chain verified loadable by Pillow on
this machine (Hiragino Sans GB → STHeiti Medium → STHeiti Light); an explicit
override path is tried before the chain, and if nothing loads the error names
every candidate and how to fix it. PingFang is deliberately absent:
``/System/Library/Fonts/PingFang.ttc`` does not exist on this macOS and the
framework-reserved PingFangUI.ttc copy cannot be opened by Pillow.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .schema import CardSpec, YearbookReport
from .themes import DEFAULT_THEME, Theme, get_theme

#: Tried in order (after any explicit override) when loading card fonts.
FONT_CHAIN: tuple[str, ...] = (
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
)

SIZE_9X16 = (1080, 1920)
SIZE_1X1 = (1080, 1080)
RATIOS: tuple[tuple[str, tuple[int, int]]] = (("9x16", SIZE_9X16), ("1x1", SIZE_1X1))

MARGIN = 120

#: Vertical anchor positions (fractions of card height) per aspect ratio.
_ANCHORS = {
    "9x16": {
        "brand": 0.050, "title": 0.100, "bar": 0.148, "head": 0.185,
        "sub": 0.300, "viz_top": 0.360, "viz_bottom": 0.860, "foot": 0.940,
        "head_scale": 1.0,
    },
    "1x1": {
        "brand": 0.055, "title": 0.100, "bar": 0.155, "head": 0.190,
        "sub": 0.340, "viz_top": 0.410, "viz_bottom": 0.840, "foot": 0.940,
        "head_scale": 0.75,
    },
}

#: Base headline font size per card key (at 1080px width, 9:16).
_HEADLINE_SIZE = {
    "hero": 176,
    "correction": 190,
    "complaints": 150,
    "projects": 120,
    "topics": 104,
    "closing": 120,
}

_COPY = {
    "zh": {
        "hero_title": "AI 协作年报",
        "hero_sub": "条消息 · {sessions} 个会话 · {projects} 个项目",
        "corr_title": "纠正时刻",
        "corr_sub": "你发出的消息里，{count} 条是在把它拉回正轨",
        "comp_title": "吐槽热度",
        "comp_head": "{count} 次",
        "comp_sub": "火力最猛的一周：{worst}",
        "comp_sub_zero": "这一年你没跟 AI 红过脸",
        "proj_title": "项目编年",
        "proj_head": "{count} 个项目",
        "proj_sub": "陪你最久的是「{name}」· {days} 天",
        "top_title": "话题迁徙",
        "top_sub": "{months} 个月的关键词足迹",
        "close_title": "写在最后",
        "close_head": "明年见",
        "close_sub": "纠偏 {corr} 次 · 吐槽 {comp} 次 · 消息 {msgs} 条 — 都记下了",
        "footer": "{label} · 由 Nianbao 生成",
    },
    "en": {
        "hero_title": "AI COLLAB YEARBOOK",
        "hero_sub": "messages · {sessions} sessions · {projects} projects",
        "corr_title": "COURSE CORRECTIONS",
        "corr_sub": "{count} messages steering the agent back on track",
        "comp_title": "COMPLAINT HEAT",
        "comp_head": "{count}x",
        "comp_sub": "worst week: {worst}",
        "comp_sub_zero": "you never lost your temper with your agents",
        "proj_title": "PROJECT SURVIVAL",
        "proj_head": "{count} projects",
        "proj_sub": "longest-lived: {name} · {days} days",
        "top_title": "TOPIC DRIFT",
        "top_sub": "keyword footprints across {months} months",
        "close_title": "EPILOGUE",
        "close_head": "See you next year",
        "close_sub": "{corr} corrections · {comp} complaints · {msgs} messages — all counted",
        "footer": "{label} · Made with Nianbao",
    },
}


class FontNotFoundError(RuntimeError):
    """No loadable CJK font for card rendering — names the candidates tried."""


def _resolve_font_path(override: str | Path | None = None) -> str:
    """First loadable path in the override + system fallback chain.

    Single owner of the chain walk and its error message — :func:`load_font`
    and :class:`CardRenderer` both resolve fonts through here.
    """
    candidates = [str(override)] if override else []
    candidates += list(FONT_CHAIN)
    for path in candidates:
        try:
            ImageFont.truetype(path, 16)
            return path
        except OSError:
            continue
    raise FontNotFoundError(
        "no loadable CJK font for card rendering.\n"
        "Tried:\n  " + "\n  ".join(f"- {p}" for p in candidates) + "\n"
        "Install a CJK font (e.g. Noto Sans CJK SC) and pass it with --font."
    )


def load_font(size: int, override: str | Path | None = None) -> ImageFont.FreeTypeFont:
    """Load a font at ``size``, walking the override + system fallback chain."""
    return ImageFont.truetype(_resolve_font_path(override), size)


def _lerp(c1: tuple, c2: tuple, t: float) -> tuple:
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + "…"


def _period_label(report: YearbookReport) -> str:
    if report.period_start.year == report.period_end.year:
        return str(report.period_start.year)
    return f"{report.period_start.year}–{report.period_end.year}"


def _worst_week_label(worst: tuple, lang: str) -> str:
    month, week = worst[0], worst[1]
    if lang == "zh":
        return f"{month[:4]}年{int(month[5:])}月 第{week + 1}周"
    return f"{month} W{week + 1}"


def _topics_headline(drift: dict[str, list[str]], lang: str) -> str:
    # A month can carry an empty keyword list (messages that tokenize to
    # nothing) — quoting it would render 「」 on the card, so drop it first.
    months = [month for month in sorted(drift) if drift[month]]
    if not months:
        return ""
    quote = ("「{k}」" if lang == "zh" else '"{k}"').format

    def top(month: str) -> str:
        kws = drift[month]
        return _truncate(kws[0], 8) if kws else ""

    if len(months) == 1:
        return quote(k=top(months[0]))
    pair = "从「{a}」到「{b}」" if lang == "zh" else 'from "{a}" to "{b}"'
    return pair.format(a=top(months[0]), b=top(months[-1]))


def build_card_specs(report: YearbookReport, lang: str = "zh") -> list[CardSpec]:
    """Bind the report's metrics to card layouts and zh/en copy.

    Six specs ship with v0.1: hero totals, correction rate, complaint
    heatmap, project survival, topic drift, and the closing card.
    """
    if lang not in _COPY:
        raise ValueError(
            f"unsupported card language {lang!r}; expected one of {sorted(_COPY)}"
        )
    c = _COPY[lang]
    period = _period_label(report)
    pct = round(report.correction_rate * 100)
    msgs = f"{report.total_user_messages:,}"
    heatmap = [[month, weights] for month, weights in sorted(report.complaint_heatmap.items())][-12:]
    bars = [(p.project, p.sessions) for p in report.project_survival[:5]]
    drift = [(month, kws[:3]) for month, kws in sorted(report.topic_drift.items())[-6:]]

    if report.worst_week is not None:
        comp_sub = c["comp_sub"].format(worst=_worst_week_label(report.worst_week, lang))
    else:
        comp_sub = c["comp_sub_zero"]

    longest = max(
        report.project_survival,
        key=lambda p: (p.days, p.sessions),
        default=None,
    )
    proj_sub = (
        c["proj_sub"].format(name=_truncate(longest.project, 14), days=longest.days)
        if longest
        else ""
    )

    specs = [
        CardSpec(
            key="hero",
            title=c["hero_title"],
            headline=msgs,
            subline=c["hero_sub"].format(
                sessions=report.total_sessions, projects=report.total_projects
            ),
            data={"period": period},
        ),
        CardSpec(
            key="correction",
            title=c["corr_title"],
            headline=f"{pct}%",
            subline=c["corr_sub"].format(count=report.correction_count),
            data={"period": period, "share": report.correction_rate},
        ),
        CardSpec(
            key="complaints",
            title=c["comp_title"],
            headline=c["comp_head"].format(count=report.complaint_count),
            subline=comp_sub,
            data={"period": period, "heatmap": heatmap},
        ),
        CardSpec(
            key="projects",
            title=c["proj_title"],
            headline=c["proj_head"].format(count=report.total_projects),
            subline=proj_sub,
            data={"period": period, "bars": bars},
        ),
        CardSpec(
            key="topics",
            title=c["top_title"],
            headline=_topics_headline(report.topic_drift, lang),
            subline=c["top_sub"].format(months=len(report.topic_drift)),
            data={"period": period, "drift": drift},
        ),
        CardSpec(
            key="closing",
            title=c["close_title"],
            headline=c["close_head"],
            subline=c["close_sub"].format(
                corr=report.correction_count,
                comp=report.complaint_count,
                msgs=msgs,
            ),
            data={"period": period},
        ),
    ]
    return specs


class CardRenderer:
    """Renders CardSpecs as PNG images; resolves the font chain once."""

    def __init__(self, theme: Theme, *, lang: str = "zh", font_path=None):
        self.theme = theme
        self.lang = lang
        self._font_path = _resolve_font_path(font_path)
        self._cache: dict[int, ImageFont.FreeTypeFont] = {}

    def _font(self, size: int) -> ImageFont.FreeTypeFont:
        if size not in self._cache:
            self._cache[size] = ImageFont.truetype(self._font_path, size)
        return self._cache[size]

    def _fit_size(self, text: str, base: int, max_width: int, floor: int = 40) -> int:
        size = base
        while size > floor and self._font(size).getlength(text) > max_width:
            size -= 6
        return size

    def _gradient(self, width: int, height: int) -> Image.Image:
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)
        top, bottom = self.theme.bg_top, self.theme.bg_bottom
        for y in range(height):
            t = y / max(height - 1, 1)
            draw.line([(0, y), (width, y)], fill=_lerp(top, bottom, t))
        return img

    def render(self, spec: CardSpec, size: tuple[int, int] = SIZE_9X16) -> Image.Image:
        """Draw one card spec at the given canvas size."""
        width, height = size
        ratio = "9x16" if height > width else "1x1"
        a = _ANCHORS[ratio]
        theme = self.theme
        img = self._gradient(width, height)
        draw = ImageDraw.Draw(img)
        max_w = width - MARGIN * 2
        y = lambda key: int(a[key] * height)  # noqa: E731

        # Brand row, title, accent tick, headline, subline — the shared spine.
        draw.text(
            (width / 2, y("brand")),
            f"NIANBAO · {spec.data.get('period', '')}".strip(" ·"),
            font=self._font(34), fill=theme.text_dim, anchor="ma",
        )
        title_size = self._fit_size(spec.title, 54, max_w, floor=34)
        draw.text(
            (width / 2, y("title")), spec.title,
            font=self._font(title_size), fill=theme.text, anchor="ma",
        )
        draw.rounded_rectangle(
            [width / 2 - 36, y("bar"), width / 2 + 36, y("bar") + 8],
            radius=4, fill=theme.accent,
        )
        head_size = self._fit_size(
            spec.headline,
            int(_HEADLINE_SIZE.get(spec.key, 140) * a["head_scale"]),
            max_w,
        )
        draw.text(
            (width / 2, y("head")), spec.headline,
            font=self._font(head_size), fill=theme.accent_soft, anchor="ma",
        )
        sub_size = self._fit_size(spec.subline, 42, max_w, floor=28)
        draw.text(
            (width / 2, y("sub")), spec.subline,
            font=self._font(sub_size), fill=theme.text_dim, anchor="ma",
        )

        # Metric payload.
        region = (MARGIN, y("viz_top"), width - MARGIN, y("viz_bottom"))
        if spec.key == "correction":
            self._draw_share_bar(draw, spec.data.get("share", 0.0), region)
        elif spec.key == "complaints":
            self._draw_heatmap(draw, spec.data.get("heatmap", []), region)
        elif spec.key == "projects":
            self._draw_bars(draw, spec.data.get("bars", []), region)
        elif spec.key == "topics":
            self._draw_drift(draw, spec.data.get("drift", []), region)

        footer = _COPY[self.lang]["footer"].format(label=theme.label)
        draw.text(
            (width / 2, y("foot")), footer,
            font=self._font(30), fill=theme.text_dim, anchor="ma",
        )
        return img

    # -- metric payloads ---------------------------------------------------

    @staticmethod
    def _v_center(y0: int, y1: int, n_rows: int, row_h: int, gap: int) -> int:
        """Top y of an n-row block centered inside [y0, y1] (sparse rows)."""
        block_h = n_rows * row_h + (n_rows - 1) * gap
        return y0 + max(0, (y1 - y0 - block_h) // 2)

    def _draw_share_bar(self, draw: ImageDraw.ImageDraw, share: float, region) -> None:
        x0, y0, x1, y1 = region
        cy = (y0 + y1) // 2
        bar_h = 18
        draw.rounded_rectangle(
            [x0, cy - bar_h // 2, x1, cy + bar_h // 2],
            radius=bar_h // 2, fill=self.theme.heat_low,
        )
        fill_w = int((x1 - x0) * min(max(share, 0.0), 1.0))
        if fill_w > bar_h:
            draw.rounded_rectangle(
                [x0, cy - bar_h // 2, x0 + fill_w, cy + bar_h // 2],
                radius=bar_h // 2, fill=self.theme.accent,
            )

    def _draw_heatmap(self, draw: ImageDraw.ImageDraw, rows: list, region) -> None:
        if not rows:
            return
        x0, y0, x1, y1 = region
        label_w = 190
        gap = 12
        cells = 5
        cell_w = (x1 - x0 - label_w - gap * (cells - 1)) // cells
        row_h = min(74, (y1 - y0) // len(rows) - gap)
        if row_h < 24 or cell_w < 24:
            return
        y0 = self._v_center(y0, y1, len(rows), row_h, gap)
        max_weight = max(max(weights) for _month, weights in rows) or 1.0
        label_font = self._font(30)
        for r, (month, weights) in enumerate(rows):
            cy = y0 + r * (row_h + gap)
            draw.text(
                (x0, cy + row_h // 2), month,
                font=label_font, fill=self.theme.text_dim, anchor="lm",
            )
            for c, weight in enumerate(weights[:cells]):
                cx = x0 + label_w + c * (cell_w + gap)
                t = weight / max_weight if weight > 0 else 0.0
                draw.rounded_rectangle(
                    [cx, cy, cx + cell_w, cy + row_h], radius=10,
                    fill=_lerp(self.theme.heat_low, self.theme.heat_high, t),
                )

    def _draw_bars(self, draw: ImageDraw.ImageDraw, rows: list, region) -> None:
        if not rows:
            return
        x0, y0, x1, y1 = region
        rows = rows[: max(1, (y1 - y0) // 86)]
        gap = 14
        row_h = min(72, (y1 - y0) // len(rows) - gap)
        if row_h < 24:
            return
        y0 = self._v_center(y0, y1, len(rows), row_h, gap)
        name_w = 330
        num_w = 90
        track_x = x0 + name_w + 20
        track_end = x1 - num_w
        max_count = max(count for _name, count in rows) or 1
        name_font = self._font(34)
        num_font = self._font(30)
        for r, (name, count) in enumerate(rows):
            cy = y0 + r * (row_h + gap)
            mid = cy + row_h // 2
            draw.text(
                (x0, mid), _truncate(name, 9),
                font=name_font, fill=self.theme.text, anchor="lm",
            )
            draw.rounded_rectangle(
                [track_x, mid - 8, track_end, mid + 8], radius=8,
                fill=self.theme.heat_low,
            )
            fill_w = int((track_end - track_x) * count / max_count)
            if fill_w > 16:
                draw.rounded_rectangle(
                    [track_x, mid - 8, track_x + fill_w, mid + 8], radius=8,
                    fill=self.theme.accent_soft,
                )
            draw.text(
                (x1, mid), str(count),
                font=num_font, fill=self.theme.text_dim, anchor="rm",
            )

    def _draw_drift(self, draw: ImageDraw.ImageDraw, rows: list, region) -> None:
        if not rows:
            return
        x0, y0, x1, y1 = region
        rows = rows[: max(1, (y1 - y0) // 62)]
        row_h = 34
        gap = 20
        y0 = self._v_center(y0, y1, len(rows), row_h, gap)
        month_font = self._font(30)
        kw_font = self._font(30)
        for r, (month, kws) in enumerate(rows):
            cy = y0 + r * (row_h + gap)
            draw.text(
                (x0, cy), month,
                font=month_font, fill=self.theme.accent_soft, anchor="la",
            )
            draw.text(
                (x0 + 200, cy), " · ".join(kws),
                font=kw_font, fill=self.theme.text_dim, anchor="la",
            )


def render_card_set(
    specs: list[CardSpec],
    out_dir: str | Path,
    *,
    theme: str | Theme | None = None,
    lang: str = "zh",
    font_path: str | Path | None = None,
) -> list[Path]:
    """Render every spec at both aspect ratios into ``out_dir``.

    Returns the written paths, e.g. ``hero-9x16.png`` and ``hero-1x1.png``.
    """
    if not isinstance(theme, Theme):
        theme = get_theme(theme or DEFAULT_THEME)
    renderer = CardRenderer(theme, lang=lang, font_path=font_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for spec in specs:
        for ratio, size in RATIOS:
            path = out_dir / f"{spec.key}-{ratio}.png"
            renderer.render(spec, size).save(path)
            paths.append(path)
    return paths
