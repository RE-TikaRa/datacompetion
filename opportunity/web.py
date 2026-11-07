import csv
import hmac
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
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
HTTP_BASIC = HTTPBasic(auto_error=False)
AUTH_DEPENDENCY = Depends(HTTP_BASIC)


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


def _role(request: Request, credentials: HTTPBasicCredentials | None) -> str:
    reviewer_username = os.getenv("REVIEWER_USERNAME", "")
    reviewer_password = os.getenv("REVIEWER_PASSWORD", "")
    decision_username = os.getenv("DECISION_MAKER_USERNAME", "")
    decision_password = os.getenv("DECISION_MAKER_PASSWORD", "")
    if reviewer_password or decision_password:
        if credentials is not None:
            username = credentials.username.encode("utf-8")
            password = credentials.password.encode("utf-8")
            if (
                reviewer_password
                and hmac.compare_digest(username, reviewer_username.encode("utf-8"))
                and hmac.compare_digest(password, reviewer_password.encode("utf-8"))
            ):
                return "reviewer"
            if (
                decision_password
                and hmac.compare_digest(username, decision_username.encode("utf-8"))
                and hmac.compare_digest(password, decision_password.encode("utf-8"))
            ):
                return "decision-maker"
        raise HTTPException(
            status_code=401,
            detail="账号或密码错误。",
            headers={"WWW-Authenticate": "Basic"},
        )
    if request.client and request.client.host in {"127.0.0.1", "::1", "testclient"}:
        return "reviewer"
    raise HTTPException(status_code=403, detail="请配置本地复核员或决策者账号。")


def create_app(root: Path = ROOT) -> FastAPI:
    load_dotenv(root / ".env", override=False)
    app = FastAPI(title="AI 应用机会评估系统", docs_url="/api/docs")
    app.mount("/assets", StaticFiles(directory=WEB_ROOT), name="assets")

    @app.get("/api/runs")
    def runs(
        request: Request,
        credentials: HTTPBasicCredentials | None = AUTH_DEPENDENCY,
    ) -> list[dict]:
        _role(request, credentials)
        output = []
        for path in sorted((root / "results").glob("*/**/review/review_summary.json")):
            summary = read_json(path)
            run = path.parent.parent.resolve()
            output.append(
                {"run_id": run.relative_to(root / "results").as_posix(), **summary}
            )
        return output

    @app.get("/api/me")
    def current_user(
        request: Request,
        credentials: HTTPBasicCredentials | None = AUTH_DEPENDENCY,
    ) -> dict:
        role = _role(request, credentials)
        return {"role": role}

    @app.get("/api/review/{run_id:path}")
    def review(
        run_id: str,
        request: Request,
        credentials: HTTPBasicCredentials | None = AUTH_DEPENDENCY,
    ) -> dict:
        if _role(request, credentials) != "reviewer":
            raise HTTPException(
                status_code=403, detail="决策者账号不能查看逐条正文和复核记录。"
            )
        run = _run_path(root, run_id)
        rows = _load_review(run)
        summary = read_json(run / "review" / "review_summary.json")
        return {"summary": summary, "labels": _labels(root), "rows": rows}

    @app.get("/api/review/{run_id:path}/{record_id}")
    def review_record(
        run_id: str,
        record_id: str,
        request: Request,
        credentials: HTTPBasicCredentials | None = AUTH_DEPENDENCY,
    ) -> dict:
        if _role(request, credentials) != "reviewer":
            raise HTTPException(
                status_code=403, detail="决策者账号不能查看逐条正文和复核记录。"
            )
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
    def update_review(
        run_id: str,
        record_id: str,
        update: ReviewUpdate,
        request: Request,
        credentials: HTTPBasicCredentials | None = AUTH_DEPENDENCY,
    ) -> dict:
        if _role(request, credentials) != "reviewer":
            raise HTTPException(
                status_code=403, detail="决策者账号不能修改人工复核记录。"
            )
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

    @app.get("/api/decision/{run_id:path}")
    def decision_view(
        run_id: str,
        request: Request,
        credentials: HTTPBasicCredentials | None = AUTH_DEPENDENCY,
    ) -> dict:
        if _role(request, credentials) != "decision-maker":
            raise HTTPException(status_code=403, detail="此视图仅对决策者账号开放。")
        run = _run_path(root, run_id)
        result = {
            "run_id": run_id,
            "status": "暂无主题分析",
            "topics": None,
            "scoring": None,
            "review": None,
        }
        topic_paths = sorted(run.parent.glob("*/topics.json"), reverse=True)
        if (run / "topics.json").exists():
            topic_paths.insert(0, run / "topics.json")
        for topic_path in topic_paths:
            data = read_json(topic_path)
            scoring = read_json(topic_path.with_name("scoring.json"))
            ranked = {row["topic_id"]: row for row in scoring.get("ranking", [])}
            topics = []
            for topic in data.get("topics", []):
                rank = ranked.get(topic["topic_id"], {})
                topics.append(
                    {
                        key: topic[key]
                        for key in [
                            "topic_id",
                            "topic_name",
                            "functional_category",
                            "industry",
                            "record_count",
                            "source_names",
                            "source_count",
                            "dimension_scores",
                        ]
                        if key in topic
                    }
                    | {
                        key: rank[key]
                        for key in ["value_score", "priority"]
                        if key in rank
                    }
                )
            result.update(
                status=data["status"],
                topics=topics,
                scoring={
                    "weights": scoring.get("scoring", {}).get("weights"),
                    "sensitivity": scoring.get("sensitivity"),
                },
            )
            break
        review_summary = run / "review" / "review_summary.json"
        if review_summary.exists():
            summary = read_json(review_summary)
            result["review"] = {
                key: summary.get(key)
                for key in [
                    "review_records",
                    "reviewed_records",
                    "pending_records",
                    "review_status",
                ]
            }
        return result

    @app.get("/", response_class=FileResponse)
    def index() -> FileResponse:
        return FileResponse(WEB_ROOT / "index.html")

    return app


app = create_app()
