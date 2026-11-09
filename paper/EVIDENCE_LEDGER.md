# 论文证据账本

## 研究对象

- 研究批次：B01。需求方向为综合 AI 应用机会，覆盖多个行业。
- 时间窗：2026-08-10 至 2026-11-07（北京时间口径）。
- 来源：GitHub、Hacker News、量子位、IT之家、V2EX，共 5 个公开来源。
- 原始字段出现：3,576；来源 URL 唯一记录：2,566；最终清洗记录：2,561。

## 可写入正文的事实

| 论文主张 | 证据文件 | 强度 | 限制 |
| --- | --- | --- | --- |
| B01 完成多源公开数据采集与可追溯清洗 | 采集与清洗报告 | 结构审计通过 | 来源样本量和历史覆盖不一致 |
| 清洗结果包含 2,561 条记录 | cleaning.json、records.jsonl、result1.csv | 数量可复现 | 670 条内容不完整，907 条缺少热度 |
| 原模型覆盖全部清洗记录 | judging.json、JUDGING_B01.md | 结构审计通过 | 置信度是模型自评，尚未校准 |
| AI 代理复核覆盖 509 条复核队列 | assistant_adjudication_summary.json | 编号和证据审计通过 | 不是人工真值 |
| AI 代理结果包含 100 条机会候选 | assistant_proxy_summary.json | 代理结果可复现 | 2,052 条未抽样记录仍为原模型标签 |
| 代理候选形成 14 个主题 | topics.json | 成员审计通过 | 12 个主题为单记录，轮廓系数 0.204 |

## 不可写成强结论的内容

- 不报告 Precision、Recall、F1 或概率校准结果，因为没有真人真值。
- 不把 AI 代理复核称为人工复核，也不把代理 result2 称为正式比赛 result2。
- 不把代理主题称为已经识别出的可靠热点。
- 不把来源记录数量解释为各行业真实需求占比。
- 不把缺失热度解释为低热度。

## 代理主题摘要

| 主题 | 成员数 | 价值分 | 来源覆盖 |
| --- | ---: | ---: | --- |
| C2 AI智能体在架构、排障与医疗等场景的应用 | 22 | 85.76 | GitHub、V2EX、量子位 |
| C1 AI编程助手的使用方式与工作流程 | 66 | 54.26 | Hacker News |
| C10 Emu Concept – Make AI Follows Your Rules. (Feed… | 1 | 27.48 | Hacker News |
| C12 PostgreSQL Internals [pdf] (2023) | 1 | 25.96 | Hacker News |
| C13 Every Mac comes with an (undocumented) family m… | 1 | 25.96 | Hacker News |
| C14 Restaurant Delivery Payment-Skimming Campaign | 1 | 25.96 | Hacker News |
| C3 Idea to reduce AI token use at large orgs | 1 | 24.43 | Hacker News |
| C8 What is the best LLM for turbo charging code? | 1 | 24.00 | Hacker News |
| C11 Show HN: The Public Eye – Agentic search for co… | 1 | 23.84 | Hacker News |
| C4 What is your AI era PowerPoint alternative? | 1 | 23.41 | Hacker News |
| C5 Ask HN: Airbnbs with AI Photos | 1 | 22.82 | Hacker News |
| C9 Ask HN: Organize and Cleanup iCloud Photos Usin… | 1 | 22.81 | Hacker News |
| C6 How to process incoming call audio on Android /… | 1 | 22.39 | Hacker News |
| C7 Latency reduction for consumer facing AI applic… | 1 | 21.79 | Hacker News |

代理评分权重为多源指向度 0.45、记录规模 0.35、互动信号 0.20。缺失互动指标不填零，主题没有可用指标时按可用维度重新归一。
