import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
TOPIC_RUN = ROOT / "results/B01/20261118T192102321700Z"
FIGURE_DIR = ROOT / "paper/figures"

topics = json.loads((TOPIC_RUN / "topics.json").read_text(encoding="utf-8"))["topics"]
with (TOPIC_RUN / "result4.csv").open(encoding="utf-8-sig", newline="") as stream:
    result4 = list(csv.DictReader(stream))
scores = {row["主题簇编号"]: float(row["机会价值分"]) for row in result4}
topics = sorted(topics, key=lambda row: (-scores[row["topic_id"]], row["topic_id"]))

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 8,
        "axes.titlesize": 10,
        "axes.labelsize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)

names = [f"{row['topic_id']} · {row['record_count']} 条" for row in topics][::-1]
counts = [row["record_count"] for row in topics][::-1]
values = [scores[row["topic_id"]] for row in topics][::-1]
source_counts = [row["source_count"] for row in topics][::-1]
colors = ["#0F4D92" if count >= 2 else "#A7AEB8" for count in source_counts]

fig, axes = plt.subplots(1, 2, figsize=(8.6, 5.3), sharey=True)
count_bars = axes[0].barh(names, counts, color=colors, height=0.68)
score_bars = axes[1].barh(names, values, color=colors, height=0.68)
axes[0].set_title("主题成员规模")
axes[0].set_xlabel("机会记录数")
axes[1].set_title("四维机会价值分")
axes[1].set_xlabel("机会价值分（0–100）")
axes[0].set_yticks(range(len(names)), names)
axes[0].set_xlim(0, max(counts) * 1.28)
axes[1].set_xlim(0, 100)
axes[0].bar_label(count_bars, padding=3, fmt="%d", fontsize=7)
axes[1].bar_label(score_bars, padding=3, fmt="%.2f", fontsize=7)
axes[0].grid(axis="x", alpha=0.18)
axes[1].grid(axis="x", alpha=0.18)
axes[1].tick_params(axis="y", labelleft=False)
fig.suptitle("人工确认机会主题的规模、来源覆盖与正式价值分", y=0.995, fontsize=11)
fig.legend(
    handles=[
        Patch(facecolor="#0F4D92", label="多源热点（来源网站数 ≥ 2）"),
        Patch(facecolor="#A7AEB8", label="单源或单条对照"),
    ],
    loc="lower center",
    ncol=2,
    frameon=False,
    bbox_to_anchor=(0.5, -0.015),
    fontsize=8,
)
fig.tight_layout(rect=(0, 0.04, 1, 0.97))
for extension in ("png", "pdf", "svg"):
    fig.savefig(FIGURE_DIR / f"fig05_topic_size_score.{extension}", bbox_inches="tight")
plt.close(fig)
print("fig05_topic_size_score regenerated from", TOPIC_RUN)
