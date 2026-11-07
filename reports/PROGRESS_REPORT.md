# 项目实施与操作记录

更新时间：2026-11-08  
项目：第三届甘肃省大学生数据挖掘挑战赛本科组，AI 应用场景智能挖掘与机会评估系统。

本报告记录代码交付和会改变数据状态的重要操作。每个阶段列出目的、文件、命令、数据变化和检查结果。后续新增功能完成后继续更新。

## 当前状态

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| 赛题与资料准备 | 已完成 | 赛题、官方附件、空模板、公开来源和目录已整理 |
| 项目说明与实现方案 | 已完成 | `README.md`、`PROJECT_MEMORY.md`、`plan.md`、`todo.md` 已建立 |
| 环境和模型连接 | 已完成 | Python 3.14 项目环境；本机 Codex Responses 模型连接检查成功 |
| 多语言向量模型 | 已下载，待校验 | 多语言 E5 small ONNX 权重已下载；向量代码已编写，Pyright 尚有一项 NumPy 输出类型问题 |
| 可复用采集模块 | 已拆分，待端到端复测 | 现有适配器已移入 `opportunity/collection.py`，`scripts/collect_data.py` 改为命令行入口 |
| 清洗和 result1 | 已实现，尚未运行 | 从采集字段生成新的清洗运行目录，避免写回 B01 原始快照 |
| 机会判断至提交材料 | 未开始完成 | `result2`、`result3`、`result4`、系统界面、评价样本及论文尚未生成 |

当前提交为 `59e8c35 feat: connect analysis to configured model service`。未推送。当前代码有未提交的任务一采集拆分、清洗、向量与测试。

## 1. 赛题资料和初始数据

1. 根据赛题说明，整理了五项任务、官方字段、标签和匿名提交条件，详见 [赛题分析](ANALYSIS_MODELING_REPORT.md)。
2. 建立 `docs/competition/`、`data/reference/`、`templates/results/` 和 `archive/`。赛题 PDF、两份 Excel、四份 CSV、压缩包和解压副本均保留。
3. 官方附件 1 提取为 16 个功能类别与 30 个行业。附件 2 提取为 20 个参考来源。
4. 检查压缩包后，六份内部文件与对应归档附件逐一比对，内容相同。
5. 调查 GitHub、Hacker News、量子位、IT之家、V2EX 当前公开 API、RSS、robots 或条款入口，页面快照保存在 `data/reference/web_policies/`，没有把这些页面放入公开 Git 提交。

**数据采集：**首批 `B01` 使用 2026-08-10 至 2026-11-07 的近 90 日范围，获取后清洗到 `2,601` 条相关记录。来源数分别为 GitHub 395、Hacker News 1,532、量子位 604、IT之家 22、V2EX 48。

该数据仍为有限公开搜索和 RSS 样本。GitHub 与 Hacker News 检索有页数上限；RSS 不含完整历史。496 条文本短于 100 字符，396 条只有标题，274 条只有项目简介，934 条没有公开热度。三组正文完全相同的记录仍在 B01 原始索引中。详细记录见 [B01 采集报告](DATA_COLLECTION_B01.md)。

**命令与检查：**采集时运行 `py scripts/collect_data.py --batch B01`。结构检查命令为 `py scripts/audit_data.py --batch B01`，曾检查 2,601 条 JSONL、CSV、正文、日期和来源关联，无结构错误；该检查不等于机会判断质量验证。

## 2. Git 忽略、提交和全量目标

`.gitignore` 忽略 `.serena/`、`.ruff_cache/`、`.pytest_cache/`、虚拟环境、环境文件、`data/raw/`、`data/processed/`、模型权重、站点政策快照和运行结果。这样 B01 正文与下载模型留在本机，不进入代码提交。

| 提交 | 内容 |
| --- | --- |
| `a276c71 feat: add AI opportunity data collection` | 初始项目说明、采集程序、赛题分析、官方附件、结果模板和忽略规则 |
| `8737bad docs: plan complete competition deliverables` | 全量完成目标、分项完成条件及进度清单 |
| `59e8c35 feat: connect analysis to configured model service` | Python 项目环境、依赖锁、本机模型连接、JSON Schema 输出、模型配置文档与测试 |

目标和逐项进展在 [plan.md](../plan.md) 与 [todo.md](../todo.md) 维护。每个完整功能及有独立价值的修复通过检查后，已获授权自动创建本地提交；不推送、不切换分支、不删除原资料。

## 3. Python 环境和大模型接口

**操作：**`uv init --bare --name ai-opportunity --python 3.14` 创建 `pyproject.toml` 与 `.venv`。使用 `uv add` 安装并锁定 FastAPI、Uvicorn、HTTPX、NumPy、scikit-learn、ONNX Runtime、tokenizers、Hugging Face Hub、python-docx、Matplotlib 和 ReportLab。开发工具通过 `uv add --dev pytest pyright` 加入，精确版本写入 `uv.lock`。

**凭据：**根据用户授权，`opportunity/model.py` 读取现有 Codex 的模型名、Responses API 服务地址及本机认证。敏感密钥未复制进项目，运行日志和报告也不含密钥。项目部署时可改用本地 `.env`。成本字段必须同时配置实际单价，未配置时显示未知。

**真实连接检查：**`uv run python scripts/check_model.py` 成功向 `gpt-6.1-sol` 发送一个无业务数据的 JSON Schema 连通请求，响应 `completed`。返回 22,459 个输入 token、13 个输出 token，接口未提供经过确认的单价，因此未计算费用。终端显示中文发生编码乱码，该检查只验证了请求和 JSON 字段，不用于判断模型中文质量。

## 4. 多语言向量模型

根据用户授权，从 Hugging Face revision `614241f622f53c4eeff9890bdc4f31cfecc418b3` 下载 `intfloat/multilingual-e5-small`，文件写入 Git 忽略的 `data/models/multilingual-e5-small/`。

| 文件 | 大小 |
| --- | ---: |
| `onnx/model_qint8_avx512_vnni.onnx` | 118,346,824 字节 |
| `onnx/tokenizer.json` | 17,082,730 字节 |
| `config.json` | 655 字节 |
| `README.md` | 497,538 字节 |

模型清单记录版本、下载来源和 MIT 许可。ONNX 接口检查确认三个输入 `input_ids`、`attention_mask`、`token_type_ids`，输出 384 维 hidden state。现已实现 attention-mask mean pooling 和 L2 单位向量；中文与英文语义相似性样例测试通过。完整运行 Pyright 时尚有一项 ONNX 返回值的类型提示需要处理，不能仅根据样例测试认定此模块完成。

## 5. 当前任务一实现

当前工作树对采集功能进行模块化，不重新下载 B01：

- `opportunity/collection.py` 承载可复用的来源适配器和独立批次写入。
- `scripts/collect_data.py` 提供批次、日期和需求方向命令参数。
- `opportunity/cleaning.py` 读取 B01 的来源字段，在全新的运行目录中去渠道噪声、规范正文、标准化 URL、保留质量标记，并生成官方格式 `result1.csv` 和 JSONL 关系表。
- `opportunity/files.py` 提供运行目录和 JSON、CSV、JSONL 文件读写。
- `opportunity/embedding.py` 提供本地文本向量计算。
- `opportunity/__main__.py` 暂提供 `clean` 和 `collect` 命令。

清洗设计按风险区分重复类型：同来源 URL 去除 UTM 等追踪参数后合并并保留原链接；长正文先做四字符 TF-IDF 候选检索，再以字符 shingle Jaccard `≥0.95` 合并；标题或短文本不会因为内容简短相同就被认作转载。跨来源合并保留所有来源、URL、请求、发布时间和各自热度指标，热度不求和。短正文、标题样本、简介样本及缺失热度进入质量标记。

这段处理尚未针对 B01 实际执行。因此目前还没有本轮 `result1.csv`、近重复数量和清洗报告结果。实际运行后将在此表追加记录，列出输入记录数、输出记录数、合并明细和相对路径。

## 6. 已执行的代码检查

| 检查 | 最近结果 | 涉及范围 |
| --- | --- | --- |
| `ruff format` | 已执行 | 现有 Python 脚本与新 Python 模块 |
| `ruff check --fix` | 已执行 | Ruff 配置选择的 E/F/I/UP/B/SIM 规则 |
| `uv run python -m pytest tests/test_model.py tests/test_cleaning.py -q` | 7 项通过 | 模型配置、安全与结构化输出、清洗和重复判断 |
| `uv run python -m pytest tests/test_embedding.py -q` | 1 项通过 | 向量形状、L2 归一化、中英相似性样例 |
| `uv run pyright` | 1 项失败 | `embedding.py` 中 ONNX `run()` 返回类型声明不明确；需处理并重跑 |
| `uv run python -m pytest -q` | 尚未针对当前工作树重跑 | 全量测试，包括即将新增的任务一集成检查 |

前两项测试组分别运行，尚无覆盖所有当前代码的完整通过结果。测试范围只验证代码行为和样本，不替代人工标签与竞赛研究结论。

## 操作记录

| 时间 | 操作 | 结果或数据影响 |
| --- | --- | --- |
| 2026-11-07 | 整理原始附件与采集 B01 | 原文件保留；本地生成 2,601 条原始相关记录和快照 |
| 2026-11-07 | B01 结构检查 | JSONL、CSV、来源链接、正文文件和时间窗结构通过 |
| 2026-11-07 | 下载多语言 E5 模型 | 本地下载约 135 MB，MIT 许可，未提交 Git |
| 2026-11-07 | 模型连接检查 | Responses API 返回完成，记录 token，用量价格未配置 |
| 2026-11-08 | 创建 Python 3.14 环境并锁定依赖 | `.venv` 被忽略，依赖和精确解析保存在 `pyproject.toml`、`uv.lock` |
| 2026-11-08 | 编写任务一模块化和清洗代码 | 当前未提交；尚未处理真实 B01 输入 |

## 下一步

1. 修正 Pyright 的 ONNX 输出类型提示，运行完整格式、静态检查和测试。
2. 用已有 B01 原始字段执行清洗，生成单独 `result1.csv`，检查重复映射、来源、行数及所有快照路径。
3. 评估正文去重与标题质量，完成任务一后更新本报告和 `todo.md` 并提交。
4. 继续任务二；需保留模型证据、排除原因、机器置信度和人工复核记录。
