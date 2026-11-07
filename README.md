# AI 应用场景的智能挖掘与机会评估系统

第三届甘肃省大学生数据挖掘挑战赛本科组项目。系统围绕用户提出的需求方向，从公开渠道采集内容，识别具有真实需求和实现条件的 AI 应用机会，聚合主题并评估价值，为立项决策提供可追溯的依据。

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
  raw/<批次号>/             采集配置、请求记录和保留的来源字段
  processed/<批次号>/       统一记录索引与清洗正文
docs/
  competition/              原始赛题 PDF
  AI_USAGE.md               AI 辅助工作记录
reports/                    赛题分析、数据采集与质量报告
scripts/                    采集、官方标签提取和数据检查脚本
templates/results/          官方四份空 CSV 模板
```

采集字段和清洗结果分别保存。`data/processed/<批次号>/` 是来源索引，`results/<批次号>/<运行时间>/` 保存清洗结果。每次运行都生成新目录。

## 数据采集

项目运行使用 Python 3.14 和 `uv.lock` 中的依赖。北京时间用于确定日期范围，存储的发布时间使用带时区的 ISO 8601 格式。

```powershell
uv sync --locked
uv run python -m opportunity collect --batch B02 --direction "农业 AI 应用" --keywords 农业 种植 农机
uv run python -m opportunity clean --batch B02
uv run python -m opportunity judge --run results/B02/<清洗运行时间> --limit 8
uv run python scripts/audit_judgements.py --run results/B02/<判别运行时间>
uv run python scripts/audit_data.py --batch B02
uv run python scripts/audit_cleaning.py --run results/B02/<运行时间>
```

`--keywords` 指定需求关键词，`--direction` 写入批次说明；只有命中关键词的记录会进入该需求的清洗结果。未指定 `--reference-date` 时按当前北京时间向前检索 90 天。每次采集使用新的批次号，已有批次不会覆盖。

`clean` 从该批次采集字段生成新的独立运行目录，包含官方表头 `result1.csv`、正文快照、来源关联和清洗报告。

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
- [实施进展记录](reports/PROGRESS_REPORT.md)
- [AI 辅助工作记录](docs/AI_USAGE.md)

## 交付要求

提交材料包括论文 Word/PDF、四份结果 CSV、源码和运行说明、全流程截图、AI 使用报告。论文正文不超过 30 页，作品及附件不得包含学校、队号、团队成员和指导教师等身份信息。

采集正文仅用于本地研究与可追溯分析，引用保留来源。原始内容、处理记录和站点快照默认不进入 Git；发布资料前应按各来源的许可决定可包含的内容。系统还需要明确需求发起者、决策者等角色的权限与数据可见范围，并记录模型调用、存储和部署成本。
