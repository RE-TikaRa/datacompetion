import argparse
import csv
import json
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opportunity.files import ROOT, read_json, read_jsonl
from opportunity.judging import exact_source_quote

parser = argparse.ArgumentParser(description="检查 AI 裁定代理复核结果。")
parser.add_argument("--run", required=True, type=Path)
args = parser.parse_args()
cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
run = args.run if args.run.is_absolute() else ROOT / args.run
run = run.resolve()
if not run.is_relative_to(ROOT / "results") or not run.is_dir():
    parser.error("判别运行目录必须位于项目 results 目录内。")
review = run / "review"
output = review / "assistant_adjudication"
queue = read_jsonl(review / "review_queue.jsonl")
adjudicated = read_jsonl(output / "assistant_adjudication.jsonl")
proxy = read_jsonl(output / "assistant_review_proxy.jsonl")
summary = read_json(output / "assistant_adjudication_summary.json")
with (review / "review_comparison_blind/triage.csv").open(
    encoding="utf-8-sig", newline=""
) as stream:
    triage = list(csv.DictReader(stream))
with (output / "assistant_adjudication.csv").open(
    encoding="utf-8-sig", newline=""
) as stream:
    adjudication_csv = list(csv.DictReader(stream))
with (output / "assistant_review_proxy.csv").open(
    encoding="utf-8-sig", newline=""
) as stream:
    proxy_csv = list(csv.DictReader(stream))
queue_by_id = {row["record_id"]: row for row in queue}
adjudicated_by_id = {row["record_id"]: row for row in adjudicated}
proxy_by_id = {row["record_id"]: row for row in proxy}
triage_ids = {row["记录编号"] for row in triage}
errors = []
if set(adjudicated_by_id) != triage_ids:
    errors.append("AI 裁定没有完整覆盖真人优先查看清单。")
if set(proxy_by_id) != set(queue_by_id):
    errors.append("AI 代理复核没有覆盖全部复核队列。")
if (
    len(adjudication_csv) != len(adjudicated)
    or {row["记录编号"] for row in adjudication_csv} != triage_ids
):
    errors.append("AI 裁定 CSV 与 JSONL 范围不一致。")
if len(proxy_csv) != len(proxy) or {row["记录编号"] for row in proxy_csv} != set(
    queue_by_id
):
    errors.append("AI 代理复核 CSV 与 JSONL 范围不一致。")
adjudication_csv_by_id = {row["记录编号"]: row for row in adjudication_csv}
proxy_csv_by_id = {row["记录编号"]: row for row in proxy_csv}
for record_id, item in adjudicated_by_id.items():
    proxy_item = proxy_by_id.get(record_id)
    if proxy_item is None:
        continue
    if proxy_item["is_opportunity"] != item["is_opportunity"]:
        errors.append(f"代理结果与 AI 裁定不一致：{record_id}")
    csv_item = adjudication_csv_by_id.get(record_id)
    if csv_item is not None and csv_item["AI裁定判断"] != str(
        int(item["is_opportunity"])
    ):
        errors.append(f"AI 裁定 CSV 判断不一致：{record_id}")
for record_id, item in proxy_by_id.items():
    csv_item = proxy_csv_by_id.get(record_id)
    if csv_item is not None and csv_item["AI代理复核判断"] != str(
        int(item["is_opportunity"])
    ):
        errors.append(f"AI 代理复核 CSV 判断不一致：{record_id}")
labels = read_json(ROOT / "data/reference/labels.json")
functions = set(labels["functions"])
industries = set(labels["industries"])
for item in proxy:
    record_id = item["record_id"]
    source = queue_by_id.get(record_id)
    if source is None:
        continue
    if item["reviewer"] != "Codex model, not human":
        errors.append(f"代理复核标注来源不明确：{record_id}")
    if item["is_opportunity"] and item["functional_category"] not in functions:
        errors.append(f"代理功能类别不合法：{record_id}")
    if item["is_opportunity"] and item["industry"] not in industries:
        errors.append(f"代理行业类别不合法：{record_id}")
    if not item["is_opportunity"] and (item["functional_category"] or item["industry"]):
        errors.append(f"代理非机会记录带有分类：{record_id}")
    text = (ROOT / source["content_path"]).read_text(encoding="utf-8")
    if any(exact_source_quote(quote, text) is None for quote in item["evidence"]):
        errors.append(f"代理复核证据不在正文中：{record_id}")
for row in queue:
    if (
        row["human_is_opportunity"] is not None
        or row["human_functional_category"]
        or row["human_industry"]
        or row["human_notes"]
        or row["review_status"] != "待人工复核"
    ):
        errors.append(f"原人工队列被改写：{row['record_id']}")
if summary["review_records"] != len(queue):
    errors.append("代理复核摘要数量与队列不一致。")
if summary["adjudicated_disputed_records"] != len(triage_ids):
    errors.append("AI 裁定摘要数量与真人优先清单不一致。")
if summary["human_truth_status"] != "未形成人工真值":
    errors.append("代理复核摘要没有说明仍缺少人工真值。")
result = {
    "queue_records": len(queue),
    "adjudicated_records": len(adjudicated),
    "proxy_records": len(proxy),
    "proxy_opportunities": sum(item["is_opportunity"] for item in proxy),
    "human_queue_untouched": not any(
        row["human_is_opportunity"] is not None
        or row["human_functional_category"]
        or row["human_industry"]
        or row["human_notes"]
        or row["review_status"] != "待人工复核"
        for row in queue
    ),
    "errors": errors,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
if errors:
    sys.exit(1)
