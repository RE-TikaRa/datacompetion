from fastapi.testclient import TestClient

from opportunity.web import create_app


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
