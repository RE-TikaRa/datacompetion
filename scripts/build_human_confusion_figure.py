import json
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "results/B01/20261107T173708748922Z"
FIGURES = ROOT / "paper/figures"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


model = {row["record_id"]: row for row in read_jsonl(RUN / "judgements.jsonl")}
human = {
    row["record_id"]: row for row in read_jsonl(RUN / "final/final_judgements.jsonl")
}
counts = {
    "原模型机会": 0,
    "原模型非机会": 0,
    "人工确认机会": 0,
    "人工确认非机会": 0,
}
for record_id, row in model.items():
    counts["原模型机会" if row["is_opportunity"] else "原模型非机会"] += 1
    final = human[record_id]
    counts["人工确认机会" if final["is_opportunity"] else "人工确认非机会"] += 1

plt.rcParams.update(
    {
        "font.family": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)
labels = list(counts)
values = list(counts.values())
colors = ["#b95b57", "#d9d9d9", "#3d7ea6", "#a9c7d8"]
fig, axis = plt.subplots(figsize=(7.0, 4.0))
bars = axis.bar(labels, values, color=colors)
axis.set_ylabel("记录数")
axis.set_title("原模型与人工确认结果的机会判断规模")
axis.bar_label(bars, padding=3, fmt="%d")
axis.set_ylim(0, max(values) * 1.18)
axis.tick_params(axis="x", rotation=15)
fig.tight_layout()
for extension in ("png", "pdf", "svg"):
    fig.savefig(FIGURES / f"fig06_proxy_confusion.{extension}", bbox_inches="tight")
plt.close(fig)
print(json.dumps(counts, ensure_ascii=False))
