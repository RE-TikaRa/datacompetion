import json

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from opportunity.web import _role, create_app


def test_review_api_reads_and_updates_review_queue(tmp_path):
    root = tmp_path
    run = root / "results" / "B01" / "run" / "review"
    run.mkdir(parents=True)
    (run / "review_summary.json").write_text(
        '{"review_records":1,"review_positive_records":1,"review_negative_records":0}',
        encoding="utf-8",
    )
    row = {
        "queue_id": "R0001",
        "batch_id": "B01",
        "record_id": "S00001",
        "source_name": "GitHub",
        "content_kind": "body",
        "title": "需求",
        "content_path": "results/B01/run/text/B01_S00001.md",
        "model_is_opportunity": 1,
        "model_confidence": 0.9,
        "observable_demand": True,
        "ai_core": True,
        "technically_feasible": True,
        "excluded": False,
        "model_functional_category": "对话问答",
        "model_industry": "电商",
        "model_evidence": ["用户需要"],
        "model_exclusion_reason": "",
        "human_is_opportunity": None,
        "human_functional_category": "",
        "human_industry": "",
        "human_notes": "",
        "review_status": "待人工复核",
    }
    (run / "review_queue.jsonl").write_text(
        __import__("json").dumps(row, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (root / "data" / "reference").mkdir(parents=True)
    (root / "data" / "reference" / "labels.json").write_text(
        '{"functions":["对话问答"],"industries":["电商"]}', encoding="utf-8"
    )
    text_path = root / row["content_path"]
    text_path.parent.mkdir(parents=True)
    text_path.write_text("用户需要", encoding="utf-8")
    client = TestClient(create_app(root))
    index = client.get("/")
    assert index.status_code == 200
    assert "AI 应用机会复核" in index.text
    assert client.get("/assets/review.js").status_code == 200
    assert client.get("/api/runs").json()[0]["run_id"] == "B01/run"
    response = client.get("/api/review/B01/run")
    assert response.status_code == 200
    updated = client.post(
        "/api/review/B01/run/S00001",
        json={
            "human_is_opportunity": True,
            "human_functional_category": "对话问答",
            "human_industry": "电商",
            "human_notes": "复核通过",
        },
    )
    assert updated.status_code == 200
    saved = __import__("json").loads(
        (run / "review_queue.jsonl").read_text(encoding="utf-8")
    )
    assert saved["review_status"] == "已复核"
    assert saved["human_is_opportunity"] is True
    with (run / "review_queue.csv").open(encoding="utf-8-sig", newline="") as stream:
        updated_csv = list(__import__("csv").DictReader(stream))
    assert updated_csv[0]["人工是否构成机会"] == "1"
    assert (
        json.loads((run / "review_summary.json").read_text(encoding="utf-8"))[
            "reviewed_records"
        ]
        == 1
    )


def test_remote_access_requires_configured_accounts():
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/runs",
        "headers": [],
        "client": ("192.0.2.1", 9000),
        "server": ("127.0.0.1", 8000),
        "scheme": "http",
        "query_string": b"",
        "root_path": "",
    }
    with pytest.raises(HTTPException, match="配置"):
        _role(Request(scope), None)


def test_decision_maker_is_read_only_and_sees_only_aggregates(tmp_path, monkeypatch):
    monkeypatch.setenv("REVIEWER_USERNAME", "reviewer")
    monkeypatch.setenv("REVIEWER_PASSWORD", "review-secret")
    monkeypatch.setenv("DECISION_MAKER_USERNAME", "decision")
    monkeypatch.setenv("DECISION_MAKER_PASSWORD", "decision-secret")
    run = tmp_path / "results" / "B01" / "run"
    (run / "review").mkdir(parents=True)
    (run / "review" / "review_summary.json").write_text(
        '{"review_records":1,"reviewed_records":0,"pending_records":1,"review_status":"待人工复核"}',
        encoding="utf-8",
    )
    (run / "topics.json").write_text(
        '{"status":"候选结果","topics":[{"topic_id":"C1","topic_name":"候选"}]}',
        encoding="utf-8",
    )
    (run / "scoring.json").write_text('{"ranking":[]}', encoding="utf-8")
    client = TestClient(create_app(tmp_path))
    summary = client.get("/api/decision/B01/run", auth=("decision", "decision-secret"))
    assert summary.status_code == 200
    assert summary.json()["topics"][0]["topic_id"] == "C1"
    assert "rows" not in summary.json()
    denied = client.get("/api/review/B01/run", auth=("decision", "decision-secret"))
    assert denied.status_code == 403


def test_public_dashboard_reads_formal_topics_without_exposing_records(tmp_path):
    formal = tmp_path / "results" / "B01" / "formal"
    formal.mkdir(parents=True)
    (formal / "topics.json").write_text(
        json.dumps(
            {
                "status": "正式结果",
                "quality": {
                    "candidate_records": 2,
                    "topic_count": 2,
                    "noise_records": 1,
                    "silhouette_score": 0.2,
                    "multi_source_hotspot_topic_ids": ["C1"],
                },
                "topics": [
                    {
                        "topic_id": "C1",
                        "topic_name": "多源主题",
                        "record_count": 2,
                        "source_count": 2,
                        "source_names": ["GitHub", "V2EX"],
                        "dimension_scores": {"multi_source_direction": 100},
                    },
                    {
                        "topic_id": "C2",
                        "topic_name": "单源对照",
                        "record_count": 1,
                        "source_count": 1,
                        "source_names": ["Hacker News"],
                        "dimension_scores": {"multi_source_direction": 50},
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (formal / "scoring.json").write_text(
        '{"scoring":{"weights":{"multi_source_direction":0.4}},"ranking":[{"topic_id":"C1","value_score":80,"priority":1},{"topic_id":"C2","value_score":40,"priority":2}]}',
        encoding="utf-8",
    )
    proposal = tmp_path / "proposal"
    proposal.mkdir()
    (proposal / "C2_AI智能体证据工作台策划案_评审修订版_20261119.md").write_text(
        "# 策划案", encoding="utf-8"
    )
    (proposal / "C2_AI智能体证据工作台策划案_评审修订版_20261119.docx").write_bytes(
        b"docx"
    )
    client = TestClient(create_app(tmp_path))
    page = client.get("/dashboard")
    assert page.status_code == 200
    assert "综合 AI 应用机会决策看板" in page.text
    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert payload["quality"]["multi_source_hotspot_topic_ids"] == ["C1"]
    assert payload["topics"][0]["is_multi_source_hotspot"] is True
    assert "rows" not in payload
    assert client.get("/api/dashboard/proposal/markdown").status_code == 200
    assert client.get("/api/dashboard/proposal/docx").status_code == 200
