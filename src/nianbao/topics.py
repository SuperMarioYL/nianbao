"""Topic extraction: jieba tokenization + TF-IDF keyword scoring.

Used for per-session topics and for the month-by-month topic drift. Purely
lexicon/TF-IDF based — no models, no embeddings, no network.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter

import jieba

# Silence jieba's "Building prefix dict ..." chatter so the CLI stays clean.
jieba.setLogLevel(logging.WARNING)

_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]+|[0-9A-Za-z#@./_-]+")

_ZH_STOPWORDS = frozenset(
    """
    的 了 是 在 我 你 他 她 它 我们 你们 他们 她们 它们 这 那 这个 那个 这些 那些
    和 与 及 跟 或者 还是 就 都 也 而 并 并且 或者 如果 那么 因为 所以 但是 可是
    一个 一些 一下 一样 没有 不是 什么 怎么 怎样 为什么 哪 哪个 哪些 谁 多少
    会 能 可以 要 想 需要 觉得 知道 说 看 做 用 给 对 从 到 被 把 让 使
    吧 吗 呢 啊 呀 哦 嗯 哈 呵 唉 好的 好吧 现在 然后 之后 以前 时候 地方 问题
    东西 事情 情况 方式 方法 部分 内容 直接 基本 应该 可能 已经 开始 继续 进行
    谢谢 请 帮 帮忙 一下 再 又 还 只 光 每 各 别 另外 其他 其它 以及 比如 例如
    code claude gpt glm ai ok okay yes no the and for you are was were this that
    with have has had will would could should about into from your our their
    what which when where does did doing been being them they then than more
    some just like want need make made use used using file files line lines
    here there only very much many also
    """.split()
    + [
        "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
        "不", "了", "个", "人", "上", "下", "中", "大", "小", "到", "说", "要",
        "go", "do", "if", "it", "is", "as", "at", "by", "of", "on", "or", "be",
    ]
)


def tokenize(text: str) -> list[str]:
    """Segment text with jieba and keep meaningful keyword tokens.

    Keeps CJK runs of length >= 2 and ASCII words of length >= 3, dropping
    stopwords and bare numbers.
    """
    tokens: list[str] = []
    for raw in jieba.cut(text):
        token = raw.strip().lower()
        if not token:
            continue
        for part in _TOKEN_RE.findall(token):
            part = part.strip(".-_/@#").lower()
            if not part or part in _ZH_STOPWORDS:
                continue
            if part.isdigit():
                continue
            has_cjk = any("\u4e00" <= ch <= "\u9fff" for ch in part)
            if has_cjk:
                if len(part) >= 2:
                    tokens.append(part)
            elif len(part) >= 3:
                tokens.append(part)
    return tokens


def extract_keywords(docs: dict[str, str], top_n: int = 8) -> dict[str, list[str]]:
    """TF-IDF top keywords per labeled document group.

    ``docs`` maps a group key (session id or "YYYY-MM") to its concatenated
    text. Scoring is standard smoothed TF-IDF across the groups; ties break
    alphabetically so output is deterministic.
    """
    if not docs:
        return {}
    tokenized = {key: tokenize(text) for key, text in docs.items()}
    n_docs = len(tokenized)
    df: Counter[str] = Counter()
    for counts in (Counter(tokens) for tokens in tokenized.values()):
        df.update(counts.keys())

    result: dict[str, list[str]] = {}
    for key, tokens in tokenized.items():
        tf = Counter(tokens)
        scored = [
            (count * (math.log((n_docs + 1) / (1 + df[term])) + 1.0), term)
            for term, count in tf.items()
        ]
        scored.sort(key=lambda item: (-item[0], item[1]))
        result[key] = [term for _score, term in scored[:top_n]]
    return result
