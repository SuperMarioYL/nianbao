[English](./README.en.md) | **简体中文**

<div align="center">

<img src="https://readme-typing-svg.demolab.com/?font=Fira+Code&weight=600&size=26&pause=1600&color=E13E3E&center=true&vCenter=true&random=false&width=720&lines=nianbao+--demo;%E2%86%92+33%25+%E7%9A%84%E6%B6%88%E6%81%AF%E6%98%AF%E5%9C%A8%E7%BA%A0%E6%AD%A3%E5%AE%83;12+%E5%BC%A0%E5%8D%A1%E7%89%87+%E2%86%92+.%2Fnianbao-out%2F" alt="nianbao --demo → 33% 的消息是在纠正它 → 12 张卡片 → ./nianbao-out/">

# Nianbao · AI 协作年报

一年下来，你和 Claude Code 说过的每句话都躺在本地日志里。Nianbao 把这些
Coding Agent 会话记录挖出来，算出你的纠正率、吐槽热度和话题漂移，生成一张能晒的「AI 协作年报」。

[![CI](https://github.com/SuperMarioYL/nianbao/actions/workflows/ci.yml/badge.svg)](https://github.com/SuperMarioYL/nianbao/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-0.1.0-e13e3e)](https://github.com/SuperMarioYL/nianbao/releases)
[![Python](https://img.shields.io/badge/python-3.12%2B-3776ab)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-e13e3e)](./LICENSE)
![Offline](https://img.shields.io/badge/100%25_offline-%E6%9C%AC%E5%9C%B0%E8%BF%90%E8%A1%8C-e13e3e)

<p>
  <img src="assets/sample-card-9x16.png" width="252" alt="示例年报卡片（9:16）：33% 的消息是在纠正它">
  <img src="assets/sample-card-1x1.png" width="252" alt="示例年报卡片（1:1）：33% 的消息是在纠正它">
</p>

<sub>真实渲染输出 · 内置示例数据（<code>--demo</code>）· Midnight 主题</sub>

</div>

---

## <img src="assets/icons/rocket.svg" width="22" alt=""> 快速开始

前置：Python 3.12+ 和 [uv](https://docs.astral.sh/uv/)。

```bash
# 30 秒试用：内置示例会话数据，不需要本地日志
uvx nianbao --demo

# 跑你自己的历史：默认读 ~/.claude/projects，全程只读
uvx nianbao
```

`nianbao` 会依次：解析日志（带进度条）→ 在终端打印年报摘要 → 把 12 张 PNG 写进 `./nianbao-out/`。

没有 uv 的话：`pip install nianbao`，然后 `nianbao --demo`。
想从源码跑：`git clone https://github.com/SuperMarioYL/nianbao && cd nianbao`，然后 `uvx --from . nianbao --demo`（或 `uv run nianbao --demo`）。

用的是其他 Coding Agent 的日志？指定目录即可，格式自动识别、可以混放：

```bash
uvx nianbao --logs-dir ~/.zcode/cli/rollout   # ZCode / GLM CLI
```

## <img src="assets/icons/video.svg" width="22" alt=""> 演示

终端录制（asciinema v2 格式，时长约 3 秒，`nianbao --demo` 的真实输出）：

```bash
asciinema play assets/demo.cast
```

录制文件：[assets/demo.cast](assets/demo.cast)（浏览器里可用 [asciinema 播放器](https://docs.asciinema.org/manual/player/)打开）

同一次运行的终端输出（内置示例数据）：

```text
--demo：使用内置示例会话数据
解析会话日志 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1/1 0:00:00

╭────────────────────────────────╮
│ Nianbao · AI 协作年报          │
│ 2026-06-03 → 2026-06-03 · 1 天 │
╰────────────────────────────────╯

  会话   你发出的消息   助手回复   项目
 ───────────────────────────────────────
     1              6          8      1

╭──────────────────────────────────────────────────────────────────────────────╮
│ 33% 的消息是在纠正它 —— 2 次纠偏                                             │
╰──────────────────────────────────────────────────────────────────────────────╯
╭──────────────────────────────────────────────────────────────────────────────╮
│ 吐槽 1 次 · 火力最猛的一周 2026年6月 第1周（强度 3 · 1 条）                  │
╰──────────────────────────────────────────────────────────────────────────────╯

  项目         会话     首次出现     最近一次   存活
 ────────────────────────────────────────────────────
  api-server      1   2026-06-03   2026-06-03   0 天

 2026-06  文件 · 测试 · 路由 · app · flask · healthz · 他妈的 · 保留


╭───────────────────────────────────────────────────────╮
│ 6 张卡片 × 2 种比例已写入 nianbao-out（共 12 个 PNG） │
│ 预览：open nianbao-out                                │
╰───────────────────────────────────────────────────────╯
```

示例数据只有一个会话；换成你自己的历史，同样的命令会输出你的数字和 12 张卡片。两张示例卡片见顶部。

## <img src="assets/icons/chart-bar.svg" width="22" alt=""> 年报里有什么

一次运行往 `./nianbao-out/` 写 6 张卡 × 2 种比例（9:16 1080×1920，朋友圈 / 即刻；1:1 1080×1080，九宫格），共 12 张 PNG：

| 卡片 | 算什么 |
| --- | --- |
| 总量 | 你发出的消息总数、会话数、项目数 |
| 纠正时刻 | 纠正率——「不对 / 重新 / 我说的是 / not what I asked」这类消息的占比，配进度条 |
| 吐槽热度 | 吐槽次数、按月×周的热力格、火力最猛的一周 |
| 项目编年 | 项目数、各项目会话数横条、陪你最久的项目和天数 |
| 话题迁徙 | 每月关键词足迹（jieba TF-IDF），看话题从哪漂到哪 |
| 写在最后 | 全年数字回顾：纠偏几次、吐槽几次、一共聊了多少条 |

卡片文案有中英两套（`--lang zh | en`），配色三套（`--theme midnight | aurora | sunset`，见下方配置）。每张卡片的页脚都带「由 Nianbao 生成」——晒图的时候，它自己会说话。

## <img src="assets/icons/bulb.svg" width="22" alt=""> 为什么做 Nianbao

r/ClaudeAI 上有位用户把自己一年的 Claude Code 历史导出来手工数了一遍：10,727 条消息，33% 是纠正或吐槽，其中 895 条是重度的（爆粗、「我从来没让你」）。这个数字谁都好奇，却没有任何产品给你看：

- **提供方只给你看账单**。token 用量、成本、速率限制——「33% 的消息在纠正模型」这种对自己不利的统计，不会出现在任何提供方的年报里。
- **监控工具回答的是另一个问题**。claude-hud、CodexBar 这类实时监控看的是「现在烧到哪了」；Nianbao 看的是「这一年我和 Agent 是怎么协作的」。一个是 meter，一个是 mirror，用的同一批日志。
- **每个好奇的人最后都自己写脚本**。写完一次、发个帖、再也不维护：JSONL 格式各家不同，没有中文的行为词典，产出只是一张截图。

Nianbao 把这条一次性脚本变成维护中的产品：中英双语的纠正 / 吐槽词典（分级、明文可审计）、跨 harness 的日志适配器、可版本化的卡片格式。全部离线，跑在你本机。

## <img src="assets/icons/schema.svg" width="22" alt=""> 工作原理

一个离线 Python 进程，没有服务端、没有网络请求、没有守护进程：

```
~/.claude/projects/**/*.jsonl ─┐
~/.zcode/cli/rollout/*.jsonl  ─┼─▶ adapters（格式嗅探）─▶ SessionRecord[]
通用 chat JSONL（{role,content}）┘                             │
                                                   lexicons（中英词典）
                                                               ▼
                                        metrics + topics（jieba TF-IDF）
                                                               ▼
                                     YearbookReport（纠正率 / 热力 / 编年 / 迁徙）
                                                               ▼
                                           cards + themes（Pillow 渲染）
                                                               ▼
                                                    ./nianbao-out/（12 张 PNG）
```

两个核心数据结构（[`schema.py`](src/nianbao/schema.py)）：

- **`SessionRecord`** — 各家 harness 日志归一化后的会话行为投影：用户消息、纠正（negation / redo / clarify / revert 四类）、吐槽（severity 1–3）、话题关键词。
- **`CardSpec`** — 把一个指标绑定到卡片布局和文案模板，让「可分享的年报卡片」成为可版本化的格式资产，而不是一次性截图。

什么算一次「纠正」、什么算「吐槽」，全部定义在 [`lexicons.py`](src/nianbao/lexicons.py) 的明文词典里——不用读代码也能逐条核对。

## <img src="assets/icons/file-text.svg" width="22" alt=""> 支持的日志格式

| 格式 | 位置 | 说明 |
| --- | --- | --- |
| Claude Code | `~/.claude/projects/**/*.jsonl` | 默认目录；过滤 sidechain、meta、tool_result 和 harness 注入的「伪用户消息」 |
| ZCode / GLM CLI | `~/.zcode/cli/rollout/model-io-sess_*.jsonl` | `request.messages` 累积数组的去重重建，full / tail / delta 窗口都能拼回一个会话；subagent 文件跳过 |
| 通用 chat JSONL | 任意目录 | 每行一个 `{role, content, timestamp?}` 的手工导出 |

格式按文件自动嗅探，`--logs-dir` 指向的目录里可以混放多种格式。其他国产 harness（DeepSeek / Qwen 系 CLI）的本地日志还没有逐一验证——手里有样例的话，欢迎带一段脱敏日志来[提 issue](https://github.com/SuperMarioYL/nianbao/issues)。

## <img src="assets/icons/terminal-2.svg" width="22" alt=""> 命令行

| 命令 | 作用 |
| --- | --- |
| `nianbao` | 完整流程：解析 → 终端摘要 → 生成卡片 |
| `nianbao summary` | 只打印终端年报摘要 |
| `nianbao cards` | 只生成 PNG 卡片组 |

| 选项 | 默认 | 说明 |
| --- | --- | --- |
| `--logs-dir` | `~/.claude/projects` | 会话日志目录，格式自动识别、可混放 |
| `--lang` | `zh` | 卡片文案语言：`zh` / `en` |
| `--theme` | `midnight` | 卡片配色：`midnight` / `aurora` / `sunset` |
| `--font` | 自动 | 指定 CJK 字体文件（.ttf / .ttc），覆盖内置字体链 |
| `--out-dir` | `./nianbao-out` | 卡片输出目录 |
| `--demo` | 关闭 | 用内置示例会话数据跑完整流程 |

## <img src="assets/icons/settings.svg" width="22" alt=""> 配置与限制

- **字体**：macOS 上自动选用 Hiragino Sans GB / STHeiti。Linux 和容器里通常没有这些字体，需要 `--font /path/to/NotoSansCJK-Regular.ttc` 指定一个 CJK 字体；找不到可用字体时，报错信息会列出尝试过的路径和修复方法。
- **统计时段**：年报区间 = 日志里实际最早到最晚的消息时间，不是自然年——刚用两个月，就是一份两个月的年报。
- **语言**：卡片文案目前只有 `zh` / `en`；纠正 / 吐槽词典中英两套同时生效，中英混聊也能测出行为。
- **v0.1 不做**：token / 成本 / 速率的实时监控；Web 界面与托管服务；中英之外的卡片语言。

## <img src="assets/icons/shield-check.svg" width="22" alt=""> 隐私

- **零网络请求**。解析、统计、渲染全部在本机完成——代码里没有一处 HTTP 调用，没有遥测，没有账号系统。
- 日志**只读**。卡片只有你主动发出去的那一刻才离开你的机器。
- 判定规则全部是 [`lexicons.py`](src/nianbao/lexicons.py) 里的明文词典，打开就能逐条核对。

## <img src="assets/icons/credit-card.svg" width="22" alt=""> 付费

个人版（v0.1 的全部功能）免费开源。商业化不在个人侧，在团队侧：

| 方案 | 价格 | 内容 |
| --- | --- | --- |
| 个人版 · 当前 | 免费开源（MIT） | 全部本地功能：解析、指标、12 张卡片、3 套配色、中英双语 |
| **团队年报 · pilot** | ¥2,999 / 团队 / 年（前 3 个设计伙伴，约 $399） | 成员各自本地跑 `nianbao` 导出 YearbookReport JSON，合并成团队 / 项目维度的年报：跨项目纠正率、采用热力图、会话总量。人工 pilot，48 小时内交付 |
| 团队年报 · 自助 | ¥4,999 / 团队 / 年（pilot 之后开放） | 同上，自助流程 |
| 主题包 | ¥19.9（v0.2 起） | 付费卡片主题 |

为什么团队能为它付费：团队 lead 看到成员晒出的个人卡片之后，要的是跨团队的视角——哪些项目在反复返工、Agent 使用集中在谁身上。这正是 v0.1 刻意不做的聚合层，也是 v0.2 的第一个商业功能。

想当设计伙伴：开一个标题带「团队年报 pilot」的 [issue](https://github.com/SuperMarioYL/nianbao/issues)。

## <img src="assets/icons/route.svg" width="22" alt=""> 路线图

- [x] **v0.1（当前）** — Claude Code / ZCode（GLM）/ 通用 chat JSONL 解析；rich TUI 摘要；6 卡 × 2 比例 PNG；中英双语；3 套主题；全离线
- [ ] **v0.2** — 团队年报（pilot → 自助）；付费主题包；更多 harness 适配（欢迎带脱敏样例日志提 issue）
- [ ] **长期** — 多年对比时间线

不做的：Web UI、实时用量监控、把你的日志传到任何服务器。

## <img src="assets/icons/license.svg" width="22" alt=""> 许可证

[MIT](./LICENSE) © 2026 SuperMarioYL

---

<p align="center"><sub><a href="./LICENSE">MIT</a> © 2026 SuperMarioYL</sub></p>
