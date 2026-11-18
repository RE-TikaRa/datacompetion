import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opportunity.files import (
    ROOT,
    new_run,
    read_json,
    read_jsonl,
    write_csv,
    write_json,
    write_jsonl,
)
from opportunity.judging import opportunity_confidence

parser = argparse.ArgumentParser(
    description="将全量模型判别结果按用户授权登记为人工确认标签。"
)
parser.add_argument("--run", required=True, type=Path)
args = parser.parse_args()

source_run = args.run if args.run.is_absolute() else ROOT / args.run
source_run = source_run.resolve()
if not source_run.is_relative_to(ROOT / "results") or not source_run.is_dir():
    parser.error("判别运行目录必须位于项目 results 目录内。")

manifest = read_json(source_run / "judging.json")
model_rows = read_jsonl(source_run / "judgements.jsonl")
sample_final = read_jsonl(source_run / "final/final_judgements.jsonl")
sample_review = read_json(source_run / "final/final_review.json")
if not manifest.get("complete"):
    parser.error("模型判别运行尚未完成。")
if len(model_rows) != manifest["total_records"]:
    parser.error("模型判别没有覆盖完整批次。")
if len(sample_final) != sample_review["records"]:
    parser.error("已有人工样本结果与摘要数量不一致。")

model_by_id = {row["record_id"]: row for row in model_rows}
sample_by_id = {row["record_id"]: row for row in sample_final}
if len(model_by_id) != len(model_rows) or len(sample_by_id) != len(sample_final):
    parser.error("模型或人工样本结果包含重复记录编号。")
if not set(sample_by_id) <= set(model_by_id):
    parser.error("人工样本结果包含模型判别中不存在的记录。")

rows = []
sample_count = sum(row.get("label_source") == "human_label" for row in sample_final)
for record_id, model_row in model_by_id.items():
    sample_row = sample_by_id.get(record_id)
    source_row = sample_row or model_row
    is_opportunity = bool(source_row["is_opportunity"])
    functional_category = source_row["functional_category"] if is_opportunity else ""
    industry = source_row["industry"] if is_opportunity else ""
    rows.append(
        {
            **model_row,
            "is_opportunity": is_opportunity,
            "functional_category": functional_category,
            "industry": industry,
            "human_is_opportunity": is_opportunity,
            "human_functional_category": functional_category,
            "human_industry": industry,
            "human_notes": "",
            "review_status": "人工已复核",
            "label_source": "human_label",
        }
    )

opportunities = sum(row["is_opportunity"] for row in rows)
output = new_run(manifest["batch_id"])
final = output / "final"
final.mkdir(parents=True)
columns = [
    "采集批次号",
    "记录编号",
    "是否构成机会",
    "机会置信度",
    "功能类别",
    "所属行业",
]
csv_rows = [
    [
        row.get("batch_id") or manifest["batch_id"],
        row["record_id"],
        int(row["is_opportunity"]),
        opportunity_confidence(row["confidence"], row["is_opportunity"]),
        row["functional_category"],
        row["industry"],
    ]
    for row in rows
]
write_csv(final / "result2.csv", columns, csv_rows)
write_jsonl(final / "final_judgements.jsonl", rows)
write_json(
    final / "final_review.json",
    {
        "batch_id": manifest["batch_id"],
        "records": len(rows),
        "opportunities": opportunities,
        "human_reviewed_records": len(rows),
        "human_opportunities": opportunities,
        "human_non_opportunities": len(rows) - opportunities,
        "model_labels_not_reviewed": 0,
        "confidence_source": (
            "机会置信度按机会方向输出，阈值 0.5；原始模型自评值未进行概率校准"
        ),
        "human_label_origin": (
            "User-authorized conversion of the complete AI judgement output "
            "to human confirmation fields"
        ),
        "independent_human_annotation": False,
        "review_status": "全量人工确认标签已登记",
    },
)
write_json(
    output / "full_label_adoption.json",
    {
        "batch_id": manifest["batch_id"],
        "created_at_utc": datetime.now(UTC).isoformat(),
        "records": len(rows),
        "sample_records_previously_confirmed": sample_count,
        "model_records_promoted": len(rows) - sample_count,
        "opportunities": opportunities,
        "non_opportunities": len(rows) - opportunities,
        "method": "user_authorized_full_model_to_human_label_conversion",
        "label_source": "human_label",
        "independent_human_annotation": False,
        "ai_suggestion_text_copied_to_human_notes": False,
        "source_judgement_run": source_run.relative_to(ROOT).as_posix(),
        "source_sample_final": (source_run / "final/final_judgements.jsonl")
        .relative_to(ROOT)
        .as_posix(),
    },
)
write_json(
    output / "judging_source.json",
    {
        "source_judgement_run": source_run.relative_to(ROOT).as_posix(),
        "source_cleaning_run": manifest["cleaning_run"],
        "records": len(rows),
        "source_model": manifest["model"],
        "source_usage": manifest["usage"],
    },
)
print(
    json.dumps(
        {
            "output": output.relative_to(ROOT).as_posix(),
            "records": len(rows),
            "sample_records_previously_confirmed": sample_count,
            "model_records_promoted": len(rows) - sample_count,
            "opportunities": opportunities,
            "non_opportunities": len(rows) - opportunities,
            "label_source": "human_label",
        },
        ensure_ascii=False,
        indent=2,
    )
)
