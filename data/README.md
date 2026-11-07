# 数据说明

## 目录

| 路径 | 内容 |
| --- | --- |
| `reference/附件1.xlsx` | 官方功能类别与行业标签 |
| `reference/附件2.xlsx` | 官方参考数据源清单 |
| `reference/labels.json` | 从附件 1 提取的 16 个功能类别与 30 个行业 |
| `reference/reference_sources.json` | 从附件 2 提取的 20 个参考网站 |
| `reference/web_policies/` | 采集时保存的 robots、接口与条款页面文本，`index.json` 保存地址和获取时间 |
| `raw/<批次号>/collection_config.json` | 该批次需求、检索条件与实际时间范围 |
| `raw/<批次号>/<来源>/<请求编号>.json` | API 或订阅源中用于分析的字段与正文，个人账号资料不保存 |
| `raw/<批次号>/<来源>/requests.json` | 请求地址、时间、状态、响应头、分页范围和错误 |
| `raw/<批次号>/manifest.json` | 批次统计、来源状态、采集环境和处理范围 |
| `processed/<批次号>/records.jsonl` | 采集阶段的来源记录索引 |
| `processed/<批次号>/records.csv` | 采集阶段适合 Excel 查看和筛选的索引 |
| `results/<批次号>/<运行时间>/result1.csv` | 官方字段格式的清洗去重结果 |
| `results/<批次号>/<运行时间>/records.jsonl` | 清洗记录、合并来源及原始响应关联 |
| `results/<批次号>/<运行时间>/text/` | 与该次清洗结果对应的正文快照 |
| `results/<批次号>/<运行时间>/cleaning.json` | 方向筛选、链接归并、去重和质量标记统计 |
| `results/<批次号>/<运行时间>/judging.json` | 判别模型、覆盖数量、人工复核状态及 token 用量 |
| `results/<批次号>/<运行时间>/batches/` | 每批模型判别检查点，可从中断处恢复 |
| `results/<批次号>/<运行时间>/judgements.jsonl` | 逐条条件、判断依据、原文引句、标签和复核状态 |

`raw` 保存从响应中选取并经过隐私处理的来源字段，不是完整 HTTP 响应字节副本。原文可通过来源链接核验，处理后的文本可通过请求编号和原始记录位置追溯。

## 统一记录字段

| 字段 | 含义 |
| --- | --- |
| `batch_id`、`record_id` | 批次和批次内连续编号 |
| `source_id`、`source_name` | 来源标识及名称 |
| `native_id`、`source_url` | 平台记录标识与公开链接 |
| `title` | 记录标题 |
| `published_at`、`updated_at`、`collected_at` | 发布时间、平台更新时间及获取时间；缺失值保留 `null` |
| `record_kind` | 项目、Issue、需求主题、产品展示、评论或文章 |
| `content_kind` | `readme`、`description`、`body`、`feed_body` 或 `title_only` |
| `content_path`、`content_characters` | 清洗正文路径及字符数 |
| `metrics` | 平台提供的星标、讨论数、投票等原始数值 |
| `query_ids`、`request_ids` | 命中的检索条件和获取请求 |
| `raw_response_paths` | 对应原始字段文件，路径以项目根目录为基准 |
| `license` | 接口公开的许可证标识；未提供时为 `null` |
| `provenance` | 原始链接、平台 ID、请求编号、发布时间、热度和响应路径 |
| `sources` | 正文重复合并后覆盖的网站名称 |
| `quality_flags` | 内容不完整、文本过短或热度缺失的提示 |

清洗运行中的 `content_path` 和 CSV“内容”列相对该次运行目录，交付 `result1.csv` 时需同时携带该运行的 `text/` 快照。

## 内容与质量

采集过程中不保存作者档案、账号资料、头像或评论者身份字段。文本处理隐去可识别格式的邮箱、电话号码、IP 和用户提及；该处理无法识别所有自然语言个人信息，正式导出前仍需要检查具体正文。

清洗包括 HTML 转正文、URL 移除和空白规范化。相同来源链接合并，多次检索命中的请求编号一并保存。相近语义、同一事件转载和跨站重复需要单独分析，不能将所有讨论相似问题的记录合并，否则会损失真实的独立需求证据。

`title_only` 只有标题，`description` 只有项目简介，不能视作完整正文。教程、产品介绍、新闻和宣传内容可进入相关记录集，是否构成机会由后续判别决定。

热度保留各平台提供的原始单位。缺失值保持缺失，GitHub 星标不能与 Hacker News 投票直接相加。采集排序、分页上限、来源间样本量差异和时间覆盖会影响热点统计，分析时需要报告这些偏差。

## 检查

```powershell
uv run python scripts/audit_data.py --batch B01
uv run python scripts/audit_cleaning.py --run results/B01/<运行时间>
```

第一个命令检查采集批次。第二个命令检查官方 CSV 列名、编号、正文快照、来源热度和原始响应关系。

同一批次文件不覆盖。再次调用采集时使用新的批次号，并保留对应配置与清单。
