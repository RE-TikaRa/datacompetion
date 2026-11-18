# 人工复核工作台

## 启动

```powershell
uv run uvicorn opportunity.web:app --host 127.0.0.1 --port 8000
```

浏览器打开 `http://127.0.0.1:8000/`。页面从 `results/` 中发现有复核队列的运行，默认显示 B01 判别运行。

默认仅在 loopback 地址开放本地复核。需要分开账号时，在本地 `.env` 设置 `REVIEWER_PASSWORD` 与 `DECISION_MAKER_PASSWORD`，启动后从页面账号入口登录。复核员账号只能读取正文和编辑人工复核。决策者账号只读主题汇总、评分和复核进度，无法读取逐条正文或修改标签。

## 操作

左侧可以按编号、来源和标题筛选，并切换候选机会、非机会样本和待复核记录。选择记录后，右侧显示来源链接、正文、模型四项条件、模型证据、建议分类和人工字段。

人工判断为“机会”时，功能和行业必须从官方标签下拉框选择；判断为“非机会”时两个分类保持为空。保存后 JSONL、CSV 和复核摘要同步更新，复核状态改为“已复核”。

## 数据边界

工作台写入当前判别运行目录下的 `review/review_queue.jsonl` 和 `review_queue.csv`。原始采集数据、清洗正文和模型自动判别不被覆盖。人工填写后运行：

```powershell
uv run python scripts/audit_review_queue.py --review results/B01/<判别运行时间>/review
```

项目也提供独立的 AI 辅助复核入口。它不会写入 `human_*` 字段，输出位于 `review/assistant_review/`；盲复核输出位于 `review/assistant_review_blind/`，三方对照输出位于 `review/review_comparison_blind/`。其中 `triage.csv` 和 `stable_positive_candidates.csv` 协助查找分歧与稳定候选。AI 辅助结果不能作为真人真值，真人确认仍需在原复核队列中完成。

`review/assistant_adjudication/` 下的裁定和 `full_batch_proxy/assistant_proxy_result2.csv` 属于历史辅助过程。当前正式全量人工字段和 `result2.csv` 位于 `results/B01/20261118T160530815667Z/`，正式主题和评分位于 `results/B01/20261118T192102321700Z/`。

对复核清单的人工结论会覆盖相应模型标签。用户授权将其余已有 AI 判断转登记为人工确认字段后，正式 `result2.csv` 覆盖全部清洗记录，`final_review.json` 标明全量人工字段覆盖数量。confidence 仍为模型自评值，未经过概率校准。

```powershell
uv run python scripts/finalize_review.py --run results/B01/<判别运行时间>
```
