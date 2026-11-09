# 论文图表规划

| 图表 | 论证问题 | 数据来源 | 计划位置 | 结论边界 |
| --- | --- | --- | --- | --- |
| Figure 1 | B01 来源组成与样本规模 | records.jsonl | 数据与采集 | 不代表平台总体 |
| Figure 2 | 各阶段记录规模变化 | cleaning.json、judging.json、代理摘要 | 方法与结果 | 不是召回率 |
| Figure 3 | 内容质量限制 | cleaning.json | 数据质量 | 缺失与短文本需保留 |
| Figure 4 | 代理复核相对原模型的变化 | 代理 JSONL | 复核与评价 | 不是真人准确率 |
| Figure 5 | 代理主题规模与价值分布 | topics.json、scoring.json | 主题与价值评估 | 不能宣称热点稳定 |
| Figure 6 | 原模型与代理标签交叉变化 | 代理 JSONL | 稳健性与限制 | 只能说明代理敏感性 |
