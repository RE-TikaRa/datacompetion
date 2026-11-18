import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "results/B01/20261107T173708748922Z"
FULL = ROOT / "results/B01/20261118T160530815667Z"
FIGURES = ROOT / "paper/figures"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


model = {row["record_id"]: row for row in read_jsonl(RUN / "judgements.jsonl")}
human = {
    row["record_id"]: row for row in read_jsonl(FULL / "final/final_judgements.jsonl")
}
matrix = np.zeros((2, 2), dtype=int)
for record_id, row in model.items():
    matrix[int(row["is_opportunity"]), int(human[record_id]["is_opportunity"])] += 1

plt.rcParams.update(
    {
        "font.family": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)
fig, axis = plt.subplots(figsize=(5.2, 4.4))
image = axis.imshow(matrix, cmap="Blues")
for i in range(2):
    for j in range(2):
        axis.text(
            j,
            i,
            f"{matrix[i, j]:,}",
            ha="center",
            va="center",
            color="white" if matrix[i, j] > matrix.max() * 0.55 else "#1f2937",
            fontsize=13,
            fontweight="bold",
        )
axis.set_xticks([0, 1], ["最终非机会", "最终机会"])
axis.set_yticks([0, 1], ["原模型非机会", "原模型机会"])
axis.set_xlabel("全量人工确认标签")
axis.set_ylabel("原模型标签")
axis.set_title("原模型与全量人工确认标签的四格交叉")
fig.colorbar(image, ax=axis, shrink=0.82, label="记录数")
fig.tight_layout()
for extension in ("png", "pdf", "svg"):
    fig.savefig(FIGURES / f"fig06_human_confusion.{extension}", bbox_inches="tight")
plt.close(fig)
print(
    json.dumps(
        {
            "tn": int(matrix[0, 0]),
            "fp": int(matrix[0, 1]),
            "fn": int(matrix[1, 0]),
            "tp": int(matrix[1, 1]),
        },
        ensure_ascii=False,
    )
)
