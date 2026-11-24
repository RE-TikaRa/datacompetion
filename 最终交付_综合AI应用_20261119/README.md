# 综合 AI 应用公开数据应用实践交付

本目录提供系统方法论文、C2 应用策划案、四份结果表、可运行界面和部署证据。

## 论文与结果

- 当前全文编译 PDF：`paper/论文_全文编译版_20261120.pdf`，共 29 页，来自当前 `paper/manuscript/main.tex`。图表采用阿拉伯数字编号，正文方括号引文为上标，参考文献按首次引用顺序排列。
- 前一版 LaTeX 论文 PDF：`paper/论文_编号与引用修订版_20261120.pdf`。
- 前一版 LaTeX PDF：`paper/论文_最新修订版_去副标题_20261120.pdf`。
- 前一版 LaTeX PDF：`paper/论文_最新修订版_20261120.pdf`。
- 前一版 LaTeX PDF：`paper/论文_目录图表修订版_20261120.pdf`。
- Word 文件：`paper/论文_20261119.docx`
- 策划案：`proposal/C2_AI智能体证据工作台策划案_20261119.docx`
- 结果表：`results/result1.csv` 至 `results/result4.csv`
- 数据规模：2,561 条清洗记录、100 条机会记录、14 个展示主题；C2 是唯一满足来源网站数不少于 2 的多源热点。

## 界面与部署

`interface/` 是可独立运行的界面部署单元，包含静态前端、FastAPI 后端、正式主题快照、复核队列、正文快照和策划案下载文件。它不包含采集程序、模型调用或论文构建工具。

启动方式和角色权限见 [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) 与 [`interface/README.md`](interface/README.md)。

```powershell
cd interface
uv run uvicorn opportunity.web:app --host 127.0.0.1 --port 8000
```

页面入口：

- `http://127.0.0.1:8000/dashboard`：决策看板
- `http://127.0.0.1:8000/`：复核工作台
- `http://127.0.0.1:8000/api/docs`：API 文档

界面验收截图：

- [`docs/screenshots/decision-dashboard.png`](docs/screenshots/decision-dashboard.png)：决策看板，显示 100 条机会、14 个主题、1 个多源热点和 C2 价值分 81.52。
- [`docs/screenshots/reviewer-detail.png`](docs/screenshots/reviewer-detail.png)：复核工作台，显示 509/509 已复核、来源、标题、模型置信度和复核状态。

`docs/SCREENSHOT_LOG.md` 记录截图对应的本地验收状态，`docs/VERIFY_REPORT.md` 记录论文、结果和界面检查。
