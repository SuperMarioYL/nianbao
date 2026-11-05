# Changelog

## v0.3.0 — 2026-11-06

正确性修复版本：把四个会悄悄算错、或直接让整次运行崩掉的输入问题修掉。

### fix — 统计口径与坏输入

- 「助手回复」改为按 `message.id` 去重。Claude Code 把一次回复拆成 thinking / text / tool_use 多条 JSONL 记录，此前逐条计数，真实日志上把回复数放大了约 3 倍（本机 244 个真实会话文件：2,066 条记录 vs 721 条真实回复）
- 单条畸形记录不再让整次运行崩掉：时间戳是数字、`message` 是字符串、`cwd` 不是字符串时，此前会抛出未捕获的 `AttributeError` / `TypeError`；现在与解析失败的 JSON 行一样跳过
- 缺时间戳的消息按文件自身的时间线补日期，不再用「现在」：首条消息没有时间戳时，此前会给整份年报塞进一个当月会话（2025-03 的对话被算成 2025-03-01 → 2026-11-06，614 天）
- 卡片行文案改为按像素宽度截断：CJK 字符宽度约为西文的两倍，此前按字符数截断，9 个汉字的项目名会压在进度条上；话题行的关键词也不再跑出画布

### quality — 版本一致性

- `VERSION` / `pyproject.toml` / `nianbao.__version__` / `uv.lock` / 两个 README 徽章 / `web/site.json` 统一到 0.3.0，并新增 `tests/test_version_lockstep.py` 防止再次漂移

## v0.2.0 — 2026-10-09

正确性修复版本：所有日历型指标改按你本机的日历归属，不再被日志里的 UTC 时间戳带偏。

### fix — 本机日历与时间戳

- 吐槽热力图、「火力最猛的一周」、话题漂移改按机器本地时区的日历归属。此前按日志内的 UTC 时间戳分桶，对 UTC+8 用户，每天 16:00 之后的会话都会被记到错误的日 / 周 / 月
- 修复混合时区日志导致的崩溃：一个目录里同时放带时区与不带时区时间戳的 chat 导出（或单文件首条消息缺时间戳）时，统计层会抛出未捕获的 `TypeError`；现在所有时间戳在统计边界统一归一化，不再崩溃
- 修复话题卡片标题渲染：某个月的消息全被分词过滤成零关键词时，标题不再渲染出「」

## v0.1.0 — 2026-09-08

首个公开版本：把本地 Coding Agent 会话日志，变成可分享的「AI 协作年报」。

### m1 — 指标计算

- Claude Code JSONL 适配器（`~/.claude/projects/**/*.jsonl`）：只统计人类真正输入的消息，过滤 sidechain、meta、`tool_result` 与 harness 注入的伪用户消息
- 中英双语纠正 / 吐槽词典（纠正四类：negation / redo / clarify / revert；吐槽 severity 1–3），纯文本可审计
- 纠正率、吐槽计数、按月×周的吐槽热力图与「火力最猛的一周」、项目编年（首次出现 / 最近一次 / 存活天数）
- jieba TF-IDF 月度关键词与话题漂移
- rich TUI 终端年报摘要

### m2 — 卡片渲染

- Pillow 渲染 6 张卡片 × 2 种比例（9:16 1080×1920 / 1:1 1080×1080），共 12 张 PNG 写入 `./nianbao-out/`
- 卡片文案中英双语（`--lang zh|en`），三套配色（`--theme midnight|aurora|sunset`）
- CJK 字体回退链（macOS Hiragino Sans GB / STHeiti）+ `--font` 显式覆盖，找不到字体时报错列出全部候选路径
- 每张卡片页脚带「由 Nianbao 生成」署名

### m3 — 打磨与发布

- ZCode / GLM CLI model-io 日志适配器：`request.messages` 累积数组去重重建，full / tail / delta 窗口都能拼回一个会话，subagent 文件跳过
- 通用 chat JSONL 适配器（每行一条 `{role, content, timestamp?}`）；格式按文件自动嗅探，同一目录可混放
- `--demo`：用内置示例会话跑完整流程，没有本地日志也能试用
- asciinema 演示录制（`assets/demo.cast`）与示例卡片（`assets/sample-card-*.png`）
- PyPI 打包（hatchling；fixtures 随 wheel 分发，装完即 `nianbao --demo`）
