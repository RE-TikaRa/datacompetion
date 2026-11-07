const state = {
  runId: "",
  rows: [],
  labels: { functions: [], industries: [] },
  selected: "",
  filter: "all",
};

const get = id => document.getElementById(id);

const node = (tag, text = "", className = "") => {
  const item = document.createElement(tag);
  item.textContent = text;
  item.className = className;
  return item;
};

async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  return data;
}

async function loadRuns() {
  const runs = await api("/api/runs");
  const select = get("run");
  select.replaceChildren();
  for (const run of runs) {
    const option = node("option", run.run_id);
    option.value = run.run_id;
    select.append(option);
  }
  if (runs.length) await loadRun(runs[0].run_id);
}

async function loadRun(runId) {
  const data = await api(`/api/review/${encodeURIComponent(runId)}`);
  state.runId = runId;
  state.rows = data.rows;
  state.labels = data.labels;
  get("summary").textContent =
    `${data.summary.reviewed_records || 0} / ${data.summary.review_records} 已复核`;
  renderRows();
  if (state.selected) await showRecord(state.selected);
}

function matches(row) {
  if (state.filter === "positive") return row.model_is_opportunity === 1;
  if (state.filter === "negative") return row.model_is_opportunity === 0;
  if (state.filter === "pending") return row.review_status !== "已复核";
  return true;
}

function renderRows() {
  const query = get("search").value.trim().toLocaleLowerCase();
  const body = get("rows");
  body.replaceChildren();
  for (const record of state.rows) {
    const text = `${record.record_id} ${record.title} ${record.source_name}`
      .toLocaleLowerCase();
    if (!matches(record) || (query && !text.includes(query))) continue;
    const row = node("tr", "", record.record_id === state.selected ? "selected" : "");
    row.append(node("td", record.record_id));
    const source = node("td");
    source.append(node("span", record.source_name, "source"));
    source.append(document.createElement("br"));
    source.append(node("span", record.title));
    row.append(source);
    row.append(node(
      "td",
      `${record.model_is_opportunity ? "候选" : "非机会"} · ${Number(record.model_confidence).toFixed(2)}`,
      record.model_is_opportunity ? "model-positive" : "model-negative",
    ));
    row.append(node(
      "td",
      record.review_status === "已复核" ? "已复核" : "待复核",
      record.review_status === "已复核" ? "review-done" : "review-pending",
    ));
    row.addEventListener("click", () => showRecord(record.record_id));
    body.append(row);
  }
}

function selectOptions(select, values, selected) {
  select.replaceChildren();
  const empty = node("option", "无");
  empty.value = "";
  select.append(empty);
  for (const value of values) {
    const option = node("option", value);
    option.value = value;
    select.append(option);
  }
  select.value = selected || "";
}

function labeled(label, input, className = "") {
  const wrapper = node("label", label, className);
  wrapper.append(input);
  return wrapper;
}

function conditions(record) {
  const section = node("section", "", "section");
  section.append(node("h3", "模型判断条件"));
  const values = [
    ["存在需求", record.observable_demand],
    ["AI 为核心", record.ai_core],
    ["技术可实现", record.technically_feasible],
    ["命中排除项", record.excluded],
  ];
  const list = node("div", "", "conditions");
  for (const [label, value] of values) {
    list.append(node("span", `${label}：${value ? "是" : "否"}`, `condition ${value ? "yes" : "no"}`));
  }
  section.append(list);
  section.append(node(
    "p",
    `建议分类：${record.model_functional_category || "无"} · ${record.model_industry || "无"}`,
    "muted",
  ));
  if (record.model_exclusion_reason) {
    section.append(node("p", `排除原因：${record.model_exclusion_reason}`, "muted"));
  }
  for (const quote of record.model_evidence) {
    section.append(node("blockquote", quote, "evidence"));
  }
  return section;
}

async function showRecord(recordId) {
  state.selected = recordId;
  renderRows();
  const data = await api(
    `/api/review/${encodeURIComponent(state.runId)}/${encodeURIComponent(recordId)}`,
  );
  const record = data.item;
  const panel = get("detail");
  panel.replaceChildren();

  const heading = node("div", "", "detail-heading");
  heading.append(node("h2", `${record.record_id} · ${record.title}`));
  const link = node("a", record.source_url);
  link.href = record.source_url;
  link.target = "_blank";
  link.rel = "noreferrer";
  heading.append(link);
  heading.append(node(
    "div",
    `${record.source_name} · ${record.content_kind} · 模型置信度 ${Number(record.model_confidence).toFixed(2)}`,
    "meta",
  ));
  panel.append(heading, conditions(record));

  const content = node("section", "", "section");
  content.append(node("h3", "清洗后的原文"));
  content.append(node("pre", data.text, "source-text"));
  panel.append(content);

  const form = node("section", "", "section review-form");
  form.append(node("h3", "人工判断"));
  const fields = node("div", "", "review-fields");
  const verdict = document.createElement("select");
  verdict.id = "human-verdict";
  for (const [value, label] of [["", "未判断"], ["true", "机会"], ["false", "非机会"]]) {
    const option = node("option", label);
    option.value = value;
    verdict.append(option);
  }
  verdict.value = record.human_is_opportunity === null
    ? ""
    : String(record.human_is_opportunity);
  fields.append(labeled("是否构成机会", verdict));

  const functional = document.createElement("select");
  functional.id = "human-function";
  selectOptions(functional, state.labels.functions, record.human_functional_category);
  fields.append(labeled("功能类别", functional));
  const industry = document.createElement("select");
  industry.id = "human-industry";
  selectOptions(industry, state.labels.industries, record.human_industry);
  fields.append(labeled("所属行业", industry));
  form.append(fields);

  const notes = document.createElement("textarea");
  notes.id = "human-notes";
  notes.maxLength = 2000;
  notes.value = record.human_notes;
  form.append(labeled("复核说明", notes, "notes-field"));
  const error = node("div", "", "form-error");
  error.id = "form-error";
  form.append(error);
  const save = node("button", "保存复核结果", "save-button");
  save.addEventListener("click", () => saveReview(record.record_id));
  form.append(save);
  panel.append(form);
}

async function saveReview(recordId) {
  const verdict = get("human-verdict").value;
  const update = {
    human_is_opportunity: verdict === "" ? null : verdict === "true",
    human_functional_category: get("human-function").value,
    human_industry: get("human-industry").value,
    human_notes: get("human-notes").value,
  };
  try {
    await api(
      `/api/review/${encodeURIComponent(state.runId)}/${encodeURIComponent(recordId)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(update),
      },
    );
    await loadRun(state.runId);
  } catch (error) {
    get("form-error").textContent = error.message;
  }
}

get("run").addEventListener("change", () => loadRun(get("run").value));
get("search").addEventListener("input", renderRows);
for (const button of document.querySelectorAll("[data-filter]")) {
  button.addEventListener("click", () => {
    state.filter = button.dataset.filter;
    for (const other of document.querySelectorAll("[data-filter]")) {
      other.classList.toggle("active", other === button);
    }
    renderRows();
  });
}
loadRuns().catch(error => {
  get("detail").textContent = error.message;
});
