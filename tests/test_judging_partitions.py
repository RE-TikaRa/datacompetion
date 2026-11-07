from typing import cast

import pytest

from opportunity.judging import ModelClient, judge_partition


def test_failed_group_splits_and_saves_reusable_checkpoints(tmp_path, monkeypatch):
    calls = []

    def judge(client, records, labels):
        calls.append([row["record_id"] for row in records])
        if len(records) > 1:
            raise ValueError("invalid group output")
        record = records[0]
        return {
            "record_ids": [record["record_id"]],
            "items": [{"record_id": record["record_id"]}],
            "usage": {
                "response_id": record["record_id"],
                "model": "test",
                "elapsed_seconds": 1,
                "input_tokens": 2,
                "output_tokens": 1,
                "cached_input_tokens": 0,
                "cost": None,
                "cost_basis": "unknown",
            },
            "evidence_repairs": [],
        }

    monkeypatch.setattr("opportunity.judging.judge_one_batch", judge)
    records = [{"record_id": f"S{i:05d}"} for i in range(4)]
    result = judge_partition(cast(ModelClient, None), records, {}, tmp_path, "0001")
    assert result["record_ids"] == [record["record_id"] for record in records]
    assert result["usage"]["input_tokens"] == 8
    assert len(list(tmp_path.glob("*.json"))) == 7

    resumed = judge_partition(cast(ModelClient, None), records, {}, tmp_path, "0001")
    assert resumed == result
    assert len(calls) == 7


def test_single_record_failure_remains_visible(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "opportunity.judging.judge_one_batch",
        lambda *args: (_ for _ in ()).throw(ValueError("invalid record")),
    )
    with pytest.raises(ValueError, match="invalid record"):
        judge_partition(
            cast(ModelClient, None), [{"record_id": "S00001"}], {}, tmp_path, "0001"
        )
