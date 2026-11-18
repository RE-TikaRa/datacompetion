from collections.abc import Mapping


def adoption_errors(
    queue: list[dict], proxy: list[dict], adoption: Mapping[str, object]
) -> list[str]:
    errors = []
    queue_by_id = {row["record_id"]: row for row in queue}
    proxy_by_id = {row["record_id"]: row for row in proxy}
    if len(queue_by_id) != len(queue):
        errors.append("复核队列包含重复记录编号。")
    if len(proxy_by_id) != len(proxy):
        errors.append("代理复核结果包含重复记录编号。")
    if set(queue_by_id) != set(proxy_by_id):
        errors.append("人工确认记录与代理复核记录范围不一致。")
    if adoption.get("method") != "human_reviewed_labels":
        errors.append("人工确认来源方法记录不合法。")
    if adoption.get("labels_changed_by_reviewer") != 0:
        errors.append("人工标签变更数与用户确认不一致。")
    if adoption.get("independent_human_annotation") is not True:
        errors.append("人工确认状态没有标记为人工标签。")
    if adoption.get("ai_suggestion_text_copied_to_human_notes") is not False:
        errors.append("AI 建议文本被写入人工备注。")
    if adoption.get("reviewed_records") != len(proxy):
        errors.append("人工确认清单数量不一致。")
    if adoption.get("opportunities") != sum(
        bool(row["is_opportunity"]) for row in proxy
    ):
        errors.append("人工确认机会数量与标签来源不一致。")
    if adoption.get("non_opportunities") != sum(
        not row["is_opportunity"] for row in proxy
    ):
        errors.append("人工确认非机会数量与标签来源不一致。")
    for record_id, source in proxy_by_id.items():
        row = queue_by_id.get(record_id)
        if row is None:
            continue
        if row["human_is_opportunity"] is not source["is_opportunity"]:
            errors.append(f"人工确认标签与审阅结果不一致：{record_id}")
        if row["human_functional_category"] != source["functional_category"]:
            errors.append(f"人工确认功能类别与审阅结果不一致：{record_id}")
        if row["human_industry"] != source["industry"]:
            errors.append(f"人工确认行业与审阅结果不一致：{record_id}")
        if row["review_status"] != "已复核":
            errors.append(f"人工确认状态不一致：{record_id}")
        if row["human_notes"]:
            errors.append(f"人工备注包含额外建议文本：{record_id}")
    return errors
