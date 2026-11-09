# B01 论文交付

## 当前版本

论文的唯一编辑源为 `manuscript/main.tex`，章节位于 `manuscript/sections/`，参考文献位于 `manuscript/references.tex`，图件位于 `figures/`。

2026-11-09 完成百分号转义、复核比例说明和 `body` 字段表述修正后，当前交付文件为：

- `deliverables/AI应用机会智能挖掘与评估系统_B01_校对版_20261109.pdf`
- `deliverables/AI应用机会智能挖掘与评估系统_B01_校对版_20261109.docx`

`deliverables/` 中较早的“修订版”“终稿”“交付版”文件保留作为历史导出，不应替代“校对版”。`manuscript/main.pdf` 是早期编译产物，后续编译均写入项目外的独立临时目录，避免覆盖交付文件。

## 构建

PDF 使用 Tectonic 0.17.0 的 XeTeX 引擎编译两遍。输出目录应使用新的临时路径，再将确认后的 PDF 复制到 `deliverables/`：

```powershell
tectonic -X compile paper/manuscript/main.tex --outdir C:/Tmp/datacompetition-paper-build --keep-logs --keep-intermediates
```

Word 从同一 TeX 源展开生成，使用 Pandoc 和 `scripts/build_paper_docx.py`：

```powershell
uv run python scripts/build_paper_docx.py --output paper/deliverables/<new-name>.docx
```

Word 页面级检查使用 Microsoft Word 365 导出临时 PDF；交付前需要重新渲染并查看所有页面。

## 证据边界

论文是 B01 的探索性系统方法和案例研究。2,561 条清洗记录、269 条原模型候选机会、509 条代理复核队列、100 条 AI 代理机会候选和 14 个代理主题均可由本地结果文件追溯。

代理复核由同一 Codex 模型完成，真人复核字段仍为空；未进入代理队列的 2,052 条记录沿用原模型标签。因此论文不报告人工 Precision、Recall、F1，也不把 C2 主题或其策划框架写成已验证的市场需求。

正式比赛 `result2`、`result3`、`result4` 及完整策划案仍需真人确认后重新生成。论文交付不改变原始采集数据和人工复核队列。
