import argparse
import json
import sys
from collections import Counter
from io import TextIOWrapper
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opportunity.files import ROOT, read_json, read_jsonl, write_csv, write_json

parser = argparse.ArgumentParser(description="比较原模型、可见标签和盲复核结果。")
parser.add_argument("--run", required=True, type=Path)
args = parser.parse_args()
cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
run = args.run if args.run.is_absolute() else ROOT / args.run
run = run.resolve()
if not run.is_relative_to(ROOT / "results") or not run.is_dir():
    parser.error("判别运行目录必须位于项目 results 目录内。")
review = run / "review"
queue = read_jsonl(review / "review_queue.jsonl")
visible = read_jsonl(review / "assistant_review/assistant_review.jsonl")
blind = read_jsonl(review / "assistant_review_blind/assistant_review.jsonl")
visible_by_id = {row["record_id"]: row for row in visible}
blind_by_id = {row["record_id"]: row for row in blind}
queue_by_id = {row["record_id"]: row for row in queue}
expected = set(queue_by_id)
if set(visible_by_id) != expected or set(blind_by_id) != expected:
    parser.error("两次辅助复核没有覆盖相同的复核队列。")
rows = []
consensus_rows = []
stable_positive_rows = []
counts = Counter()
for record_id in sorted(expected):
    original = bool(queue_by_id[record_id]["model_is_opportunity"])
    visible_value = visible_by_id[record_id]["is_opportunity"]
    blind_value = blind_by_id[record_id]["is_opportunity"]
    state = (original, visible_value, blind_value)
    counts[state] += 1
    categories = {
        (
            queue_by_id[record_id]["model_functional_category"],
            queue_by_id[record_id]["model_industry"],
        ),
        (
            visible_by_id[record_id]["functional_category"],
            visible_by_id[record_id]["industry"],
        ),
        (
            blind_by_id[record_id]["functional_category"],
            blind_by_id[record_id]["industry"],
        ),
    }
    category_disagreement = len(categories) > 1
    visible_boundary = visible_by_id[record_id]["boundary_case"]
    blind_boundary = blind_by_id[record_id]["boundary_case"]
    visible_category = (
        visible_by_id[record_id]["functional_category"],
        visible_by_id[record_id]["industry"],
    )
    blind_category = (
        blind_by_id[record_id]["functional_category"],
        blind_by_id[record_id]["industry"],
    )
    stable_positive = (
        visible_value
        and blind_value
        and visible_category == blind_category
        and not visible_boundary
        and not blind_boundary
    )
    if stable_positive:
        stable_positive_rows.append(
            [
                queue_by_id[record_id]["batch_id"],
                record_id,
                queue_by_id[record_id]["source_name"],
                queue_by_id[record_id]["content_kind"],
                queue_by_id[record_id]["title"],
                queue_by_id[record_id]["content_path"],
                int(original),
                visible_by_id[record_id]["confidence"],
                blind_by_id[record_id]["confidence"],
                visible_category[0],
                visible_category[1],
                visible_by_id[record_id]["rationale"],
                blind_by_id[record_id]["rationale"],
                "两轮辅助判断稳定，仍需真人确认",
            ]
        )
    reasons = []
    if len({original, visible_value, blind_value}) > 1:
        reasons.append("判定分歧")
    if visible_boundary or blind_boundary:
        reasons.append("存在边界情况")
    if category_disagreement:
        reasons.append("功能或行业分类分歧")
    reason = "两次辅助复核判断一致" if not reasons else "；".join(reasons)
    consensus_rows.append(
        [
            queue_by_id[record_id]["batch_id"],
            record_id,
            queue_by_id[record_id]["source_name"],
            queue_by_id[record_id]["content_kind"],
            queue_by_id[record_id]["title"],
            queue_by_id[record_id]["content_path"],
            int(original),
            int(visible_value),
            int(blind_value),
            "" if visible_value != blind_value else int(visible_value),
            visible_value != blind_value or bool(reasons),
            reason,
        ]
    )
    if reasons:
        rows.append(
            [
                queue_by_id[record_id]["batch_id"],
                record_id,
                queue_by_id[record_id]["source_name"],
                queue_by_id[record_id]["content_kind"],
                queue_by_id[record_id]["title"],
                queue_by_id[record_id]["content_path"],
                int(original),
                int(visible_value),
                int(blind_value),
                queue_by_id[record_id]["model_confidence"],
                visible_by_id[record_id]["confidence"],
                blind_by_id[record_id]["confidence"],
                visible_boundary,
                blind_boundary,
                queue_by_id[record_id]["model_functional_category"],
                queue_by_id[record_id]["model_industry"],
                visible_by_id[record_id]["functional_category"],
                visible_by_id[record_id]["industry"],
                blind_by_id[record_id]["functional_category"],
                blind_by_id[record_id]["industry"],
                visible_by_id[record_id]["rationale"],
                blind_by_id[record_id]["rationale"],
                reason,
            ]
        )
output = review / "review_comparison_blind"
output.mkdir(exist_ok=True)
summary_path = output / "comparison_summary.json"
if all(
    (output / name).is_file()
    for name in ("comparison_summary.json", "consensus.csv", "triage.csv")
):
    if not (output / "stable_positive_candidates.csv").is_file():
        write_csv(
            output / "stable_positive_candidates.csv",
            [
                "采集批次号",
                "记录编号",
                "来源网站名称",
                "内容类型",
                "标题",
                "正文路径",
                "原模型判断",
                "可见标签辅助置信度",
                "盲复核置信度",
                "共识功能类别",
                "共识所属行业",
                "可见标签理由",
                "盲复核理由",
                "状态",
            ],
            stable_positive_rows,
        )
    stability_summary = output / "stability_summary.json"
    if not stability_summary.exists():
        write_json(
            stability_summary,
            {
                "stable_positive_candidates": len(stable_positive_rows),
                "status": "模型判断稳定候选，真人尚未确认",
            },
        )
    summary = read_json(summary_path)
    print(
        json.dumps(
            {
                "output": output.relative_to(ROOT).as_posix(),
                "records": summary["records"],
                "visible_blind_agreement": summary["visible_blind_agreement"],
                "all_three_agree": summary["all_three_agree"],
                "triage_records": summary["triage_records"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit
write_csv(
    output / "triage.csv",
    [
        "采集批次号",
        "记录编号",
        "来源网站名称",
        "内容类型",
        "标题",
        "正文路径",
        "原模型判断",
        "可见标签辅助判断",
        "盲复核判断",
        "原模型置信度",
        "可见标签辅助置信度",
        "盲复核置信度",
        "可见标签边界",
        "盲复核边界",
        "原模型功能类别",
        "原模型所属行业",
        "可见标签辅助功能类别",
        "可见标签辅助所属行业",
        "盲复核功能类别",
        "盲复核所属行业",
        "可见标签理由",
        "盲复核理由",
        "建议",
    ],
    rows,
)
write_csv(
    output / "stable_positive_candidates.csv",
    [
        "采集批次号",
        "记录编号",
        "来源网站名称",
        "内容类型",
        "标题",
        "正文路径",
        "原模型判断",
        "可见标签辅助置信度",
        "盲复核置信度",
        "共识功能类别",
        "共识所属行业",
        "可见标签理由",
        "盲复核理由",
        "状态",
    ],
    stable_positive_rows,
)
write_json(
    output / "stability_summary.json",
    {
        "stable_positive_candidates": len(stable_positive_rows),
        "status": "模型判断稳定候选，真人尚未确认",
    },
)
write_csv(
    output / "consensus.csv",
    [
        "采集批次号",
        "记录编号",
        "来源网站名称",
        "内容类型",
        "标题",
        "正文路径",
        "原模型判断",
        "可见标签辅助判断",
        "盲复核判断",
        "两次辅助复核共识判断",
        "需真人确认",
        "状态说明",
    ],
    consensus_rows,
)
visible_blind_agreement = sum(
    visible_by_id[record_id]["is_opportunity"]
    == blind_by_id[record_id]["is_opportunity"]
    for record_id in expected
)
original_visible_agreement = sum(
    bool(queue_by_id[record_id]["model_is_opportunity"])
    == visible_by_id[record_id]["is_opportunity"]
    for record_id in expected
)
original_blind_agreement = sum(
    bool(queue_by_id[record_id]["model_is_opportunity"])
    == blind_by_id[record_id]["is_opportunity"]
    for record_id in expected
)
stable_positive = sum(
    visible_by_id[record_id]["is_opportunity"]
    and visible_by_id[record_id]["is_opportunity"]
    == blind_by_id[record_id]["is_opportunity"]
    for record_id in expected
)
stable_negative = sum(
    not visible_by_id[record_id]["is_opportunity"]
    and visible_by_id[record_id]["is_opportunity"]
    == blind_by_id[record_id]["is_opportunity"]
    for record_id in expected
)
write_json(
    output / "comparison_summary.json",
    {
        "records": len(queue),
        "visible_blind_agreement": visible_blind_agreement,
        "original_visible_agreement": original_visible_agreement,
        "original_blind_agreement": original_blind_agreement,
        "stable_assistant_positive": stable_positive,
        "stable_assistant_negative": stable_negative,
        "all_three_agree": sum(
            value for state, value in counts.items() if len(set(state)) == 1
        ),
        "three_way_states": {
            "|".join(map(str, state)): value for state, value in counts.items()
        },
        "triage_records": len(rows),
        "status": "辅助对照，真人尚未确认",
    },
)
print(
    json.dumps(
        {
            "output": output.relative_to(ROOT).as_posix(),
            "records": len(queue),
            "visible_blind_agreement": visible_blind_agreement,
            "all_three_agree": sum(
                value for state, value in counts.items() if len(set(state)) == 1
            ),
            "triage_records": len(rows),
        },
        ensure_ascii=False,
        indent=2,
    )
)
