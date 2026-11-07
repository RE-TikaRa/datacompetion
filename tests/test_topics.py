import pytest

from opportunity.topics import (
    TopicLabelBatch,
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
        0.5625
    )
    assert scored[0]["scoring_weights"]["record_scale"] == pytest.approx(0.4375)
    assert info["weights"]["interaction_signal"] == 0.2
