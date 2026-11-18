import argparse
import csv
import json
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opportunity.files import ROOT, read_json, read_jsonl
from opportunity.review_adoption import adoption_errors

parser = argparse.ArgumentParser(description="审计 AI 代理候选 result2 的来源和覆盖。")
parser.add_argument("--run", required=True, type=Path)
args = parser.parse_args()
cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
run = args.run if args.run.is_absolute() else ROOT / args.run
run = run.resolve()
if not run.is_relative_to(ROOT / "results") or not run.is_dir():
    parser.error("判别运行目录必须位于项目 results 目录内。")
output = run / "review/assistant_adjudication/full_batch_proxy"
required = [
    output / "assistant_proxy_result2.csv",
    output / "assistant_proxy_judgements.jsonl",
    output / "assistant_proxy_summary.json",
]
if not all(path.is_file() for path in required):
    parser.error("找不到完整的 AI 代理候选 result2 输出。")
model = read_jsonl(run / "judgements.jsonl")
proxy = read_jsonl(run / "review/assistant_adjudication/assistant_review_proxy.jsonl")
review_queue = read_jsonl(run / "review/review_queue.jsonl")
adoption_path = run / "review/human_adoption.json"
adoption = read_json(adoption_path) if adoption_path.exists() else None
merged = read_jsonl(output / "assistant_proxy_judgements.jsonl")
summary = read_json(output / "assistant_proxy_summary.json")
labels = read_json(ROOT / "data/reference/labels.json")
functions = set(labels["functions"])
industries = set(labels["industries"])
with (output / "assistant_proxy_result2.csv").open(
    encoding="utf-8-sig", newline=""
) as stream:
    csv_rows = list(csv.DictReader(stream))
model_by_id = {row["record_id"]: row for row in model}
proxy_by_id = {row["record_id"]: row for row in proxy}
queue_by_id = {row["record_id"]: row for row in review_queue}
merged_by_id = {row["record_id"]: row for row in merged}
errors = []
if set(proxy_by_id) != set(queue_by_id):
    errors.append("代理复核编号与原复核队列不一致。")
if adoption is None:
    if any(
        row["human_is_opportunity"] is not None
        or row["human_functional_category"]
        or row["human_industry"]
        or row["human_notes"]
        or row["review_status"] != "待人工复核"
        for row in review_queue
    ):
        errors.append("复核队列包含未记录来源的人工字段。")
else:
    errors.extend(adoption_errors(review_queue, proxy, adoption))
if len(merged) != len(model) or set(merged_by_id) != set(model_by_id):
    errors.append("代理候选 result2 没有完整覆盖原模型结果。")
if len(csv_rows) != len(merged) or {row["记录编号"] for row in csv_rows} != set(
    merged_by_id
):
    errors.append("代理候选 result2 CSV 与 JSONL 覆盖不一致。")
for record_id, row in merged_by_id.items():
    if record_id in proxy_by_id:
        expected = proxy_by_id[record_id]
        if row["reviewer"] != "Codex model, not human":
            errors.append(f"AI 代理标注来源不明确：{record_id}")
        if row["is_opportunity"] and row["industry"] not in industries:
            errors.append(f"AI 代理行业类别不合法：{record_id}")
        if row["is_opportunity"] and row["functional_category"] not in functions:
            errors.append(f"AI 代理功能类别不合法：{record_id}")
        if row["is_opportunity"] != expected["is_opportunity"]:
            errors.append(f"AI 代理标签未合并：{record_id}")
    else:
        original = model_by_id[record_id]
        if row["is_opportunity"] != original["is_opportunity"]:
            errors.append(f"未抽样模型标签被改动：{record_id}")
        if row["label_source"] != "original_model_not_sampled":
            errors.append(f"未抽样记录来源标记不明确：{record_id}")
    if row["is_opportunity"] and row["industry"] not in industries:
        errors.append(f"候选机会行业类别不合法：{record_id}")
    if row["is_opportunity"] and row["functional_category"] not in functions:
        errors.append(f"候选机会功能类别不合法：{record_id}")
    if not row["is_opportunity"] and (row["functional_category"] or row["industry"]):
        errors.append(f"非机会记录带有分类：{record_id}")
    csv_row = next((item for item in csv_rows if item["记录编号"] == record_id), None)
    if csv_row is not None and csv_row["是否构成机会"] != str(
        int(row["is_opportunity"])
    ):
        errors.append(f"CSV 标签与 JSONL 不一致：{record_id}")
if summary["records"] != len(model):
    errors.append("代理结果摘要记录数不一致。")
if adoption is None and summary["human_truth_status"] != "未形成人工真值":
    errors.append("代理结果没有标明缺少人工真值。")
result = {
    "records": len(merged),
    "ai_proxy_reviewed_records": len(proxy),
    "original_model_labels_not_sampled": len(merged) - len(proxy),
    "ai_proxy_opportunities": sum(row["is_opportunity"] for row in proxy),
    "human_adopted_records": adoption["reviewed_records"] if adoption else 0,
    "ai_suggestion_text_copied_to_human_notes": (
        adoption["ai_suggestion_text_copied_to_human_notes"] if adoption else False
    ),
    "errors": errors,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
if errors:
    sys.exit(1)
