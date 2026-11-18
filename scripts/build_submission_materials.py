import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def build_proposal(
    output: Path,
    topics: dict,
    scoring: dict,
    records: dict[str, dict],
) -> None:
    topic = next(item for item in topics["topics"] if item["topic_id"] == "C2")
    member_rows = [records[record_id] for record_id in topic["record_ids"]]
    source_lines = "\n".join(
        f"- `{row['record_id']}`：{row['source_name']}，《{row['title']}》；"
        f"{row['source_url']}"
        for row in member_rows
    )
    dimensions = topic["dimension_scores"]
    weights = scoring["scoring"]["weights"]
    text = f"""# C2 智能体证据工作台策划案

## 1 项目定位

C2 是 B01 正式全量标签结果中的第一优先级主题。主题包含
{topic["record_count"]} 条机会记录，覆盖 {topic["source_count"]} 个来源，价值分为
{topic["value_score"]:.2f}。主题成员涉及智能体架构、网络排障、医疗协同、代码模型、
论文检索、三维编辑和实时语音等方向，适合提炼为面向复杂任务的可审计智能体工作台。

该主题是公开记录中的技术需求集合，可作为应用端立项评估、需求访谈和产品试点设计的输入，不代表已经确认的市场规模、用户承诺或上线效果。

## 2 目标用户

- 需要处理多步骤知识检索和任务编排的研发团队；
- 需要让智能体执行工程排障、资料整理或内部流程的组织；
- 需要保留过程日志、引用来源和人工审批节点的高风险业务团队；
- 需要在本地或受控环境中部署代码模型、知识库和智能体工具的技术团队。

## 3 需求证据

成员记录共同指向以下需求线索：

1. 智能体需要在复杂任务中拆分步骤、调用工具并保留可追溯状态；
2. 工程排障、代码生成和论文检索需要同时处理结构化与非结构化资料；
3. 医疗、网络和企业流程等场景需要人工确认、权限隔离和操作审计；
4. 本地部署、模型切换、成本控制和结果引用影响实际采用成本。

## 4 最小可行产品

### 4.1 证据检索

接入用户授权的文档、代码库和公开来源，返回带来源链接、片段和时间的检索结果。每个生成结论都保存对应证据。

### 4.2 任务编排

将复杂任务拆成可观察的子任务，支持顺序执行、并行执行、失败重试和人工确认节点。每一步保存输入、工具调用、输出和状态。

### 4.3 结果回溯

为任务结果建立引用关系，支持查看原文、模型版本、提示模板、工具参数和修改记录。用户可以回退到任意检查点重新执行。

### 4.4 权限与审计

按项目、数据源和任务角色配置访问范围。医疗、网络安全和涉及外部写操作的任务必须经过人工审批，系统记录审批人和审批时间。

## 5 技术路线

1. 使用 multilingual-e5-small 生成多语言向量，建立文档和记录索引；
2. 使用混合检索召回候选片段，再由重排序模型筛选证据；
3. 使用结构化模型接口完成任务分解、工具选择和结果生成；
4. 通过状态机保存任务节点、重试次数、人工审批状态和检查点；
5. 采用 FastAPI 提供批次、记录、主题和审计接口；
6. 采用角色权限控制正文、证据、主题和导出文件的可见范围；
7. 对每次模型调用保存模型名、版本、输入输出 token 和成本配置。

## 6 实施安排

| 阶段 | 内容 | 验收指标 |
| --- | --- | --- |
| 数据接入 | 导入文档、代码库和来源配置 | 来源可追溯，正文和元数据完整 |
| 检索验证 | 建立向量索引和混合检索 | 引用片段能回到原文 |
| 编排开发 | 完成任务状态机和工具调用 | 任务状态可查询，失败可重试 |
| 审计上线 | 接入权限、审批和日志 | 高风险任务无法绕过审批 |
| 试点评估 | 选择两个低风险工程流程试用 | 引用正确率、完成时间和人工修改量达到预设阈值 |

## 7 评价指标

- 引用正确率：生成结论所引用片段与原文事实的一致比例；
- 任务完成时间：与人工基线比较端到端耗时；
- 人工修改量：用户对模型结果进行修改的字符数和段落数；
- 工具调用成功率：任务节点成功完成的比例；
- 审批遵循率：高风险任务经过人工节点的比例；
- 成本：按任务统计输入 token、输出 token、向量检索和存储成本。

## 8 风险控制

- 医疗、网络安全和外部写操作默认进入人工审批；
- 证据缺失时禁止生成确定性结论，改为返回待确认状态；
- 对模型输出和工具调用进行权限隔离，防止跨项目读取数据；
- 保存模型版本和提示模板，支持回放与问题定位；
- 对来源覆盖、正文完整度和主题边界进行定期抽样复核。

## 9 B01 评分依据

当前 C2 的维度分如下：

- 多源指向度：{dimensions["multi_source_direction"]:.2f}；
- 记录规模：{dimensions["record_scale"]:.2f}；
- 互动信号：{dimensions["interaction_signal"]:.2f}；
- 时间新近性：{dimensions["recency_signal"]:.2f}；
- 权重：多源指向度 {weights["multi_source_direction"]:.2f}、记录规模
  {weights["record_scale"]:.2f}、互动信号
  {weights["interaction_signal"]:.2f}、时间新近性
  {weights["recency_signal"]:.2f}。

## 10 成员证据

{source_lines}

## 11 结果边界

B01 的全量机会标签由用户授权将现有 AI 判别结果登记为人工确认字段。该登记完成了
比赛结果链路，但不等同于独立盲标实验。C2 的主题成员和评分用于应用端立项评估、产品
试点设计和验证指标制定，不能替代真实用户访谈、市场规模调查或上线效果评估。
"""
    output.write_text(text, encoding="utf-8")


parser = argparse.ArgumentParser(description="生成 B01 全量比赛提交材料。")
parser.add_argument("--formal-run", required=True, type=Path)
parser.add_argument("--full-label-run", required=True, type=Path)
parser.add_argument("--output", type=Path, default=Path("submission/B01"))
parser.add_argument(
    "--paper-pdf",
    type=Path,
    default=ROOT
    / "paper/deliverables/AI应用机会智能挖掘与评估系统_B01_最终校验版_20261119.pdf",
)
parser.add_argument(
    "--paper-docx",
    type=Path,
    default=ROOT
    / "paper/deliverables/AI应用机会智能挖掘与评估系统_B01_最终校验版_20261119.docx",
)
parser.add_argument("--paper-label", default="最终校验版_20261119")
args = parser.parse_args()

formal_run = (
    args.formal_run if args.formal_run.is_absolute() else ROOT / args.formal_run
)
formal_run = formal_run.resolve()
full_label_run = (
    args.full_label_run
    if args.full_label_run.is_absolute()
    else ROOT / args.full_label_run
).resolve()
output = args.output if args.output.is_absolute() else ROOT / args.output
output = output.resolve()
paper_pdf = args.paper_pdf if args.paper_pdf.is_absolute() else ROOT / args.paper_pdf
paper_docx = (
    args.paper_docx if args.paper_docx.is_absolute() else ROOT / args.paper_docx
)
paper_pdf = paper_pdf.resolve()
paper_docx = paper_docx.resolve()
if not paper_pdf.is_file() or not paper_docx.is_file():
    parser.error("指定的论文 PDF 或 DOCX 不存在。")
if not formal_run.is_relative_to(ROOT / "results"):
    parser.error("formal-run 必须位于项目 results 目录内。")
if not full_label_run.is_relative_to(ROOT / "results"):
    parser.error("full-label-run 必须位于项目 results 目录内。")
for required in (
    formal_run / "result3.csv",
    formal_run / "result4.csv",
    formal_run / "topics.json",
    formal_run / "scoring.json",
):
    if not required.is_file():
        parser.error(f"缺少正式结果文件：{required}")

cleaning_run = ROOT / "results/B01/20261107T164112993137Z"
records = {row["record_id"]: row for row in read_jsonl(cleaning_run / "records.jsonl")}
topics = read_json(formal_run / "topics.json")
scoring = read_json(formal_run / "scoring.json")

proposal_dir = output / "proposal"
results_dir = output / "results"
paper_dir = output / "paper"
docs_dir = output / "docs"
for directory in (proposal_dir, results_dir, paper_dir, docs_dir):
    directory.mkdir(parents=True, exist_ok=True)

build_proposal(
    proposal_dir / "C2_AI智能体证据工作台策划案.md", topics, scoring, records
)
for source, target_name in (
    (cleaning_run / "result1.csv", "result1.csv"),
    (full_label_run / "final/result2.csv", "result2.csv"),
    (formal_run / "result3.csv", "result3.csv"),
    (formal_run / "result4.csv", "result4.csv"),
):
    shutil.copy2(source, results_dir / target_name)
paper_pdf_name = f"论文_B01_{args.paper_label}.pdf"
paper_docx_name = f"论文_B01_{args.paper_label}.docx"
for source, target_name in (
    (paper_pdf, paper_pdf_name),
    (paper_docx, paper_docx_name),
):
    shutil.copy2(source, paper_dir / target_name)
shutil.copy2(ROOT / "docs/AI_USAGE.md", docs_dir / "AI_USAGE.md")
shutil.copy2(ROOT / "reports/VERIFY_REPORT.md", docs_dir / "VERIFY_REPORT.md")

manifest = {
    "batch_id": "B01",
    "formal_run": formal_run.relative_to(ROOT).as_posix(),
    "full_label_run": full_label_run.relative_to(ROOT).as_posix(),
    "cleaning_run": cleaning_run.relative_to(ROOT).as_posix(),
    "records": len(records),
    "opportunities": sum(
        1
        for row in read_jsonl(full_label_run / "final/final_judgements.jsonl")
        if row["is_opportunity"]
    ),
    "topics": len(topics["topics"]),
    "files": [
        "results/result1.csv",
        "results/result2.csv",
        "results/result3.csv",
        "results/result4.csv",
        "proposal/C2_AI智能体证据工作台策划案.md",
        f"paper/{paper_pdf_name}",
        f"paper/{paper_docx_name}",
        "docs/AI_USAGE.md",
        "docs/VERIFY_REPORT.md",
    ],
    "status": "完整比赛结果包，标签来源和证据边界见 docs/VERIFY_REPORT.md",
}
(output / "manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
(output / "README.md").write_text(
    "# B01 全量比赛提交材料\n\n"
    "本目录包含 B01 的四份正式 CSV、论文、C2 策划案、AI 使用记录和验收说明。\n\n"
    "标签已按用户授权将完整 AI 判别结果登记为人工确认字段。"
    "该登记完成正式结果链路，但不等同于独立盲标实验。\n\n"
    "正式结果来源见 `manifest.json`；原始采集数据、模型权重和运行缓存留在"
    "项目本地数据目录，不复制到提交包。\n",
    encoding="utf-8",
)
print(output)
