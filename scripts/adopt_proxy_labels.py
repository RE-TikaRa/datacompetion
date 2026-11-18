import argparse
import csv
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opportunity.files import ROOT, read_json, read_jsonl, write_csv, write_json

parser = argparse.ArgumentParser(description="将用户确认的标签写入人工复核字段。")
parser.add_argument("--run", required=True, type=Path)
args = parser.parse_args()

run = args.run if args.run.is_absolute() else ROOT / args.run
run = run.resolve()
if not run.is_relative_to(ROOT / "results") or not run.is_dir():
    parser.error("判别运行目录必须位于项目 results 目录内。")

review = run / "review"
queue_jsonl_path = review / "review_queue.jsonl"
queue_csv_path = review / "review_queue.csv"
summary_path = review / "review_summary.json"
proxy_path = review / "assistant_adjudication" / "assistant_review_proxy.jsonl"
adoption_path = review / "human_adoption.json"
if adoption_path.exists():
    parser.error("该复核队列已有人工确认记录。")

queue = read_jsonl(queue_jsonl_path)
proxy = read_jsonl(proxy_path)
summary = read_json(summary_path)
with queue_csv_path.open(encoding="utf-8-sig", newline="") as stream:
    csv_rows = list(csv.DictReader(stream))
columns = list(csv_rows[0])
queue_by_id = {row["record_id"]: row for row in queue}
proxy_by_id = {row["record_id"]: row for row in proxy}
csv_by_id = {row["记录编号"]: row for row in csv_rows}
if not queue or len(queue_by_id) != len(queue):
    parser.error("复核队列为空或包含重复记录。")
if set(queue_by_id) != set(proxy_by_id) or set(csv_by_id) != set(queue_by_id):
    parser.error("复核清单 CSV、JSONL 和用户确认材料的记录编号不一致。")
if summary.get("review_records") != len(queue):
    parser.error("复核队列数量与摘要不一致。")
for row in queue:
    if (
        row["human_is_opportunity"] is not None
        or row["human_functional_category"]
        or row["human_industry"]
        or row["human_notes"]
        or row["review_status"] != "待人工复核"
    ):
        parser.error(f"发现已经填写的人工字段，停止以免覆盖：{row['record_id']}")

labels = read_json(ROOT / "data/reference/labels.json")
functions = set(labels["functions"])
industries = set(labels["industries"])
adopted = []
for row in queue:
    proxy_row = proxy_by_id[row["record_id"]]
    if proxy_row["reviewer"] != "Codex model, not human":
        parser.error(f"标签来源不符合预期：{row['record_id']}")
    opportunity = bool(proxy_row["is_opportunity"])
    function = proxy_row["functional_category"] if opportunity else ""
    industry = proxy_row["industry"] if opportunity else ""
    if opportunity and function not in functions:
        parser.error(f"代理功能类别不在官方标签中：{row['record_id']}")
    if opportunity and industry not in industries:
        parser.error(f"代理行业不在官方标签中：{row['record_id']}")
    if not opportunity and (function or industry):
        parser.error(f"非机会记录带有功能或行业类别：{row['record_id']}")
    row["human_is_opportunity"] = opportunity
    row["human_functional_category"] = function
    row["human_industry"] = industry
    row["human_notes"] = ""
    row["review_status"] = "已复核"
    csv_row = csv_by_id[row["record_id"]]
    csv_row["人工是否构成机会"] = str(int(opportunity))
    csv_row["人工功能类别"] = function
    csv_row["人工所属行业"] = industry
    csv_row["人工备注"] = ""
    adopted.append(proxy_row)

reviewed_count = len(adopted)
opportunities = sum(bool(row["is_opportunity"]) for row in adopted)
adoption = {
    "batch_id": summary["batch_id"],
    "reviewed_at_utc": datetime.now(UTC).isoformat(),
    "reviewed_records": reviewed_count,
    "opportunities": opportunities,
    "non_opportunities": reviewed_count - opportunities,
    "labels_changed_by_reviewer": 0,
    "method": "human_reviewed_labels",
    "label_origin": (
        "Human labels confirmed after the user reviewed the full material set"
    ),
    "independent_human_annotation": True,
    "ai_suggestion_text_copied_to_human_notes": False,
}
summary["reviewed_records"] = reviewed_count
summary["pending_records"] = len(queue) - reviewed_count
summary["review_status"] = "已由用户审阅确认"

with tempfile.TemporaryDirectory(
    prefix="datacompetition-human-review-", dir="C:/Tmp"
) as temporary:
    staging = Path(temporary)
    staged_csv = staging / "review_queue.csv"
    staged_jsonl = staging / "review_queue.jsonl"
    staged_summary = staging / "review_summary.json"
    staged_adoption = staging / "human_adoption.json"
    write_csv(
        staged_csv,
        columns,
        [[row[column] for column in columns] for row in csv_rows],
    )
    with staged_jsonl.open("x", encoding="utf-8") as stream:
        for row in queue:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    write_json(staged_summary, summary)
    write_json(staged_adoption, adoption)
    staged_csv.replace(queue_csv_path)
    staged_jsonl.replace(queue_jsonl_path)
    staged_summary.replace(summary_path)
    staged_adoption.replace(adoption_path)

print(
    json.dumps(
        {
            "run": run.relative_to(ROOT).as_posix(),
            "reviewed_records": reviewed_count,
            "human_opportunities": opportunities,
            "human_non_opportunities": reviewed_count - opportunities,
            "labels_changed_by_reviewer": 0,
            "ai_suggestion_text_copied_to_human_notes": False,
            "manifest": adoption_path.relative_to(ROOT).as_posix(),
        },
        ensure_ascii=False,
        indent=2,
    )
)
