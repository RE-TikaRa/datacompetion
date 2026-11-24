# AI 应用场景的智能挖掘与机会评估系统

第三届甘肃省大学生数据挖掘挑战赛本科组项目。系统围绕用户提出的需求方向，从公开渠道采集内容，识别具有真实需求和实现条件的 AI 应用机会，聚合主题并评估价值，为立项决策提供可追溯的依据。

> 项目细则、每个文件夹的功能、B01 数据链路、当前完成度、验证命令和剩余工作集中记录在 [项目细则与当前进度](docs/PROJECT_GUIDE.md)。

### 当前状态

| 项目 | 状态 |
| --- | --- |
| B01 采集与清洗 | 完成，2,561 条清洗记录 |
| 全量自动判别 | 完成，2,561 条覆盖，269 条模型候选机会 |
| 全量人工标签登记 | 已完成 2,561 条，100 条机会，人工备注为空 |
| 正式主题与评分 | 已完成 `result3/result4`，14 个主题，C2 为 81.52 分 |
| 复核工作台与决策看板 | 代码、测试和本地浏览器验收完成；可用 `scripts/run_dashboard.ps1` 启动 |
| 决策看板与部署说明 | 已完成 | `/dashboard`、`docs/DEPLOYMENT.md`、`scripts/run_dashboard.ps1` |
| 论文 Word/PDF | 当前 LaTeX 全文编译版已完成；29 页 A4，PDF 逐页检查完成，Word 版本保留 |
| 剩余记录人工复核与全量主题结果 | 已完成；2,052 条按授权转登记人工字段 |
| 完整比赛提交包 | 已生成 `submission/B01_全量提交_20261119.zip` |
| 对外查看交付包 | 已生成 `最终交付_综合AI应用_20261119/`；最新全文 PDF 为 `paper/论文_全文编译版_20261120.pdf` |

## 任务关系

```text
需求方向 → 独立采集批次 → 清洗与去重 → 机会判别与分类
                                      ↓
立项策划案 ← 交互式结果展示 ← 价值排序 ← 语义主题聚合
```

每次需求建立一个独立批次。记录使用 `批次号-记录编号` 标识，例如 `B01-S00001`。主题、评分和策划案都需要关联到同一批次的原始内容。

| 任务 | 输出 | 主要要求 |
| --- | --- | --- |
| 多源采集与清洗 | `result1.csv` | 公开来源、发布时间、真实互动指标、清洗正文快照及批次内去重 |
| 机会判别与分类 | `result2.csv` | 覆盖全部清洗记录，输出机会判断和置信度；机会记录各标注一个功能及行业 |
| 主题聚合 | `result3.csv` | 仅聚合机会记录，生成主题名称、记录数、来源覆盖及成员编号 |
| 价值评估 | `result4.csv` | 至少评价多源指向度和记录规模，给出评分依据、权重和优先级 |
| 决策支持 | 可交互结果与策划文档 | 主题选择、目标用户、痛点、功能、技术路线、实施周期、子任务、依据来源及评分 |

## 文件结构

```text
archive/                    原始数据压缩包及解压副本
configs/collection.json     需求方向、检索条件、时间窗和数据源
data/
  reference/                官方附件、标签、参考网站与采集规则快照
  paper/                    本地论文参考资料，不进入 Git
  raw/<批次号>/             采集配置、请求记录和保留的来源字段
  processed/<批次号>/       统一记录索引与清洗正文
docs/
  competition/              原始赛题 PDF
  AI_USAGE.md               AI 辅助工作记录
reports/                    赛题分析、数据采集与质量报告
scripts/                    采集、官方标签提取和数据检查脚本
templates/results/          官方四份空 CSV 模板
submission/                 正式比赛提交目录和验收资料
```

采集字段和清洗结果分别保存。`data/processed/<批次号>/` 是来源索引，`results/<批次号>/<运行时间>/` 保存清洗结果。每次运行都生成新目录。

## 仓库整理

Git 保留源码、配置、报告、论文主源、正式提交目录和验收说明。原始采集结果、模型权重、运行缓存、参考论文和压缩包留在本机，已由 `.gitignore` 排除。当前论文编辑源是 `paper/manuscript/main.tex`，对应的全文 PDF 位于 `最终交付_综合AI应用_20261119/paper/论文_全文编译版_20261120.pdf`。

## 数据采集

项目运行使用 Python 3.14 和 `uv.lock` 中的依赖。北京时间用于确定日期范围，存储的发布时间使用带时区的 ISO 8601 格式。

```powershell
uv sync --locked
uv run python -m opportunity collect --batch B02 --direction "农业 AI 应用" --keywords 农业 种植 农机
uv run python -m opportunity clean --batch B02
uv run python -m opportunity judge --run results/B02/<清洗运行时间> --limit 8
uv run python scripts/audit_judgements.py --run results/B02/<判别运行时间>
uv run python scripts/build_review_queue.py --run results/B01/20261107T173708748922Z --negative-sample 240
uv run python scripts/audit_review_queue.py --review results/B01/20261107T173708748922Z/review
uv run python scripts/finalize_review.py --run results/B01/20261107T173708748922Z
uv run python scripts/audit_data.py --batch B02
uv run python scripts/audit_cleaning.py --run results/B02/<运行时间>
uv run python scripts/audit_topics.py --run results/B01/<主题运行时间>
uv run python scripts/assistant_review.py --run results/B01/20261107T173708748922Z
uv run python scripts/audit_assistant_review.py --run results/B01/20261107T173708748922Z
uv run python scripts/assistant_review.py --run results/B01/20261107T173708748922Z --blind --batch-size 16
uv run python scripts/audit_assistant_review.py --run results/B01/20261107T173708748922Z --blind
uv run python scripts/compare_reviews.py --run results/B01/20261107T173708748922Z
uv run python scripts/audit_review_comparison.py --run results/B01/20261107T173708748922Z
uv run python scripts/adjudicate_reviews.py --run results/B01/20261107T173708748922Z --batch-size 16
uv run python scripts/audit_adjudication.py --run results/B01/20261107T173708748922Z
uv run python scripts/build_proxy_result2.py --run results/B01/20261107T173708748922Z
uv run python scripts/audit_proxy_result2.py --run results/B01/20261107T173708748922Z
uv run python scripts/aggregate_topics.py --cleaning-run results/B01/20261107T164112993137Z --judgement-run results/B01/20261107T173708748922Z --judgement-file review/assistant_adjudication/full_batch_proxy/assistant_proxy_judgements.jsonl --label-source assistant-proxy
uv run python scripts/convert_adopted_labels_to_human.py --run results/B01/20261107T173708748922Z
uv run python scripts/audit_human_adoption.py --run results/B01/20261107T173708748922Z
uv run python scripts/aggregate_topics.py --cleaning-run results/B01/20261107T164112993137Z --judgement-run results/B01/20261107T173708748922Z --judgement-file final/final_judgements.jsonl --label-source human-reviewed
```

`--keywords` 指定需求关键词，`--direction` 写入批次说明；只有命中关键词的记录会进入该需求的清洗结果。未指定 `--reference-date` 时按当前北京时间向前检索 90 天。每次采集使用新的批次号，已有批次不会覆盖。

`clean` 从该批次采集字段生成新的独立运行目录，包含官方表头 `result1.csv`、正文快照、来源关联和清洗报告。

前两条 `assistant-proxy` 命令只用于复现历史辅助结果；正式结果使用 `results/B01/20261118T160530815667Z/` 的全量人工字段和 `results/B01/20261118T192102321700Z/` 的正式主题输出。

```powershell
ruff format
ruff check --fix
```

官方工作表已导出为程序读取的 JSON。提取脚本采用独占创建，发现现有输出时停止，原 Excel 保持完整。

## 阅读入口

- [赛题分析与实现约束](reports/ANALYSIS_MODELING_REPORT.md)
- [数据来源与采集依据](reports/DATA_SOURCES.md)
- [数据目录和字段说明](data/README.md)
- [B01 数据采集报告](reports/DATA_COLLECTION_B01.md)
- [B01 清洗报告](reports/DATA_CLEANING_B01.md)
- [任务二判别方法](reports/JUDGING_METHOD.md)
- [B01 机会判别结果](reports/JUDGING_B01.md)
- [B01 候选主题与评分](reports/TOPICS_CANDIDATE_B01.md)
- [B01 AI 辅助复核](reports/REVIEW_ASSISTED_B01.md)
- [实施进展记录](reports/PROGRESS_REPORT.md)
- [人工复核工作台](docs/REVIEW_WORKBENCH.md)
- [AI 辅助工作记录](docs/AI_USAGE.md)
- [B01 论文结果与证据边界](paper/RESULTS_REPORT.md)
- [B01 论文证据账本](paper/EVIDENCE_LEDGER.md)
- [论文源文件与交付版本](paper/manuscript/main.tex)

## 交付要求

提交材料包括论文 Word/PDF、四份结果 CSV、源码和运行说明、全流程截图、AI 使用报告。论文正文不超过 30 页，作品及附件不得包含学校、队号、团队成员和指导教师等身份信息。

采集正文仅用于本地研究与可追溯分析，引用保留来源。原始内容、处理记录和站点快照默认不进入 Git；发布资料前应按各来源的许可决定可包含的内容。系统还需要明确需求发起者、决策者等角色的权限与数据可见范围，并记录模型调用、存储和部署成本。
