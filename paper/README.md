# B01 论文交付

## 当前版本

论文的唯一编辑源为 `manuscript/main.tex`，章节位于 `manuscript/sections/`，参考文献位于 `manuscript/references.tex`，图件位于 `figures/`。

2026-11-18 的论文修订交付将另存为日期化探索修订版，不覆盖 2026-11-09 校对版：

- `deliverables/AI应用机会智能挖掘与评估系统_B01_探索修订版_20261118.pdf`
- `deliverables/AI应用机会智能挖掘与评估系统_B01_探索修订版_20261118.docx`
- `deliverables/AI应用机会智能挖掘与评估系统_B01_最终校验版_20261118.pdf`
- `deliverables/AI应用机会智能挖掘与评估系统_B01_最终校验版_20261118.docx`

`deliverables/` 中已有的“校对版”“修订版”“终稿”“交付版”文件均保留为历史导出。`manuscript/main.pdf` 是早期编译产物，论文构建写入项目外的新临时目录。

## 构建

PDF 使用 Tectonic 0.17.0 的 XeTeX 引擎编译两遍。输出目录应使用新的临时路径，再将确认后的 PDF 复制到 `deliverables/`：

```powershell
tectonic -X compile paper/manuscript/main.tex --outdir C:/Tmp/datacompetition-paper-build --keep-logs --keep-intermediates
```

Word 从同一 TeX 源展开生成，使用 Pandoc 和 `scripts/build_paper_docx.py`：

```powershell
uv run python scripts/build_paper_docx.py --output paper/deliverables/<new-name>.docx
```

最终校验版 PDF 已由 TeX 主源重新编译；DOCX 已由同一主源重新展开并完成结构检查。旧版 Word 页面级检查记录仍保留在本地 QA 目录，当前环境没有可用的 `soffice` 渲染器。

## 证据边界

论文是 B01 的探索性系统方法和案例研究。2,561 条清洗记录、269 条原模型候选机会、509 条人工复核记录、100 条人工确认机会和 14 个人工确认主题均可由本地结果文件追溯。

509 条复核材料已由用户确认人工分类，人工字段只保存类别，人工备注为空。`human_adoption.json` 记录人工标签来源和范围。未进入队列的 2,052 条记录沿用原模型标签，因此论文不把 509 条样本表现外推为全量性能，也不把 C2 主题或其策划框架写成已验证的市场需求。

剩余 2,052 条记录的人工复核、正式主题边界确认、完整策划案和比赛截图尚未完成。当前混合标签结果作为探索性证据。
