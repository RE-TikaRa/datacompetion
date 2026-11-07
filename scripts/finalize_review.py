import argparse
import json
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opportunity.files import (
    ROOT,
    read_json,
    read_jsonl,
    write_csv,
    write_json,
    write_jsonl,
)


def finalize(run: Path, root: Path = ROOT) -> Path:
    run = run.resolve()
    if not run.is_relative_to(root / "results") or not run.is_dir():
        raise ValueError("判别运行目录必须位于项目 results 目录内。")
    review_path = run / "review" / "review_queue.jsonl"
    if not review_path.exists():
        raise ValueError("找不到人工复核队列。")
    reviewed_rows = read_jsonl(review_path)
    labels = read_json(root / "data/reference/labels.json")
    functions = set(labels["functions"])
    industries = set(labels["industries"])
    pending = [
        row["record_id"] for row in reviewed_rows if row["review_status"] != "已复核"
    ]
    if pending:
        raise ValueError(f"复核队列尚有 {len(pending)} 条未完成，首条为 {pending[0]}。")
    errors = []
    for row in reviewed_rows:
        decision = row["human_is_opportunity"]
        if decision is None:
            errors.append(f"人工机会标签为空：{row['record_id']}")
        if decision is True:
            if row["human_functional_category"] not in functions:
                errors.append(f"人工功能类别非法：{row['record_id']}")
            if row["human_industry"] not in industries:
                errors.append(f"人工所属行业非法：{row['record_id']}")
        elif row["human_functional_category"] or row["human_industry"]:
            errors.append(f"非机会记录带有人工分类：{row['record_id']}")
    if errors:
        raise ValueError("；".join(errors[:5]))
    judging_run = run
    manifest = read_json(judging_run / "judging.json")
    if not manifest["complete"]:
        raise ValueError("全量模型判别尚未完成。")
    model_rows = read_jsonl(judging_run / "judgements.jsonl")
    if len(model_rows) != manifest["total_records"]:
        raise ValueError("模型判别记录没有完整覆盖清洗记录。")
    manual_rows = {row["record_id"]: row for row in reviewed_rows}
    rows = []
    human_reviewed = []
    for model_row in model_rows:
        review_row = manual_rows.get(model_row["record_id"])
        if review_row is None:
            rows.append(
                {
                    **model_row,
                    "human_is_opportunity": None,
                    "human_functional_category": "",
                    "human_industry": "",
                    "human_notes": "",
                    "review_status": "模型标签待复核",
                }
            )
            continue
        human_reviewed.append(review_row)
        rows.append(
            {
                **model_row,
                "is_opportunity": review_row["human_is_opportunity"],
                "functional_category": review_row["human_functional_category"],
                "industry": review_row["human_industry"],
                "human_notes": review_row["human_notes"],
                "review_status": "人工已复核",
            }
        )
    output = run / "final"
    output.mkdir(exist_ok=True)
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
            row["batch_id"],
            row["record_id"],
            int(row["is_opportunity"]),
            row["confidence"],
            row["functional_category"],
            row["industry"],
        ]
        for row in rows
    ]
    write_csv(output / "result2.csv", columns, csv_rows)
    write_jsonl(output / "final_judgements.jsonl", rows)
    write_json(
        output / "final_review.json",
        {
            "batch_id": rows[0]["batch_id"] if rows else None,
            "records": len(rows),
            "opportunities": sum(row["is_opportunity"] is True for row in rows),
            "human_reviewed_records": len(human_reviewed),
            "human_opportunities": sum(
                row["human_is_opportunity"] is True for row in human_reviewed
            ),
            "human_non_opportunities": sum(
                row["human_is_opportunity"] is False for row in human_reviewed
            ),
            "model_labels_not_reviewed": len(rows) - len(human_reviewed),
            "confidence_source": (
                "模型自评置信度，未进行概率校准；人工复核只覆盖人工复核清单中的记录"
            ),
            "review_status": "人工复核样本已合并，其余标签待复核",
        },
    )
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="根据已完成的人工复核导出正式 result2。"
    )
    parser.add_argument("--run", required=True, type=Path)
    args = parser.parse_args()
    cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
    try:
        output = finalize(args.run)
    except ValueError as error:
        parser.error(str(error))
    print(
        json.dumps(
            {"output": output.relative_to(ROOT).as_posix()},
            ensure_ascii=False,
            indent=2,
        )
    )
