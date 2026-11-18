import pytest

from opportunity.topics import (
    TopicLabelBatch,
    is_multi_source_hotspot,
    score_topics,
    short_title,
    top_keywords,
)


def test_topic_title_is_bounded():
    assert len(short_title("一" * 100)) <= 48


def test_topic_keywords_drop_single_letter_fragments():
    keywords = top_keywords(
        [
            "AI assistant helps people search documents and answer questions",
            "AI assistant helps people summarize documents",
        ]
    )
    assert all(len(word.strip()) >= 3 for word in keywords if word.isascii())


def test_topic_label_batch_accepts_model_result_aliases():
    payload = {
        "labels": [
            {
                "topic_id": "C1",
                "name": "设备维护需求",
                "basis_record_ids": ["S00001"],
            }
        ]
    }
    assert TopicLabelBatch.model_validate(payload).topics[0].topic_id == "C1"


def test_multi_source_hotspot_requires_two_sources():
    assert is_multi_source_hotspot({"source_count": 2})
    assert not is_multi_source_hotspot({"source_count": 1})


def test_missing_heat_is_not_scored_as_zero_and_weights_renormalize():
    topics = [
        {
            "topic_id": "C1",
            "record_ids": ["S00001"],
            "source_count": 1,
            "record_count": 1,
        }
    ]
    records = {
        "S00001": {
            "source_id": "forum",
            "metrics": {"comments": None},
        }
    }
    judgements = {"S00001": {"confidence": 0.9}}
    scored, info = score_topics(topics, records, judgements)
    assert scored[0]["dimension_scores"]["interaction_signal"] is None
    assert scored[0]["dimension_scores"]["multi_source_direction"] == 100
    assert scored[0]["dimension_scores"]["record_scale"] == 100
    assert scored[0]["scoring_weights"]["multi_source_direction"] == pytest.approx(
        0.5714285714
    )
    assert scored[0]["scoring_weights"]["record_scale"] == pytest.approx(0.4285714286)
    assert info["weights"]["interaction_signal"] == 0.15


def test_recency_uses_latest_batch_date_and_half_life():
    topics = [
        {
            "topic_id": "C1",
            "record_ids": ["S00001"],
            "source_count": 1,
            "record_count": 1,
        },
        {
            "topic_id": "C2",
            "record_ids": ["S00002"],
            "source_count": 1,
            "record_count": 1,
        },
    ]
    records = {
        "S00001": {
            "source_id": "forum",
            "metrics": {},
            "published_at": "2026-11-07T00:00:00Z",
        },
        "S00002": {
            "source_id": "forum",
            "metrics": {},
            "published_at": "2026-10-08T00:00:00Z",
        },
    }
    scored, _ = score_topics(topics, records, {})
    by_id = {topic["topic_id"]: topic for topic in scored}
    assert by_id["C1"]["dimension_scores"]["recency_signal"] == pytest.approx(100)
    assert by_id["C2"]["dimension_scores"]["recency_signal"] == pytest.approx(50)
    assert by_id["C1"]["scoring_weights"]["recency_signal"] == pytest.approx(
        0.1764705882
    )
