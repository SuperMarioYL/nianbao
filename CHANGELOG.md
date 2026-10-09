# Changelog

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
