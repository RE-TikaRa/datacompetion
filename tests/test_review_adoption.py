from opportunity.review_adoption import adoption_errors


def test_human_adoption_must_match_the_reviewed_labels():
    queue = [
        {
            "record_id": "S00001",
            "human_is_opportunity": True,
            "human_functional_category": "知识检索",
            "human_industry": "教育",
            "human_notes": "",
            "review_status": "已复核",
        }
    ]
    proxy = [
        {
            "record_id": "S00001",
            "is_opportunity": True,
            "functional_category": "知识检索",
            "industry": "教育",
        }
    ]
    adoption = {
        "method": "human_reviewed_labels",
        "labels_changed_by_reviewer": 0,
        "reviewed_records": 1,
        "opportunities": 1,
        "non_opportunities": 0,
        "independent_human_annotation": True,
        "ai_suggestion_text_copied_to_human_notes": False,
    }

    assert adoption_errors(queue, proxy, adoption) == []

    queue[0]["human_is_opportunity"] = False
    assert "人工确认标签与审阅结果不一致：S00001" in adoption_errors(
        queue, proxy, adoption
    )
