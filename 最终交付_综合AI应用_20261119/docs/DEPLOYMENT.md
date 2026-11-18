# 系统部署与运行说明

系统由 FastAPI 后端和 `web/` 静态前端组成，默认使用本地公开数据运行，不需要外部数据库。

本次交付同时提供了可独立查看的 `interface/` 界面与部署单元。它只保留看板、复核工作台、正式结果快照和策划案下载文件，不包含采集程序、模型调用和论文构建工具。进入 `最终交付_综合AI应用_20261119/interface/` 或压缩包中的同名目录后，可按其中的 `README.md` 启动。

## 本机启动

在项目根目录执行：

```powershell
uv sync --locked
uv run uvicorn opportunity.web:app --host 127.0.0.1 --port 8000
```

打开以下地址：

- `http://127.0.0.1:8000/dashboard`：决策看板，展示正式主题、来源覆盖、四维价值分和策划案下载。
- `http://127.0.0.1:8000/`：复核员工作台，查看逐条正文、模型证据和人工字段。
- `http://127.0.0.1:8000/api/docs`：本地 API 文档。

界面源码位于 `web/`，后端入口为 `opportunity/web.py`。截图证据位于 `最终交付_综合AI应用_20261119/docs/screenshots/`，其中 `decision-dashboard.png` 展示决策看板，`reviewer-detail.png` 展示复核工作台。

也可以执行：

```powershell
scripts/run_dashboard.ps1
```

对外查看目录中的启动脚本为：

```powershell
最终交付_综合AI应用_20261119/interface/scripts/run_dashboard.ps1
```

## 角色与权限

未配置账号时，回环地址只允许复核员视图和只读决策看板。决策看板只返回主题、来源覆盖、评分维度、优先级和策划案下载入口，不返回逐条正文。

需要区分账号时，在项目根目录 `.env` 中设置：

```text
REVIEWER_USERNAME=reviewer
REVIEWER_PASSWORD=修改为本地密码
DECISION_MAKER_USERNAME=decision
DECISION_MAKER_PASSWORD=修改为本地密码
```

复核员可以读取正文并编辑人工复核字段。决策者只能读取主题汇总和评分，不能读取逐条正文，也不能修改标签。

## 正式数据来源

看板自动选择 `results/` 中状态为“正式结果”的最新主题运行目录。正式结果包含 100 条人工确认机会记录、14 个展示主题和四维价值评分；多源热点判定要求主题至少覆盖两个来源网站。

策划案下载接口为：

```text
/api/dashboard/proposal/markdown
/api/dashboard/proposal/docx
```

## 常规部署

在受控内网中可将监听地址改为 `0.0.0.0`，并使用反向代理提供 HTTPS、访问日志和账号保护：

```powershell
uv run uvicorn opportunity.web:app --host 0.0.0.0 --port 8000
```

公开网络部署前必须配置复核员和决策者账号，并限制来源数据和正文快照的访问范围。模型服务密钥不写入源码，运行成本由实际服务配置记录。
