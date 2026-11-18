# 项目细则与当前进度

更新时间：2026-11-19。项目目录为 `C:/Users/Tika/Desktop/datacompetion`，分支为 `main`。本地提交状态和最新提交号请用 `git status --short --branch` 与 `git log -1 --oneline` 查看；改动只在本机，没有推送远程。

这份文档是项目导航和进度记录。README 负责快速入口，本文件负责说明目录职责、数据流、运行结果、验证方式、交付状态和剩余工作。`results/`、`data/raw/`、`data/processed/`、`data/models/` 等目录被 `.gitignore` 忽略，但它们仍然存在于本机，是当前研究结果的主要存储位置。

## 一眼查看

系统处理链路：

```text
需求方向
  -> 独立采集批次
  -> 来源字段与正文快照
  -> 清洗、相关性筛选、去重
  -> 全量机会判别
  -> 复核队列与证据回指
  -> 语义主题聚合
  -> 价值评分与优先级
  -> 复核工作台、论文和策划案
```

### 当前完成度

| 模块 | 当前状态 | 说明 |
| --- | --- | --- |
| 赛题、附件和模板整理 | 已完成 | 原赛题、官方附件、压缩包和四份空模板已归档 |
| B01 公开数据采集 | 已完成 | 5 个公开来源，原始相关记录 2,601 条 |
| B01 清洗与 `result1` | 已完成 | 最终清洗记录 2,561 条，正文快照和去重关系完整 |
| 全量自动机会判别 | 已完成 | 覆盖 2,561 条，原模型候选机会 269 条 |
| 人工复核 | 已完成样本复核 | 用户确认 509 条材料，100 条机会与 409 条非机会；人工备注为空 |
| 模型辅助复核与裁定 | 已完成辅助过程 | 辅助结果保存在独立文件，人工字段只保存用户确认类别 |
| 语义聚类与价值评分 | 已完成正式流程 | 14 个全量人工确认主题，12 个单记录主题，轮廓系数 0.2039439 |
| 全量人工 `result2` | 已生成 | 2,561 条均登记为人工字段，100 条机会 |
| 正式 `result3`、`result4` | 已生成 | `results/B01/20261118T192102321700Z/result3.csv`、`result4.csv` |
| 复核工作台与决策看板 | 已完成并验收 | FastAPI、本地页面、角色权限、标签校验、正式主题看板和策划案下载均已实现；截图位于最终交付目录 |
| 论文 Word/PDF | 最终校验版已验收 | 增加分类器嵌套验证、来源留出、图表和文献；新旧版分别保存 |
| 完整比赛提交包 | 已生成 | `submission/B01_全量提交_20261119.zip`；内部过程包保留在项目目录 |
| 对外查看交付包 | 已生成并更新 | `最终交付_综合AI应用_20261119/` 与 `submission/综合AI应用_评审修订_20261119.zip`；含界面部署单元和两张验收截图 |

### B01 关键数字

| 阶段 | 记录数或结果 | 当前文件 |
| --- | ---: | --- |
| 采集阶段相关记录 | 2,601 | `data/processed/B01/`，本地忽略目录 |
| 原始字段出现 | 3,576 | `results/B01/20261107T164112993137Z/cleaning.json` |
| 来源 URL 唯一记录 | 2,566 | 同上 |
| 最终清洗记录 | 2,561 | `results/B01/20261107T164112993137Z/result1.csv` |
| 自动判别覆盖 | 2,561 | `results/B01/20261107T173708748922Z/judgements.jsonl` |
| 原模型候选机会 | 269 | `results/B01/20261107T173708748922Z/result2.csv` |
| 人工复核队列 | 509 | `results/B01/20261107T173708748922Z/review/` |
| 全量人工确认机会候选 | 100 | `results/B01/20261118T160530815667Z/final/result2.csv` |
| 正式主题 | 14 | `results/B01/20261118T192102321700Z/topics.json` |
| 单记录主题 | 12 | 同上 |
| 正式主题最高分 | C2，81.52 | `results/B01/20261118T192102321700Z/scoring.json` |

## 根目录文件

| 文件 | 功能 |
| --- | --- |
| `README.md` | 快速入口、任务关系、常用运行命令和阅读链接 |
| `docs/PROJECT_GUIDE.md` | 本文件，说明目录职责、数据流、进度和验证方式 |
| `PROJECT_MEMORY.md` | 项目长期记忆和已确认的范围、决策、限制 |
| `plan.md` | 完整实现目标、产物定义、技术组织和执行顺序 |
| `todo.md` | 可勾选的阶段进度清单 |
| `pyproject.toml` | Python 项目依赖、开发依赖和 pytest 根路径配置 |
| `uv.lock` | uv 锁定的依赖版本 |
| `ruff.toml` | Ruff 检查规则 |
| `.env.example` | 模型服务、账号和价格配置示例，不含真实密钥 |
| `.gitignore` | 忽略本地数据、模型、缓存和论文构建中间件 |

本机还存在 `.venv/`（uv 管理的项目环境）、`.serena/`（IDE 项目状态）、`.pytest_cache/` 和 `.ruff_cache/`（工具缓存）、`.git/`（版本库数据）。它们不是业务源码，也不会作为项目交付物。

## 目录职责

### `archive/`

保存原始比赛资料压缩包和解压副本，作为只读归档。

| 路径 | 内容 |
| --- | --- |
| `archive/本科组数据.zip` | 原始压缩包 |
| `archive/本科组数据/附件/附件1.xlsx` | 官方功能和行业标签原件 |
| `archive/本科组数据/附件/附件2.xlsx` | 官方参考网站清单原件 |
| `archive/本科组数据/附件/result1.csv` 至 `result4.csv` | 官方空结果模板副本 |

### `configs/`

| 文件 | 内容 |
| --- | --- |
| `configs/collection.json` | B01 需求方向、90 日窗口、关键词、来源、分页上限和访问间隔 |
| `configs/embedding.json` | multilingual-e5-small 的 revision、ONNX 文件、384 维、512 token、池化和归一化配置 |

### `data/`

保存数据说明、官方参考资料、原始字段、处理索引和本地模型。原始数据、处理数据、模型权重和政策快照由 `.gitignore` 排除。

| 路径 | 功能和内容 |
| --- | --- |
| `data/README.md` | 数据目录、字段、来源、质量标记和审计命令 |
| `data/reference/附件1.xlsx` | 官方功能和行业标签 |
| `data/reference/附件2.xlsx` | 官方参考网站 |
| `data/reference/labels.json` | 从附件 1 导出的 16 个功能和 30 个行业 |
| `data/reference/reference_sources.json` | 从附件 2 导出的 20 个网站 |
| `data/reference/web_policies/` | robots、API、条款和入口页面的本地政策快照 |
| `data/raw/B01/` | 采集配置、请求记录、响应字段和批次清单 |
| `data/processed/B01/` | 采集阶段统一索引、CSV、JSONL 和正文索引 |
| `data/models/multilingual-e5-small/` | multilingual-e5-small ONNX 权重和 tokenizer |
| `data/state/` | 运行状态预留目录 |

当前模型目录包括 `onnx/model_qint8_avx512_vnni.onnx` 和 `onnx/tokenizer.json`；使用设置见 `configs/embedding.json`。

`data/raw/` 保存从公开响应中选取并脱敏后的字段，不是所有网站的完整 HTTP 字节备份。`data/processed/` 是采集阶段索引；清洗运行结果放在 `results/`。

### `docs/`

| 文件或目录 | 功能 |
| --- | --- |
| `docs/competition/本科组赛题：AI应用场景的智能挖掘与机会评估系统.pdf` | 赛题原文 |
| `docs/AI_USAGE.md` | 重要 AI 操作、模型用量、复核边界、论文构建和交付记录 |
| `docs/MODELS.md` | 文本模型连接、认证、E5 向量模型和运行环境说明 |
| `docs/REVIEW_WORKBENCH.md` | 本地复核工作台启动、角色和人工标签写入规则 |
| `docs/PROJECT_GUIDE.md` | 项目总导航、文件夹说明和当前进度 |

### `opportunity/`

核心 Python 包。命令行、审计脚本和 Web 页面共用其中的业务逻辑。

| 文件 | 功能 |
| --- | --- |
| `__main__.py` | `python -m opportunity` 的 collect、clean、judge 等命令入口 |
| `collection.py` | 5 个来源的采集适配器和请求记录 |
| `cleaning.py` | URL 归一化、HTML 转文本、脱敏、相关性筛选和重复处理 |
| `embedding.py` | 本地 E5 tokenizer 和 ONNX Runtime 推理 |
| `files.py` | 项目根目录、JSON、JSONL、CSV 和运行路径辅助函数 |
| `model.py` | Codex Responses API 结构化调用、认证、用量和成本字段 |
| `judging.py` | 四条件机会判别、证据回指、官方标签校验和批次恢复 |
| `topics.py` | E5 向量、HDBSCAN、主题成员、质量指标、评分和敏感性 |
| `web.py` | FastAPI 复核 API、角色认证、正文查看、标签校验和决策者汇总 |
| `__init__.py` | Python 包标识 |

### `paper/`

| 路径 | 功能 | 当前状态 |
| --- | --- | --- |
| `paper/manuscript/main.tex` | 唯一论文主源文件 | 当前编辑源 |
| `paper/manuscript/sections/` | 引言、方法、数据、判别、主题、案例、结论和复现说明 | 当前编辑源 |
| `paper/manuscript/references.tex` | 24 条论文、API 和模型资料引用 | DOI、出版社记录和新增本地文献已核对 |
| `paper/figures/` | 17 张论文图，含 PNG、PDF 和 SVG | 由本地结果及实验输出生成 |
| `paper/EVIDENCE_LEDGER.md` | 正文主张、证据和限制 | 已完成 |
| `paper/RESULTS_REPORT.md` | B01 论文结果总表 | 已完成 |
| `paper/FIGURE_STORYBOARD.md` | 图件用途、来源和解释边界 | 已完成 |
| `paper/README.md` | 论文源、构建方式、修订交付和证据边界 | 已更新 |
| `paper/deliverables/*探索修订版_20261118*` | 新版 PDF 和 DOCX | 已完成编译与版面复核 |
| `paper/deliverables/*最终校验版_20261118*` | 当前一致性校验后的 PDF 和 DOCX | 已完成 TeX 编译、PDF 逐页检查和 DOCX 结构检查 |
| `submission/B01/` | 四份正式 CSV、论文、C2 策划案、AI 使用记录和验收说明 | 已生成 |
| `paper/deliverables/*校对版_20261109*` | 旧版 PDF 和 DOCX | 保留原样 |
| `paper/docx_render/` | Word 页面渲染预览 | 本地 QA |
| `paper/figure-versions/` | 早期图件版本 | 本地历史，不进入 Git |
| `paper/manuscript/docx_source/` | 早期 Word 展开文件 | 本地历史，不进入 Git |

论文是系统方法与 B01 应用实践。2,561 条标签已经登记为人工确认字段，正式主题和 C2 策划案已生成；其中 2,052 条标签来自用户授权的 AI 判断转登记，不构成独立盲标真值。

### `reports/`

| 文件 | 功能 |
| --- | --- |
| `ANALYSIS_MODELING_REPORT.md` | 赛题五项任务的输入、输出、约束、方法和校验条件 |
| `DATA_SOURCES.md` | 5 个来源、接口、政策、分页限制和样本边界 |
| `DATA_COLLECTION_B01.md` | B01 采集请求、来源数量、时间范围和覆盖限制 |
| `DATA_CLEANING_B01.md` | B01 清洗、去重、正文快照和质量标记 |
| `JUDGING_METHOD.md` | 机会判别条件、证据匹配和批处理恢复机制 |
| `JUDGING_B01.md` | 全量自动判别结果和复核状态 |
| `REVIEW_ASSISTED_B01.md` | 可见标签、盲复核、三方对照、AI 裁定和代理结果 |
| `TOPICS_CANDIDATE_B01.md` | 旧版 269 条模型候选聚类的限制说明 |
| `PROGRESS_REPORT.md` | 重要操作和阶段进展记录 |
| `VERIFY_REPORT.md` | 当前论文、数据关系、构建和页面验收 |

### `results/`

本地运行结果根目录，被 `.gitignore` 忽略。每个时间戳目录对应一次运行，文件名不会自动表示结果为正式或已验收。

| B01 运行目录 | 内容 | 状态 |
| --- | --- | --- |
| `20261107T164112993137Z` | `result1.csv`、`cleaning.json`、`records.jsonl` 和 2,561 份正文 | 清洗基线 |
| `20261107T171955877644Z` | 判别预览和单批次检查点 | 历史试运行 |
| `20261107T172307813709Z` | 判别探针 | 历史试运行 |
| `20261107T173708748922Z` | 全量判别、原模型 `result2.csv`、509 条复核队列及复核子目录 | 判别主运行 |
| `20261107T210556133301Z`、`211408888959Z`、`214922650910Z` | 多轮代理标签下的历史主题与评分 | 候选历史结果 |
| `20261107T222914355590Z` | 269 条原模型候选聚类和评分 | 非正式候选 |
| `20261108T043220466135Z` | 100 条代理机会的 `proxy_result3.csv`、`proxy_result4.csv` 和明细 | 最新代理候选 |
| `20261118T160530815667Z` | 2,561 条全量人工字段、正式 `result2.csv` 和来源登记 | 全量正式标签 |
| `20261118T192102321700Z` | 正式 `result3.csv`、`result4.csv`、主题和评分 | 正式主题结果 |

其中 `20261107T171955877644Z` 和 `20261107T172307813709Z` 是全量判别前的试运行/探针目录，不构成 B01 完整输出。四个以 `result3.csv`、`result4.csv` 命名的中间目录同样属于历史候选；正式生成的判断依据是 `topics.json` 中记录的 `label_source` 和状态字段。

`assistant_proxy_result2.csv` 是人工确认前生成的历史辅助结果。当前全量人工结果位于 `results/B01/20261118T160530815667Z/final/result2.csv`，2,561 条均登记为人工确认字段。

### `scripts/`

| 类型 | 文件 | 功能 |
| --- | --- | --- |
| 采集和模型 | `collect_data.py`、`download_model.py`、`check_model.py` | 采集入口、E5 下载、模型连接探针 |
| 参考资料 | `extract_reference.py` | 从官方 Excel 导出标签和来源 JSON |
| 数据审计 | `audit_data.py`、`audit_cleaning.py` | 批次字段、快照、去重和质量审计 |
| 判别与人工复核 | `build_review_queue.py`、`finalize_review.py`、`audit_judgements.py`、`audit_review_queue.py` | 建立复核队列、人工标签合并与审计 |
| AI 复核 | `assistant_review.py`、`compare_reviews.py`、`audit_assistant_review.py`、`audit_review_comparison.py` | 可见标签、盲复核、三方对照 |
| AI 裁定 | `adjudicate_reviews.py`、`audit_adjudication.py`、`build_proxy_result2.py`、`audit_proxy_result2.py` | 生成 AI 代理候选结果 |
| 主题评分 | `aggregate_topics.py`、`audit_topics.py` | 聚类、评分、敏感性和成员审计 |
| 论文图表 | `build_paper_materials.py` | 从 B01 结果生成 6 张图、证据账本和结果报告 |
| 论文 Word | `build_paper_docx.py`、`repair_docx_surface.py` | 从 TeX 生成 DOCX 并设置页面、字体和标题样式 |

### `templates/`

`templates/results/result1.csv` 至 `result4.csv` 是官方提交表头，均不含业务样本或标准答案。

### `tests/`

| 文件 | 测试范围 |
| --- | --- |
| `test_cleaning.py` | URL、正文、去重和质量标记 |
| `test_embedding.py` | 本地向量接口 |
| `test_model.py` | 结构化模型客户端 |
| `test_judging.py`、`test_judging_partitions.py` | 机会条件、证据和批次恢复 |
| `test_assistant_review.py` | AI 复核、盲复核和裁定 |
| `test_finalize_review.py` | 标签合并和待复核状态 |
| `test_topics.py` | 主题成员、评分和敏感性 |
| `test_web.py` | API、角色和官方标签校验 |

当前 `uv run pytest -q` 结果为 35 项通过。

### `web/`

复核工作台前端静态资源：`index.html` 页面骨架、`review.js` 批次/筛选/正文/保存/优先级交互，`review.css` 负责布局和响应式样式。决策看板使用 `dashboard.html`、`dashboard.js` 和 `dashboard.css`，后端为 `opportunity/web.py`。运行 `scripts/run_dashboard.ps1` 后可在 `/dashboard` 和 `/` 访问；本地验收截图位于 `最终交付_综合AI应用_20261119/docs/screenshots/`。

## B01 数据链路

```text
data/raw/B01/
  -> data/processed/B01/
  -> results/B01/20261107T164112993137Z/
       result1.csv + text/ + cleaning.json
  -> results/B01/20261107T173708748922Z/
       原模型 result2.csv + judgements.jsonl + review/
  -> review/assistant_adjudication/full_batch_proxy/
       assistant_proxy_result2.csv
  -> results/B01/20261108T043220466135Z/
       proxy_result3.csv + proxy_result4.csv
```

### 输出状态区别

- 清洗 `result1.csv` 结构审计通过，可描述为 B01 清洗结果。
- 判别运行的 `result2.csv` 是原模型全量结果；正式人工登记结果位于 `results/B01/20261118T160530815667Z/final/result2.csv`。
- `assistant_proxy_result2.csv` 是人工登记前的历史辅助结果，继续保留用于过程追溯。
- 正式 `result3.csv`、`result4.csv` 位于 `results/B01/20261118T192102321700Z/`，成员、分数和优先级审计通过。

## 查看进度和运行检查

### Git 和当前论文文件

```powershell
git status --short --branch
git log -5 --oneline
Get-ChildItem paper/deliverables -File | Sort-Object LastWriteTime
```

### 代码质量检查

```powershell
ruff format --check
ruff check
uv run pyright
uv run pytest -q
```

### B01 数据与标签审计

```powershell
uv run python scripts/audit_data.py --batch B01
uv run python scripts/audit_cleaning.py --run results/B01/20261107T164112993137Z
uv run python scripts/audit_judgements.py --run results/B01/20261107T173708748922Z
uv run python scripts/audit_human_adoption.py --run results/B01/20261107T173708748922Z
uv run python scripts/audit_topics.py --run results/B01/20261118T035924558190Z
```

### 论文入口

- 当前评审修订版 Word/PDF：`paper/deliverables/*评审修订版_20261119.*`
- 历史探索修订版 Word/PDF：`paper/deliverables/*探索修订版_20261118.*`
- 旧版校对件：`paper/deliverables/*校对版_20261109.*`
- TeX 主源：`paper/manuscript/main.tex`
- 结果总表：`paper/RESULTS_REPORT.md`
- 验收报告：`reports/VERIFY_REPORT.md`
- 重要操作记录：`docs/AI_USAGE.md`

## 当前交付检查

1. 论文 PDF、DOCX、四份结果表和策划案已进入对外查看目录。
2. 决策看板与复核工作台已完成本地浏览器验收，截图和日志已进入对外目录。
3. `interface/` 提供脱离采集和模型流程的界面部署单元，按其 `README.md` 即可启动。
4. 若需要独立研究评价，可将分层抽样盲标作为单独实验记录，不改变当前正式结果。

## 适用边界

- B01 来自公开 API、RSS 和有限分页，不代表 5 个网站的完整 90 日语料。
- `body` 是采集字段类型，不保证正文完整。
- 模型 confidence 是模型自评值，尚未进行概率校准。
- 结果表的机会置信度按机会方向输出，机会取原始自评值，非机会取 `1-confidence`；机会候选阈值为 0.5。
- 509 条复核材料经过用户阅读并确认，类别写入人工字段、备注为空；队列之外的记录仍沿用原模型标签。
- 2,052 条记录的人工字段来自用户授权的 AI 判断转登记；分类器比较只说明对 509 条逐条审阅标签的复现程度。
- 240 条负例按来源、正文类型和置信度定向抽取，不能无偏估计全量负例漏判率。
- 缺少互动数据时保留缺失，不填为零；没有配置服务价格时 token 成本未知。
- 复核工作台与决策看板已完成本地浏览器实操验收；交付包中的服务按需启动，不保持常驻。
- 论文将 B01 作为应用实践批次，C2 框架可用于应用端立项评估和产品试点设计，但不是已确认的用户需求、市场规模或产品效果。
- 2026-11-19 评审修订版使用 Tectonic 的 XeTeX 引擎编译；`paper/manuscript/main.pdf` 是历史编译文件，不代表当前修订版版面。
