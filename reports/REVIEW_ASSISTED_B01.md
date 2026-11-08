# B01 AI 辅助复核报告

## 复核范围

输入为 B01 判别运行中的 509 条复核记录：269 条模型候选机会，以及按来源网站和正文类型分层抽取的 240 条模型非机会。

原人工复核队列位于 `results/B01/20261107T173708748922Z/review/review_queue.jsonl`。本报告中的标签由 Codex 模型辅助生成，不能替代真人标注，也不作为比赛提交中的人工真值。

## 处理方法

- 模型：本机 Codex 配置中的 `gpt-6.1-sol`，通过 Responses API 调用。
- 批量：每批 8 条，最多 3 个并发；失败批次递归拆分后恢复。
- 输入：来源、正文类型、标题、正文摘要，以及原自动判别字段。原模型判断只作为待检查信息，不能直接复制。
- 判定：检查可观察终端需求、AI 核心作用、技术可实现性和排除项。
- 分类：机会记录从官方 16 个功能和 30 个行业中选择；非机会记录分类留空。
- 证据：每条结果至少保留一条正文摘录，程序检查摘录能回到完整正文；空白和标点差异会转换为原文片段。
- 边界：证据不足、需求与产品介绍混杂、分类不明确，或需要真人判断时标记 `boundary_case=true`。

正文摘要用于控制请求长度，完整正文没有被覆盖，仍保留在 B01 清洗运行目录。由于复核模型看到了原模型判断，结果存在判断锚定风险。

## 结果

| 指标 | 数值 |
| --- | ---: |
| 复核记录 | 509 |
| AI 辅助判断为机会 | 141 |
| 与原模型判断一致 | 379 |
| 原模型为机会、辅助复核改为非机会 | 129 |
| 原模型为非机会、辅助复核改为机会 | 1 |
| 边界记录 | 197 |
| 分歧或边界记录并集 | 232 |
| 证据片段修正 | 520 |

一致率为 `379 / 509 = 74.46%`。这只是两个模型输出之间的一致率，不是准确率。当前没有真人真值，因此不能据此计算真实 Precision、Recall、F1 或概率校准指标。

240 条模型非机会样本按来源网站和正文类型轮转，每个分层内优先抽取模型置信度较低的记录。这是面向不确定样本的定向抽样，不是随机样本；即使完成真人标注，也不能用它无偏估算全部 2,292 条模型非机会中的漏判率或总体召回率。

## 输出文件

结果保存在 `results/B01/20261107T173708748922Z/review/assistant_review/`：

- `assistant_review.jsonl`：509 条结构化辅助复核结果。
- `assistant_review.csv`：可查看的辅助复核表，包含理由、证据和边界标记。
- `assistant_review_summary.json`：数量、分歧、边界和模型用量汇总。
- `human_attention.csv`：232 条建议真人优先查看的记录。
- `human_attention_summary.json`：真人优先查看清单的统计。
- `batches/`：每个成功批次的可恢复检查点。

原 `review_queue.jsonl`、`review_queue.csv` 中的 `human_*` 字段保持空白，审计结果为 `human_queue_untouched=true`。

盲复核结果保存在同级的 `assistant_review_blind/`，它只接收记录编号、来源、正文类型、标题和正文摘要，不接收原模型判断或第一轮辅助判断。盲复核判断为机会 109 条，边界记录 170 条，按盲复核结果筛出的真人优先查看记录 270 条。

三方对照保存在 `review_comparison_blind/`：

- `consensus.csv`：509 条全量对照，给出原模型、可见标签辅助复核、盲复核和两次辅助复核共识。
- `triage.csv`：328 条存在判断分歧、边界情况或功能/行业分类分歧的记录。
- `comparison_summary.json`：三方状态数量和一致率。
- `stable_positive_candidates.csv`：23 条两轮辅助复核均判机会、功能和行业一致且均未标边界的记录，仅作为真人优先查看的候选。
- `stability_summary.json`：高稳定候选数量和状态。

两次辅助复核判断一致 419 条，其中共同判断为机会 80 条、共同判断为非机会 339 条；原模型、可见标签辅助复核和盲复核三者同时一致 313 条。可见标签辅助复核与盲复核仍使用同一个模型和同一批正文，只能用于发现对原标签的敏感性，不能形成独立真值。

把两次辅助复核都判为机会、功能和行业完全一致、且两次都没有标记边界的记录再筛选，只有 23 条。这些记录的判断稳定性相对更高，但仍需真人确认。

## 模型用量

- 输入 token：758,777。
- 输出 token：97,710。
- 缓存输入 token：259,677。
- 运行耗时：约 2,595 秒。
- 成本：未配置服务单价，因此未知。

盲复核另外使用 602,232 个输入 token、84,925 个输出 token 和 119,932 个缓存输入 token，耗时约 1,864 秒，成本同样未知。

复现命令：

```powershell
uv run python scripts/assistant_review.py --run results/B01/20261107T173708748922Z
uv run python scripts/audit_assistant_review.py --run results/B01/20261107T173708748922Z
uv run python scripts/assistant_review.py --run results/B01/20261107T173708748922Z --blind --batch-size 16
uv run python scripts/audit_assistant_review.py --run results/B01/20261107T173708748922Z --blind
uv run python scripts/compare_reviews.py --run results/B01/20261107T173708748922Z
uv run python scripts/audit_review_comparison.py --run results/B01/20261107T173708748922Z
```

真人确认后，才能把确认结果写入原复核队列，导出正式 `result2.csv`，并据此重跑正式主题和价值评分。
