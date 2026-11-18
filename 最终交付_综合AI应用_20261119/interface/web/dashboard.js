const state = { data: null, selected: "" };

const get = id => document.getElementById(id);
const node = (tag, text = "", className = "") => {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  return element;
};

const format = value => Number(value).toFixed(2);

async function loadDashboard() {
  const response = await fetch("/api/dashboard");
  if (!response.ok) throw new Error(`看板数据加载失败：HTTP ${response.status}`);
  state.data = await response.json();
  get("run-id").textContent = state.data.display_name;
  renderMetrics();
  renderHotspot();
  renderRanking();
  const first = state.data.topics.find(item => item.is_multi_source_hotspot)
    || state.data.topics[0];
  showTopic(first.topic_id);
}

function renderMetrics() {
  const quality = state.data.quality;
  const hotspotCount = quality.multi_source_hotspot_topic_ids.length;
  const metrics = [
    ["机会记录", quality.candidate_records, "全量人工确认机会"],
    ["展示主题", quality.topic_count, `${quality.noise_records} 个单记录展示项`],
    ["多源热点", hotspotCount, "来源网站数 ≥ 2"],
    ["聚类轮廓系数", format(quality.silhouette_score), "非噪声成员"],
  ];
  const container = get("metrics");
  container.replaceChildren();
  for (const [label, value, note] of metrics) {
    const card = node("article", "", "metric-card");
    card.append(node("span", label, "metric-label"));
    card.append(node("strong", String(value), "metric-value"));
    card.append(node("span", note, "metric-note"));
    container.append(card);
  }
}

function renderHotspot() {
  const hotspot = state.data.topics.find(item => item.is_multi_source_hotspot);
  get("hotspot-count").textContent = `${state.data.quality.multi_source_hotspot_topic_ids.length} 个`;
  const content = get("hotspot-content");
  content.replaceChildren();
  if (!hotspot) {
    content.append(node("p", "当前正式结果没有满足多源定义的主题。", "empty-state"));
    return;
  }
  const title = node("div", "", "hotspot-title");
  title.append(node("span", hotspot.topic_id, "topic-id"));
  title.append(node("h3", hotspot.topic_name));
  content.append(title);
  content.append(node("p", `${hotspot.record_count} 条机会记录 · ${hotspot.source_names.join("、")}`));
  const score = node("div", "", "hotspot-score");
  score.append(node("span", "机会价值分"));
  score.append(node("strong", format(hotspot.value_score)));
  content.append(score);
}

function renderRanking() {
  const container = get("ranking");
  container.replaceChildren();
  const max = Math.max(...state.data.topics.map(item => Number(item.value_score)));
  for (const topic of state.data.topics) {
    const row = node("button", "", "ranking-row");
    row.type = "button";
    if (topic.topic_id === state.selected) row.classList.add("selected");
    const label = node("span", "", "ranking-label");
    label.append(node("b", `${topic.priority}. ${topic.topic_id}`));
    label.append(node("span", topic.topic_name));
    const meta = node("span", "", "ranking-meta");
    meta.append(node("span", `${topic.record_count} 条 · ${topic.source_count} 源`));
    meta.append(node("strong", format(topic.value_score)));
    const track = node("span", "", "ranking-track");
    const bar = node("span", "", "ranking-bar");
    bar.style.width = `${Math.max(3, Number(topic.value_score) / max * 100)}%`;
    if (topic.is_multi_source_hotspot) bar.classList.add("hotspot-bar");
    track.append(bar);
    row.append(label, meta, track);
    row.addEventListener("click", () => showTopic(topic.topic_id));
    container.append(row);
  }
}

function showTopic(topicId) {
  state.selected = topicId;
  const topic = state.data.topics.find(item => item.topic_id === topicId);
  if (!topic) return;
  renderRanking();
  const panel = get("topic-detail");
  panel.replaceChildren();
  const header = node("div", "", "panel-heading");
  const heading = node("div");
  heading.append(node("p", "SELECTED TOPIC", "eyebrow"));
  heading.append(node("h2", `${topic.topic_id} · ${topic.topic_name}`));
  header.append(heading);
  header.append(node("span", topic.is_multi_source_hotspot ? "多源热点" : "单源对照", topic.is_multi_source_hotspot ? "badge badge-blue" : "badge badge-gray"));
  panel.append(header);
  panel.append(node("p", `${topic.record_count} 条机会记录 · 来源覆盖：${topic.source_names.join("、")}`));
  const score = node("div", "", "selected-score");
  score.append(node("span", "机会价值分"));
  score.append(node("strong", format(topic.value_score)));
  panel.append(score);
  const dimensions = node("div", "", "dimension-list");
  const names = {
    multi_source_direction: "多源指向度",
    record_scale: "记录规模",
    interaction_signal: "互动信号",
    recency_signal: "时间新近性",
  };
  for (const [key, value] of Object.entries(topic.dimension_scores || {})) {
    const item = node("div", "", "dimension-item");
    item.append(node("span", names[key] || key));
    item.append(node("b", value === null ? "缺失" : format(value)));
    const track = node("span", "dimension-track");
    const bar = node("span", "dimension-bar");
    bar.style.width = `${value === null ? 0 : value}%`;
    track.append(bar);
    item.append(track);
    dimensions.append(item);
  }
  panel.append(dimensions);
}

loadDashboard().catch(error => {
  get("hotspot-content").append(node("p", error.message, "error"));
});
