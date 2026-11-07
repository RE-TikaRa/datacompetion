import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from opportunity.files import ROOT, read_json, read_jsonl

WEB_ROOT = ROOT / "web"
REVIEW_COLUMNS = [
    "采集批次号",
    "记录编号",
    "来源网站名称",
    "内容类型",
    "标题",
    "正文路径",
    "模型是否构成机会",
    "模型置信度",
    "需求信号",
    "AI核心性",
    "技术可实现性",
    "排除项",
    "模型功能类别",
    "模型所属行业",
    "模型证据",
    "模型排除理由",
    "人工是否构成机会",
    "人工功能类别",
    "人工所属行业",
    "人工备注",
]


class ReviewUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    human_is_opportunity: bool | None
    human_functional_category: str = ""
    human_industry: str = ""
    human_notes: str = Field(default="", max_length=2000)


def _run_path(root: Path, run_id: str) -> Path:
    run = (root / "results" / run_id).resolve()
    if not run.is_relative_to((root / "results").resolve()) or not run.is_dir():
        raise HTTPException(status_code=404, detail="运行目录不存在。")
    return run


def _review_path(run: Path) -> Path:
    path = run / "review" / "review_queue.jsonl"
    if not path.exists():
        raise HTTPException(status_code=404, detail="该运行没有人工复核队列。")
    return path


def _load_review(run: Path) -> list[dict]:
    return read_jsonl(_review_path(run))


def _csv_row(row: dict) -> dict:
    human_value = row["human_is_opportunity"]
    return {
        "采集批次号": row["batch_id"],
        "记录编号": row["record_id"],
        "来源网站名称": row["source_name"],
        "内容类型": row["content_kind"],
        "标题": row["title"],
        "正文路径": row["content_path"],
        "模型是否构成机会": row["model_is_opportunity"],
        "模型置信度": row["model_confidence"],
        "需求信号": row["observable_demand"],
        "AI核心性": row["ai_core"],
        "技术可实现性": row["technically_feasible"],
        "排除项": row["excluded"],
        "模型功能类别": row["model_functional_category"],
        "模型所属行业": row["model_industry"],
        "模型证据": "；".join(row["model_evidence"]),
        "模型排除理由": row["model_exclusion_reason"],
        "人工是否构成机会": "" if human_value is None else int(human_value),
        "人工功能类别": row["human_functional_category"],
        "人工所属行业": row["human_industry"],
        "人工备注": row["human_notes"],
    }


def _save_review(run: Path, rows: list[dict]) -> None:
    path = _review_path(run)
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    csv_path = path.with_name("review_queue.csv")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerows(_csv_row(row) for row in rows)
    summary_path = path.with_name("review_summary.json")
    summary = read_json(summary_path)
    reviewed = sum(row["review_status"] == "已复核" for row in rows)
    summary.update(
        reviewed_records=reviewed,
        pending_records=len(rows) - reviewed,
        reviewed_at=datetime.now(UTC).isoformat(),
    )
    with summary_path.open("w", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def _labels(root: Path) -> dict:
    return read_json(root / "data/reference/labels.json")


def create_app(root: Path = ROOT) -> FastAPI:
    app = FastAPI(title="AI 应用机会评估系统", docs_url="/api/docs")
    app.mount("/assets", StaticFiles(directory=WEB_ROOT), name="assets")

    @app.get("/api/runs")
    def runs() -> list[dict]:
        output = []
        for path in sorted((root / "results").glob("*/**/review/review_summary.json")):
            summary = read_json(path)
            output.append({"run_id": path.parent.parent.name, **summary})
        return output

    @app.get("/api/review/{run_id:path}")
    def review(run_id: str) -> dict:
        run = _run_path(root, run_id)
        rows = _load_review(run)
        summary = read_json(run / "review" / "review_summary.json")
        return {"summary": summary, "labels": _labels(root), "rows": rows}

    @app.get("/api/review/{run_id:path}/{record_id}")
    def review_record(run_id: str, record_id: str) -> dict:
        run = _run_path(root, run_id)
        rows = _load_review(run)
        item = next((row for row in rows if row["record_id"] == record_id), None)
        if item is None:
            raise HTTPException(status_code=404, detail="记录不存在。")
        text_path = (root / item["content_path"]).resolve()
        if not text_path.is_relative_to(root) or not text_path.exists():
            raise HTTPException(status_code=404, detail="正文快照不存在。")
        return {"item": item, "text": text_path.read_text(encoding="utf-8")}

    @app.post("/api/review/{run_id:path}/{record_id}")
    def update_review(run_id: str, record_id: str, update: ReviewUpdate) -> dict:
        run = _run_path(root, run_id)
        rows = _load_review(run)
        item = next((row for row in rows if row["record_id"] == record_id), None)
        if item is None:
            raise HTTPException(status_code=404, detail="记录不存在。")
        labels = _labels(root)
        if update.human_is_opportunity is True:
            if update.human_functional_category not in labels["functions"]:
                raise HTTPException(status_code=422, detail="功能类别不在官方标签中。")
            if update.human_industry not in labels["industries"]:
                raise HTTPException(status_code=422, detail="所属行业不在官方标签中。")
        elif update.human_functional_category or update.human_industry:
            raise HTTPException(status_code=422, detail="非机会记录不能填写机会分类。")
        item.update(
            {
                "human_is_opportunity": update.human_is_opportunity,
                "human_functional_category": update.human_functional_category,
                "human_industry": update.human_industry,
                "human_notes": update.human_notes,
                "review_status": "已复核"
                if update.human_is_opportunity is not None
                else "待人工复核",
            }
        )
        _save_review(run, rows)
        return {"record_id": record_id, "review_status": item["review_status"]}

    @app.get("/", response_class=FileResponse)
    def index() -> FileResponse:
        return FileResponse(WEB_ROOT / "index.html")

    return app


app = create_app()
