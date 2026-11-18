# 界面与部署单元

这里保留本次交付的可运行界面和展示数据快照，不包含采集、模型调用或论文构建工具。

## 启动

在本目录执行：

```powershell
uv run uvicorn opportunity.web:app --host 127.0.0.1 --port 8000
```

也可以执行：

```powershell
scripts/run_dashboard.ps1
```

打开以下地址：

- `http://127.0.0.1:8000/dashboard`：决策看板，展示机会数量、主题质量、多源热点、价值分和策划案下载入口。
- `http://127.0.0.1:8000/`：复核工作台，展示逐条来源、模型判断、证据和复核状态。
- `http://127.0.0.1:8000/api/docs`：只读 API 文档。

`results/正式主题结果/` 保存决策看板读取的正式主题与评分，`results/正式复核数据批次/` 保存复核工作台读取的 509 条复核材料和正文快照。页面不需要外部数据库。

## 文件

- `opportunity/`：只读 Web 后端。
- `web/`：决策看板与复核工作台的静态资源。
- `results/`：面向界面的正式结果快照。
- `proposal/`：C2 策划案下载文件。
- `scripts/run_dashboard.ps1`：本地启动脚本。
