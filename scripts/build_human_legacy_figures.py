import json
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
CLEANING = ROOT / "results/B01/20261107T164112993137Z"
JUDGING = ROOT / "results/B01/20261107T173708748922Z"
HUMAN = JUDGING / "final/final_judgements.jsonl"
TOPICS = ROOT / "results/B01/20261118T035924558190Z/topics.json"
FIGURES = ROOT / "paper/figures"
MANUSCRIPT_FIGURES = ROOT / "paper/manuscript/figures"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def save(fig, stem: str) -> None:
    for extension in ("png", "pdf", "svg"):
        fig.savefig(FIGURES / f"{stem}.{extension}", bbox_inches="tight")
        fig.savefig(MANUSCRIPT_FIGURES / f"{stem}.{extension}", bbox_inches="tight")
    plt.close(fig)


plt.rcParams.update(
    {
        "font.family": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)
cleaning = read_json(CLEANING / "cleaning.json")
model = read_jsonl(JUDGING / "judgements.jsonl")
human = read_jsonl(HUMAN)
topics = read_json(TOPICS)["topics"]

stages = [
    ("原始字段出现", cleaning["raw_record_appearances"]),
    ("来源 URL 唯一", cleaning["url_unique_records"]),
    ("最终清洗记录", cleaning["retained_records"]),
    ("模型候选机会", sum(row["is_opportunity"] for row in model)),
    ("人工确认机会", sum(row["is_opportunity"] for row in human)),
]
fig, axis = plt.subplots(figsize=(7.0, 4.0))
bars = axis.bar(
    range(len(stages)),
    [value for _, value in stages],
    color=["#596f9e", "#728bb5", "#4e9b8f", "#c57a36", "#3d7ea6"],
)
axis.bar_label(bars, labels=[f"{value:,}" for _, value in stages], padding=3)
axis.set_xticks(
    range(len(stages)), [label for label, _ in stages], rotation=18, ha="right"
)
axis.set_ylabel("记录数")
axis.set_title("从采集到人工确认机会的记录规模变化")
axis.grid(axis="y", alpha=0.22)
save(fig, "fig02_pipeline_counts")

model_positive = sum(row["is_opportunity"] for row in model)
human_positive = sum(row["is_opportunity"] for row in human)
states = {
    "原模型机会": model_positive,
    "原模型非机会": len(model) - model_positive,
    "人工确认机会": human_positive,
    "人工确认非机会": len(human) - human_positive + len(model) - len(human),
}
fig, axis = plt.subplots(figsize=(7.0, 4.0))
bars = axis.bar(
    list(states),
    list(states.values()),
    color=["#b95b57", "#d9d9d9", "#3d7ea6", "#a9c7d8"],
)
axis.set_ylabel("记录数")
axis.set_title("原模型与人工确认结果的机会判断规模")
axis.bar_label(bars, padding=3, fmt="%d")
axis.set_ylim(0, max(states.values()) * 1.18)
axis.tick_params(axis="x", rotation=15)
save(fig, "fig04_label_shift")

topic_rows = sorted(topics, key=lambda row: (-row["record_count"], row["topic_id"]))
fig, (size_axis, score_axis) = plt.subplots(
    1, 2, figsize=(8.2, 5.2), gridspec_kw={"width_ratios": [1.0, 1.0]}
)
names = [row["topic_id"] for row in topic_rows][::-1]
counts = [row["record_count"] for row in topic_rows][::-1]
scores = [row["value_score"] for row in topic_rows][::-1]
size_bars = size_axis.barh(names, counts, color="#397f78")
size_axis.bar_label(size_bars, padding=2, fmt="%d", fontsize=7)
size_axis.set_xlabel("主题成员数")
size_axis.set_title("主题规模")
size_axis.set_xlim(0, max(counts) * 1.18)
score_bars = score_axis.barh(names, scores, color="#c87932")
score_axis.bar_label(score_bars, padding=2, fmt="%.1f", fontsize=7)
score_axis.set_xlabel("机会价值分")
score_axis.set_title("主题价值分")
score_axis.set_xlim(0, max(scores) * 1.22)
score_axis.tick_params(axis="y", labelleft=False)
fig.suptitle("人工确认机会主题的规模与价值分", y=1.01)
fig.tight_layout()
save(fig, "fig05_topic_size_score")

print(
    json.dumps(
        {
            "human_records": len(human),
            "human_opportunities": human_positive,
            "topics": len(topics),
        },
        ensure_ascii=False,
        indent=2,
    )
)
