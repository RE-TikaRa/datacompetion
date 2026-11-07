# 项目实施与操作记录

更新时间：2026-11-08
项目：第三届甘肃省大学生数据挖掘挑战赛本科组，AI 应用场景智能挖掘与机会评估系统。

本报告只记录阶段成果、重要数据操作、验证结果和提交。

## 当前状态

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| 赛题与资料准备 | 已完成 | 赛题、官方附件、空模板、公开来源和目录已整理 |
| 项目说明与实现方案 | 已完成 | `README.md`、`PROJECT_MEMORY.md`、`plan.md`、`todo.md` 已建立 |
| 环境和模型连接 | 已完成 | Python 3.14 项目环境；本机 Codex Responses 模型连接检查成功 |
| 多语言向量模型 | 已完成 | 多语言 E5 small ONNX 权重已下载，接口和中英相似性样例已验证 |
| 可复用采集模块 | 已完成 | 来源适配器已移入 `opportunity/collection.py`，`scripts/collect_data.py` 保留为命令行入口 |
| 清洗和 result1 | 已完成 | B01 已生成独立运行目录、官方 CSV、正文快照、记录关系和清洗报告 |
| 机会判断模块 | 自动判别完成，人工复核待做 | 2,561 条已生成 result2，269 条模型候选机会，509 条复核队列 |
| 候选主题和评分 | 已生成候选结果 | 269 条模型正例形成 46 个候选主题；聚类分离较弱，不能当作正式结果 |
| 机会判断至提交材料 | 未完成 | 人工复核、正式 `result3`、`result4`、界面和论文尚未生成 |

当前提交为 `a593822 feat: split invalid judgement batches`。未推送。任务一和任务二自动判别代码已提交，分析输出保留在本地忽略目录。

## 1. 资料和初始数据

赛题、官方附件和四份空结果模板已分类保存。标签表含 16 个功能和 30 个行业，另有 20 个参考网站。压缩包内附件与归档副本一致，所有原文件均保留。赛题拆解见 [分析报告](ANALYSIS_MODELING_REPORT.md)。

**数据采集：**首批 `B01` 使用 2026-08-10 至 2026-11-07 的近 90 日范围，获取后清洗到 `2,601` 条相关记录。来源数分别为 GitHub 395、Hacker News 1,532、量子位 604、IT之家 22、V2EX 48。

B01 来自有分页上限的公开搜索和当前 RSS，不能代表平台全量。采集结果有短文本、标题、简介和缺失热度。用 `py scripts/collect_data.py --batch B01` 采集，以 `py scripts/audit_data.py --batch B01` 检查记录关系；结构检查不代表机会判断质量。详见 [采集报告](DATA_COLLECTION_B01.md)。

## 2. Git 忽略、提交和全量目标

`.gitignore` 忽略 `.serena/`、`.ruff_cache/`、`.pytest_cache/`、虚拟环境、环境文件、`data/raw/`、`data/processed/`、模型权重、站点政策快照和运行结果。这样 B01 正文与下载模型留在本机，不进入代码提交。

| 提交 | 内容 |
| --- | --- |
| `a276c71 feat: add AI opportunity data collection` | 初始项目说明、采集程序、赛题分析、官方附件、结果模板和忽略规则 |
| `8737bad docs: plan complete competition deliverables` | 全量完成目标、分项完成条件及进度清单 |
| `59e8c35` | Python 项目环境、依赖锁、本机模型连接及结构化输出 |
| `0c02a9f` | 进展报告首版 |
| `f3b0eaf` | 批次清洗、result1、来源追溯审计和向量模型 |
| `2eabb28` | 采集及清洗运行命令与数据目录说明 |

目标和逐项进展在 [plan.md](../plan.md) 与 [todo.md](../todo.md) 维护。每个完整功能及有独立价值的修复通过检查后，已获授权自动创建本地提交；不推送、不切换分支、不删除原资料。

## 3. Python 环境和大模型接口

**环境：**使用 `uv init --bare --name ai-opportunity --python 3.14` 创建 `.venv`，依赖和精确解析版本写入 `pyproject.toml`、`uv.lock`。

**凭据：**根据用户授权，`opportunity/model.py` 读取现有 Codex 的模型名、Responses API 服务地址及本机认证。敏感密钥未复制进项目，运行日志和报告也不含密钥。项目部署时可改用本地 `.env`。成本字段必须同时配置实际单价，未配置时显示未知。

**连接检查：**`uv run python scripts/check_model.py` 使用 `gpt-6.1-sol` 发出不含业务数据的结构化请求，收到完成响应。服务返回 token 用量，单价未配置，费用未知。此操作只检查 API 和 JSON 输出，不评价模型效果。

## 4. 多语言向量模型

**语义模型：**按授权下载 MIT 许可的 `intfloat/multilingual-e5-small` ONNX 量化版，约 136 MB，保存在 `data/models/`，不进入提交。已核对模型接口，实现均值池化和向量归一化；中英文语义样例通过。

## 5. 当前任务一实现

`opportunity/collection.py`、`opportunity/cleaning.py` 和 `opportunity/embedding.py` 分别负责采集、清洗和本地向量；`scripts/collect_data.py`、`opportunity/__main__.py` 提供命令入口。清洗按去追踪参数的 URL、长正文相似度和质量标记处理记录，保留各来源证据和热度。

**B01 实际结果：**运行目录为 `results/B01/20261107T164112993137Z/`。3,576 次原始字段出现经过方向筛选和时间检查，2,566 条形成来源 URL 唯一记录，最终保留 2,561 条。742 条方向不符，267 条同来源 URL 归并，1 条超出时间窗；长正文重复处理得到 5 组重复映射，其中 3 组完全重复、2 组高相似。标题和短文本没有因为相同而自动合并。

清洗后来源为 GitHub 387、Hacker News 1,523、量子位 581、IT之家 22、V2EX 48，共 2,561 条。执行 `uv run python scripts/audit_cleaning.py --run results/B01/20261107T164112993137Z`，CSV、JSONL 和 2,561 份正文快照一致。当前 `result1.csv` 保存在运行目录，最终提交目录尚未整理。

## 6. 验证与下一步

任务二以现有 Codex 模型完成 2 条及 5 条跨来源试运行。全量运行每批 16 条、并发 3，共 161 批。141 批已完成，共 2,241 条；20 批失败后尚未写入结果。运行目录为 `results/B01/20261107T173708748922Z/`。恢复器现会将失败批次递归拆为每组 4、2、1 条并保存子组检查点。早期失败请求 token 用量未知。

候选聚类在 269 条模型机会标签上运行，生成 46 个主题，其中 44 个为单记录主题，轮廓系数 0.184。候选主题名存在关键词碎片和噪声，正式热点分析需等人工复核后重新运行。详见 [候选主题报告](TOPICS_CANDIDATE_B01.md)。

最近一次执行 `ruff format`、`ruff check --fix`、`uv run pyright` 和 `uv run python -m pytest -q`，格式、静态类型检查通过，14 项测试通过；B01 清洗审计通过。检查验证实现和数据结构，不替代人工标签或竞赛结论。

## 下一步

1. 人工复核 `results/B01/20261107T173708748922Z/review/review_queue.csv`，再计算人工评价指标。
