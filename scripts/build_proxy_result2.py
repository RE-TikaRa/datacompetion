import argparse
import csv
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
from opportunity.judging import opportunity_confidence


def build_proxy_result2(run: Path, root: Path = ROOT) -> Path:
    run = run.resolve()
    if not run.is_relative_to(root / "results") or not run.is_dir():
        raise ValueError("判别运行目录必须位于项目 results 目录内。")
    model_rows = read_jsonl(run / "judgements.jsonl")
    batch_id = read_json(run / "judging.json")["batch_id"]
    proxy_path = run / "review" / "assistant_adjudication/assistant_review_proxy.jsonl"
    proxy_rows = read_jsonl(proxy_path)
    queue = read_jsonl(run / "review/review_queue.jsonl")
    model_by_id = {row["record_id"]: row for row in model_rows}
    proxy_by_id = {row["record_id"]: row for row in proxy_rows}
    queue_ids = {row["record_id"] for row in queue}
    model_ids = set(model_by_id)
    if len(model_by_id) != len(model_rows) or len(proxy_by_id) != len(proxy_rows):
        raise ValueError("模型结果或 AI 代理复核中存在重复记录编号。")
    if set(proxy_by_id) != queue_ids or not queue_ids <= model_ids:
        raise ValueError("AI 代理复核与原队列编号不一致。")
    output = run / "review/assistant_adjudication/full_batch_proxy"
    output.mkdir(parents=True, exist_ok=True)
    result_csv = output / "assistant_proxy_result2.csv"
    result_jsonl = output / "assistant_proxy_judgements.jsonl"
    summary_path = output / "assistant_proxy_summary.json"
    if all(path.is_file() for path in (result_csv, result_jsonl, summary_path)):
        return output
    if any(path.exists() for path in (result_csv, result_jsonl, summary_path)):
        raise ValueError("代理结果输出不完整，拒绝覆盖已有文件。")
    merged = []
    for model_row in model_rows:
        proxy = proxy_by_id.get(model_row["record_id"])
        if proxy is None:
            merged.append(
                {
                    **model_row,
                    "batch_id": batch_id,
                    "label_source": "original_model_not_sampled",
                    "review_status": "模型标签待复核",
                    "human_is_opportunity": None,
                }
            )
        else:
            merged.append(
                {
                    **model_row,
                    **proxy,
                    "batch_id": batch_id,
                    "label_source": proxy["review_basis"],
                    "review_status": "AI代理复核",
                    "human_is_opportunity": None,
                }
            )
    with (root / "templates/results/result2.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        columns = next(csv.reader(stream))
    rows = [
        [
            row["batch_id"],
            row["record_id"],
            int(row["is_opportunity"]),
            opportunity_confidence(row["confidence"], row["is_opportunity"]),
            row["functional_category"],
            row["industry"],
        ]
        for row in merged
    ]
    write_csv(result_csv, columns, rows)
    write_jsonl(result_jsonl, merged)
    write_json(
        summary_path,
        {
            "batch_id": merged[0]["batch_id"] if merged else None,
            "records": len(merged),
            "ai_proxy_reviewed_records": len(proxy_rows),
            "original_model_labels_not_sampled": len(merged) - len(proxy_rows),
            "model_positive_records_in_proxy_review": sum(
                row["model_is_opportunity"] for row in queue
            ),
            "ai_proxy_opportunities": sum(row["is_opportunity"] for row in proxy_rows),
            "human_truth_status": "未形成人工真值",
            "status": "AI代理复核候选result2，不是正式人工结果",
            "source_counts": {
                "ai_proxy_review": len(proxy_rows),
                "original_model_not_sampled": len(merged) - len(proxy_rows),
            },
            "proxy_result_file": result_csv.relative_to(root).as_posix(),
            "proxy_judgements_file": result_jsonl.relative_to(root).as_posix(),
            "proxy_review_source": proxy_path.relative_to(root).as_posix(),
        },
    )
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="导出区分 AI 代理与未抽样模型标签的候选 result2。"
    )
    parser.add_argument("--run", required=True, type=Path)
    args = parser.parse_args()
    cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
    try:
        output = build_proxy_result2(args.run)
    except ValueError as error:
        parser.error(str(error))
    print(
        json.dumps(
            {"output": output.relative_to(ROOT).as_posix()},
            ensure_ascii=False,
            indent=2,
        )
    )
