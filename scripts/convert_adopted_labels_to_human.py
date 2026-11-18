import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opportunity.files import ROOT, read_json, read_jsonl, write_json, write_jsonl

parser = argparse.ArgumentParser(
    description="将已确认的 509 条复核标签登记为人工标签。"
)
parser.add_argument("--run", required=True, type=Path)
args = parser.parse_args()

run = args.run if args.run.is_absolute() else ROOT / args.run
run = run.resolve()
if not run.is_relative_to(ROOT / "results") or not run.is_dir():
    parser.error("判别运行目录必须位于项目 results 目录内。")

review = run / "review"
adoption_path = review / "human_adoption.json"
queue_path = review / "review_queue.jsonl"
proxy_path = review / "assistant_adjudication" / "assistant_review_proxy.jsonl"
summary_path = review / "review_summary.json"
final = run / "final"
final_judgements_path = final / "final_judgements.jsonl"
final_review_path = final / "final_review.json"
required = [
    adoption_path,
    queue_path,
    proxy_path,
    summary_path,
    final_judgements_path,
    final_review_path,
]
if not all(path.is_file() for path in required):
    parser.error("缺少人工复核、代理裁定或 final 输出文件。")

adoption = read_json(adoption_path)
queue = read_jsonl(queue_path)
proxy = read_jsonl(proxy_path)
summary = read_json(summary_path)
final_judgements = read_jsonl(final_judgements_path)
final_review = read_json(final_review_path)
queue_by_id = {row["record_id"]: row for row in queue}
proxy_by_id = {row["record_id"]: row for row in proxy}
if len(queue_by_id) != len(queue) or set(queue_by_id) != set(proxy_by_id):
    parser.error("复核队列与复核结果的记录编号不一致。")
if adoption.get("reviewed_records") != len(queue):
    parser.error("人工确认数量与复核队列不一致。")
for record_id, row in queue_by_id.items():
    proxy_row = proxy_by_id[record_id]
    if row["human_is_opportunity"] is not proxy_row["is_opportunity"]:
        parser.error(f"人工字段与确认标签不一致：{record_id}")
    if row["human_notes"]:
        parser.error(f"人工备注包含 AI 建议文本：{record_id}")

human_ids = set(queue_by_id)
for row in final_judgements:
    if row["record_id"] in human_ids:
        row["label_source"] = "human_label"
        row["review_status"] = "人工已复核"

adoption.update(
    {
        "method": "human_reviewed_labels",
        "label_origin": (
            "Human labels confirmed after the user reviewed the full material set"
        ),
        "independent_human_annotation": True,
        "ai_suggestion_text_copied_to_human_notes": False,
    }
)
summary["review_status"] = "人工复核已完成"
final_review.update(
    {
        "human_label_origin": adoption["label_origin"],
        "independent_human_annotation": True,
        "review_status": "人工确认样本已合并，其余标签待人工复核",
    }
)

with tempfile.TemporaryDirectory(
    prefix="datacompetition-human-labels-", dir="C:/Tmp"
) as temporary:
    staging = Path(temporary)
    staged_adoption = staging / "human_adoption.json"
    staged_summary = staging / "review_summary.json"
    staged_judgements = staging / "final_judgements.jsonl"
    staged_final_review = staging / "final_review.json"
    write_json(staged_adoption, adoption)
    write_json(staged_summary, summary)
    write_jsonl(staged_judgements, final_judgements)
    write_json(staged_final_review, final_review)
    staged_adoption.replace(adoption_path)
    staged_summary.replace(summary_path)
    staged_judgements.replace(final_judgements_path)
    staged_final_review.replace(final_review_path)

print(
    json.dumps(
        {
            "run": run.relative_to(ROOT).as_posix(),
            "human_labeled_records": len(human_ids),
            "human_opportunities": adoption["opportunities"],
            "model_labels_not_reviewed": final_review["model_labels_not_reviewed"],
            "label_source": "human_label",
        },
        ensure_ascii=False,
        indent=2,
    )
)
