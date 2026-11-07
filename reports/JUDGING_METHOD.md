# 任务二判别方法

## 输入与输出

输入为任务一清洗运行中的记录索引和正文快照。模型对每条记录输出需求信号、AI 核心性、技术可实现性和排除项，并提供置信度、官方功能及行业标签、原文证据和排除理由。

机会标签由程序计算：

```text
is_opportunity = observable_demand
                 AND ai_core
                 AND technically_feasible
                 AND NOT excluded
```

只有机会记录允许填写官方功能和行业标签。非机会记录保持两个字段为空。confidence 是模型自评值，尚未校准为真实概率。

模型引用的证据必须能匹配正文中的连续片段。程序忽略大小写、空白和标点差异，随后将其替换为原文的精确片段。找不到原文片段时，该批次要求模型重试，不能保留模型编造的引句。程序还检查批次 ID、官方标签、机会规则和分类字段。解析器兼容服务返回 `items`、`results`、`records`、`judgements`、`decisions` 或 `data` 等结果列表键名。

## 批量与恢复

默认每批 16 条，最多并行数由 `MODEL_CONCURRENCY` 控制，默认 3。B01 全量任务共 161 批，模型读取超时为 420 秒。每个成功响应保存为 JSON 检查点；单批网络或输出错误最多请求三次，其他成功结果仍会保存。恢复时程序比较清洗输入哈希、模型和批次配置，只重跑缺失批次。

```powershell
uv run python -m opportunity judge --run results/B01/<清洗运行时间> --limit 16
uv run python scripts/audit_judgements.py --run results/B01/<判别运行时间>
uv run python -m opportunity judge --run results/B01/<清洗运行时间> --resume results/B01/<判别运行时间>
```

使用 `--limit` 的输出是 `result2.preview.csv`。覆盖全部清洗记录时才生成官方文件名 `result2.csv`；模型输出的复核状态仍为待复核。

## 试运行

已使用 2 条记录测试 JSON Schema，又用 5 个来源各取一条内容进行了跨来源试运行。5 条调用返回 4,706 输入 token、1,272 输出 token，耗时约 72 秒。试运行中的产品介绍、新闻和讨论经四项条件分别输出判定，试用记录全部为非机会。服务单价未配置，费用未知。

这些调用只检查结构、规则和证据，不作为人工标签或最终结果。B01 全量判别和人工抽样评价尚未执行。
