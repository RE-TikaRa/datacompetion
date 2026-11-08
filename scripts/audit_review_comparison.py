import argparse
import csv
import json
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opportunity.files import ROOT, read_json, read_jsonl

parser = argparse.ArgumentParser(description="检查三方辅助复核对照和候选清单。")
parser.add_argument("--run", required=True, type=Path)
args = parser.parse_args()
cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
run = args.run if args.run.is_absolute() else ROOT / args.run
run = run.resolve()
if not run.is_relative_to(ROOT / "results") or not run.is_dir():
    parser.error("判别运行目录必须位于项目 results 目录内。")
review = run / "review"
output = review / "review_comparison_blind"
queue = read_jsonl(review / "review_queue.jsonl")
visible = read_jsonl(review / "assistant_review/assistant_review.jsonl")
blind = read_jsonl(review / "assistant_review_blind/assistant_review.jsonl")
with (output / "consensus.csv").open(encoding="utf-8-sig", newline="") as stream:
    consensus = list(csv.DictReader(stream))
with (output / "triage.csv").open(encoding="utf-8-sig", newline="") as stream:
    triage = list(csv.DictReader(stream))
with (output / "stable_positive_candidates.csv").open(
    encoding="utf-8-sig", newline=""
) as stream:
    stable = list(csv.DictReader(stream))
summary = read_json(output / "comparison_summary.json")
stability = read_json(output / "stability_summary.json")
visible_by_id = {row["record_id"]: row for row in visible}
blind_by_id = {row["record_id"]: row for row in blind}
queue_by_id = {row["record_id"]: row for row in queue}
expected_ids = set(queue_by_id)
errors = []
if set(visible_by_id) != expected_ids or set(blind_by_id) != expected_ids:
    errors.append("原队列、可见标签辅助复核与盲复核的编号集合不一致。")
if (
    len(consensus) != len(queue)
    or {row["记录编号"] for row in consensus} != expected_ids
):
    errors.append("共识表没有恰好覆盖 509 条复核记录。")
expected_triage = set()
expected_stable = set()
visible_blind_agreement = 0
all_three_agree = 0
for record_id in expected_ids:
    source = queue_by_id[record_id]
    first = visible_by_id[record_id]
    second = blind_by_id[record_id]
    model_label = bool(source["model_is_opportunity"])
    label_set = {model_label, first["is_opportunity"], second["is_opportunity"]}
    category_set = {
        (source["model_functional_category"], source["model_industry"]),
        (first["functional_category"], first["industry"]),
        (second["functional_category"], second["industry"]),
    }
    has_boundary = first["boundary_case"] or second["boundary_case"]
    if first["is_opportunity"] == second["is_opportunity"]:
        visible_blind_agreement += 1
    if len(label_set) == 1:
        all_three_agree += 1
    if len(label_set) > 1 or has_boundary or len(category_set) > 1:
        expected_triage.add(record_id)
    if (
        first["is_opportunity"]
        and second["is_opportunity"]
        and (first["functional_category"], first["industry"])
        == (second["functional_category"], second["industry"])
        and not has_boundary
    ):
        expected_stable.add(record_id)
if {row["记录编号"] for row in triage} != expected_triage:
    errors.append("三方分歧、边界或分类差异清单不完整。")
if {row["记录编号"] for row in stable} != expected_stable:
    errors.append("高稳定机会候选与筛选规则不一致。")
if summary["visible_blind_agreement"] != visible_blind_agreement:
    errors.append("辅助复核一致数量与明细不一致。")
if summary["all_three_agree"] != all_three_agree:
    errors.append("三方一致数量与明细不一致。")
if summary["triage_records"] != len(expected_triage):
    errors.append("真人优先查看数量与明细不一致。")
if stability["stable_positive_candidates"] != len(expected_stable):
    errors.append("高稳定机会候选数量与明细不一致。")
result = {
    "records": len(queue),
    "visible_blind_agreement": visible_blind_agreement,
    "all_three_agree": all_three_agree,
    "human_attention_records": len(triage),
    "stable_positive_candidates": len(stable),
    "errors": errors,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
if errors:
    sys.exit(1)
