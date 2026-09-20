const statusLabels = {
  found: "Найдено",
  matched: "Подходит",
  letter_ready: "Письмо готово",
  applied: "Отклик отправлен",
  interview: "Интервью",
  offer: "Оффер",
  rejected: "Отказ",
  archived: "Архив",
};
const workFormatLabels = {
  "": "Любой формат",
  HYBRID: "Гибрид",
  ON_SITE: "На месте у работодателя",
  REMOTE: "Удаленная работа",
};

let vacancies = [];
let selectedId = null;
let hhSearchResults = [];
let searchSuggestions = [];
let profileCatalog = { roles: [], skills: [], work_formats: [], strengths: [], constraints: [] };
let hhAreas = [];
let browserPlan = [];
let currentUser = null;
let appBooted = false;
const tagPickers = new Map();
let areaSuggestTimer = null;
let profilePrimaryArea = "Москва";
let vacancyPollTimer = null;
let searchPollTimer = null;
let vacancyLoadSequence = 0;
let vacancyLoadsInFlight = 0;
let vacancyFilterTimer = null;
const selectedLettersForApproval = new Set();

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function debounce(callback, delay) {
  let timer;
  return (...args) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => callback(...args), delay);
  };
}

function fieldValue(selector) {
  const node = $(selector);
  return node ? node.value : "";
}

function fieldChecked(selector) {
  const node = $(selector);
  return node ? node.checked : false;
}

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("show");
  setTimeout(() => node.classList.remove("show"), 2400);
}

function showAuthError(message) {
  const node = $("#auth-error");
  node.textContent = message;
  node.hidden = !message;
}

function showAuthView(view) {
  document.body.classList.add("auth-pending");
  $("#auth-screen").hidden = false;
  $("#auth-login").hidden = view !== "login";
  $("#auth-setup").hidden = view !== "setup";
  showAuthError("");
}

async function enterApp(user) {
  currentUser = user;
  $("#current-user-name").textContent = user.display_name;
  $("#current-user-role").textContent = "Локальный режим";
  $("#auth-screen").hidden = true;
  document.body.classList.remove("auth-pending");
  $$(".owner-only").forEach((node) => { node.hidden = false; });
  if (!appBooted) {
    appBooted = true;
    await bootApp();
  }
}

async function submitAuthForm(form, path) {
  const payload = Object.fromEntries(new FormData(form).entries());
  try {
    const result = await api(path, { method: "POST", body: JSON.stringify(payload) });
    await enterApp(result.user);
  } catch (error) {
    showAuthError(error.message);
  }
}

async function startAuth() {
  $("#login-form").addEventListener("submit", (event) => {
    event.preventDefault();
    submitAuthForm(event.currentTarget, "/api/auth/login");
  });
  $("#setup-form").addEventListener("submit", (event) => {
    event.preventDefault();
    submitAuthForm(event.currentTarget, "/api/auth/setup");
  });
  $("#logout").addEventListener("click", async () => {
    await api("/api/auth/logout", { method: "POST", body: "{}" });
    window.location.reload();
  });

  const state = await api("/api/auth/state");
  if (state.setup_required) return showAuthView("setup");
  if (!state.authenticated) return showAuthView("login");
  await enterApp(state.user);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Ошибка запроса");
  return data;
}

function setView(id) {
  $$(".nav").forEach((button) => button.classList.toggle("active", button.dataset.view === id));
  $$(".view").forEach((view) => view.classList.toggle("active", view.id === id));
  if (id === "dashboard") loadDashboard();
  if (id === "search") loadSearchState();
  if (id === "vacancies") loadVacancies();
  if (id === "ai-settings" && currentUser?.role === "owner") loadAiSettings();
}

function formatNumber(value) {
  return new Intl.NumberFormat("ru-RU").format(Number(value || 0));
}

function syncAiProvider(resetModel = false) {
  const form = $("#ai-settings-form");
  const provider = form.elements.provider.value;
  const isGemini = provider === "gemini";
  const isOllama = provider === "ollama";
  if (resetModel) {
    form.elements.model.value = isOllama ? "qwen3:8b" : isGemini ? "gemini-3.1-flash-lite" : "gpt-4o-mini";
  }
  $("#ai-key-field").hidden = isOllama;
  $("#clear-ai-key").hidden = isOllama;
  $("#ai-key-label").textContent = isGemini ? "Gemini API-ключ" : "OpenAI API-ключ";
  $("#ai-provider-hint").textContent = isOllama
    ? "Ollama работает на этом компьютере: резюме и вакансия не отправляются внешнему AI-провайдеру."
    : isGemini
      ? "На бесплатном тарифе Google может использовать отправленные данные для улучшения продуктов. Career Bot удаляет из текста телефон, почту и ссылки перед отправкой."
      : "Career Bot отправляет выбранную вакансию и очищенный от контактных данных карьерный профиль только для генерации письма.";
}

async function loadAiSettings() {
  const settings = await api("/api/ai/settings");
  const form = $("#ai-settings-form");
  form.elements.provider.value = settings.provider;
  form.elements.model.value = settings.model;
  syncAiProvider();
  const ollama = settings.providers?.ollama;
  const statusText = settings.provider === "ollama" && !settings.configured
    ? (ollama?.running ? "Загрузите модель" : "Ollama не запущена")
    : (settings.configured ? "Подключено" : "Не подключено");
  $("#ai-connection-status").textContent = statusText;
  $("#ai-connection-status").classList.toggle("connected", settings.configured);
  $("#ai-generation-count").textContent = formatNumber(settings.usage.generations);
  $("#ai-input-tokens").textContent = formatNumber(settings.usage.input_tokens);
  $("#ai-output-tokens").textContent = formatNumber(settings.usage.output_tokens);
  $("#ai-total-tokens").textContent = formatNumber(settings.usage.total_tokens);
}

async function saveAiSettings(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = Object.fromEntries(new FormData(form).entries());
  await api("/api/ai/settings", { method: "POST", body: JSON.stringify(payload) });
  form.elements.api_key.value = "";
  await loadAiSettings();
  toast("Настройки ИИ сохранены");
}

async function clearAiKey() {
  const form = $("#ai-settings-form");
  await api("/api/ai/settings", {
    method: "POST",
    body: JSON.stringify({
      provider: form.elements.provider.value,
      model: form.elements.model.value,
      clear_key: true,
    }),
  });
  await loadAiSettings();
  toast("API-ключ удален");
}

async function loadProfile() {
  const profile = await api("/api/profile");
  const form = $("#profile-form");
  Object.entries(profile).forEach(([key, value]) => {
    const field = form.elements[key];
    if (field) field.value = value || "";
  });
  syncAllTagPickers();
  syncProfileAreaFromLocations();
  $("#resume-file-status").textContent = profile.resume_file_uploaded
    ? `Загружен: ${profile.resume_file_name}`
    : "PDF не загружен";
  $("#hh-import-status").textContent = profile.hh_imported_at
    ? `${profile.hh_import_summary || "Профиль импортирован с hh.ru"} · ${new Date(profile.hh_imported_at).toLocaleString("ru-RU")}`
    : "Профиль hh.ru еще не импортирован";
}

async function uploadResumePdf(file) {
  if (!file) return;
  if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
    throw new Error("Выберите PDF-файл.");
  }
  if (file.size > 10 * 1024 * 1024) throw new Error("PDF должен быть не больше 10 МБ.");
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
  const result = await api("/api/profile/resume", {
    method: "POST",
    body: JSON.stringify({ name: file.name, data: btoa(binary) }),
  });
  $("#resume-file-status").textContent = `Загружен: ${result.name}`;
  toast("PDF-резюме сохранено локально");
}

function flattenAreas(items) {
  const result = [];
  (items || []).forEach((item) => {
    if (item?.id && item?.name) result.push({ id: String(item.id), name: String(item.name) });
    if (Array.isArray(item?.areas)) result.push(...flattenAreas(item.areas));
  });
  return result;
}

async function loadCatalog() {
  profileCatalog = await api("/api/catalog/profile-options");
}

async function loadAreas() {
  try {
    const response = await fetch("https://api.hh.ru/areas", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("hh areas unavailable");
    hhAreas = flattenAreas(await response.json());
  } catch (_error) {
    hhAreas = await api("/api/hh/areas");
  }
  const unique = new Map(hhAreas.map((area) => [area.id, area]));
  hhAreas = Array.from(unique.values()).sort((a, b) => a.name.localeCompare(b.name, "ru"));
  $("#hh-area-list").innerHTML = hhAreas
    .map((area) => `<option value="${escapeAttr(area.name)}"></option>`)
    .join("");
  syncPrimarySearchArea();
  $("#area-catalog-status").textContent = `Доступно регионов и городов: ${hhAreas.length}`;
}

function mergeAreas(items) {
  const unique = new Map(hhAreas.map((area) => [area.id, area]));
  items.forEach((area) => unique.set(String(area.id), { id: String(area.id), name: String(area.name) }));
  hhAreas = Array.from(unique.values()).sort((a, b) => a.name.localeCompare(b.name, "ru"));
  $("#hh-area-list").innerHTML = hhAreas.map((area) => `<option value="${escapeAttr(area.name)}"></option>`).join("");
  $("#area-catalog-status").textContent = `Доступно регионов и городов: ${hhAreas.length}`;
}

function requestAreaSuggestions(query, afterLoad) {
  window.clearTimeout(areaSuggestTimer);
  if (query.trim().length < 2) return;
  areaSuggestTimer = window.setTimeout(async () => {
    try {
      const items = await api(`/api/hh/area-suggest?q=${encodeURIComponent(query.trim())}`);
      mergeAreas(items);
      afterLoad?.();
    } catch (_error) {
      // The locally cached area list remains available while hh.ru is offline.
    }
  }, 180);
}

function splitTags(value) {
  return String(value || "").split(/[,;\n]+/).map((item) => item.trim()).filter(Boolean);
}

function pickerOptions(source) {
  if (source === "roles") return profileCatalog.roles.map((role) => role.name);
  if (source === "areas") return hhAreas.map((area) => area.name);
  if (source === "skills") {
    const roles = tagPickers.get("target_roles")?.values || [];
    const related = profileCatalog.roles
      .filter((role) => roles.some((selected) => selected.toLowerCase() === role.name.toLowerCase()))
      .flatMap((role) => role.skills);
    return Array.from(new Set(related.length ? related : profileCatalog.skills));
  }
  return profileCatalog[source] || [];
}

function renderPicker(state) {
  state.hidden.value = state.values.join(", ");
  state.chips.innerHTML = state.values
    .filter((value) => state.field !== "locations" || value.toLowerCase() !== profilePrimaryArea.toLowerCase())
    .map((value) => {
      return `<span class="tag-chip">${escapeHtml(value)}<button type="button" data-value="${escapeAttr(value)}" title="Удалить">×</button></span>`;
    })
    .join("");
  state.chips.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => {
    state.values = state.values.filter((value) => value !== button.dataset.value);
    renderPicker(state);
    if (state.field === "target_roles") renderPickerSuggestions(tagPickers.get("skills"));
  }));
}

function renderPickerSuggestions(state) {
  if (!state) return;
  const query = state.search.value.trim().toLowerCase();
  const options = pickerOptions(state.source)
    .filter((item) => !state.values.some((value) => value.toLowerCase() === item.toLowerCase()))
    .filter((item) => !query || item.toLowerCase().includes(query))
    .slice(0, 10);
  state.suggestions.innerHTML = options
    .map((item) => `<button type="button" data-value="${escapeAttr(item)}"><span>+</span>${escapeHtml(item)}</button>`)
    .join("");
  state.suggestions.classList.toggle("open", Boolean(options.length));
  state.suggestions.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => addPickerValue(state, button.dataset.value)));
}

function addPickerValue(state, rawValue) {
  const value = String(rawValue || "").trim();
  if (!value || state.values.some((item) => item.toLowerCase() === value.toLowerCase())) return;
  state.values.push(value);
  state.search.value = "";
  state.suggestions.classList.remove("open");
  renderPicker(state);
  if (state.field === "target_roles") renderPickerSuggestions(tagPickers.get("skills"));
}

function addPickerInput(state, rawValue) {
  const values = state.field === "skills" ? splitTags(rawValue) : [String(rawValue || "").trim()];
  const existing = new Set(state.values.map((item) => item.toLowerCase()));
  let changed = false;

  values.forEach((value) => {
    const normalized = value.toLowerCase();
    if (!value || existing.has(normalized)) return;
    state.values.push(value);
    existing.add(normalized);
    changed = true;
  });

  state.search.value = "";
  state.suggestions.classList.remove("open");
  if (changed) renderPicker(state);
}

function initTagPickers() {
  $$(".tag-picker").forEach((node) => {
    const state = {
      node,
      field: node.dataset.field,
      source: node.dataset.source,
      values: [],
      hidden: node.querySelector('input[type="hidden"]'),
      search: node.querySelector(".tag-search"),
      chips: node.querySelector(".tag-chips"),
      suggestions: node.querySelector(".tag-suggestions"),
    };
    tagPickers.set(state.field, state);
    state.search.addEventListener("focus", () => renderPickerSuggestions(state));
    state.search.addEventListener("input", () => {
      if (state.field === "skills" && /[,;\n]/.test(state.search.value)) {
        addPickerInput(state, state.search.value);
        return;
      }
      renderPickerSuggestions(state);
      if (state.source === "areas") requestAreaSuggestions(state.search.value, () => renderPickerSuggestions(state));
    });
    state.search.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        const first = state.suggestions.querySelector("button");
        addPickerInput(state, first?.dataset.value || state.search.value);
      }
    });
    node.querySelector(".tag-add").addEventListener("click", () => {
      const first = state.suggestions.querySelector("button");
      addPickerInput(state, first?.dataset.value || state.search.value);
    });
  });
  document.addEventListener("click", (event) => {
    tagPickers.forEach((state) => {
      if (!state.node.contains(event.target)) state.suggestions.classList.remove("open");
    });
  });
}

function syncAllTagPickers() {
  tagPickers.forEach((state) => {
    state.values = splitTags(state.hidden.value);
    renderPicker(state);
  });
}

function syncProfileAreaFromLocations() {
  const state = tagPickers.get("locations");
  const select = $("#profile-area-primary");
  if (!state || !select) return;

  const primaryOptions = Array.from(select.options).map((option) => option.value);
  const selected = state.values.find((value) =>
    primaryOptions.some((option) => option.toLowerCase() === value.toLowerCase()),
  );
  profilePrimaryArea = selected || state.values[0] || select.value || "Москва";

  if (!primaryOptions.some((option) => option.toLowerCase() === profilePrimaryArea.toLowerCase())) {
    select.add(new Option(`${profilePrimaryArea} · уточнено`, profilePrimaryArea, true, true), 0);
  }
  select.value = profilePrimaryArea;
  if (!state.values.some((value) => value.toLowerCase() === profilePrimaryArea.toLowerCase())) {
    state.values.unshift(profilePrimaryArea);
  }
  renderPicker(state);
}

function updateProfilePrimaryArea() {
  const state = tagPickers.get("locations");
  const nextArea = fieldValue("#profile-area-primary").trim();
  if (!state || !nextArea) return;
  state.values = [
    nextArea,
    ...state.values.filter(
      (value) => value.toLowerCase() !== profilePrimaryArea.toLowerCase() && value.toLowerCase() !== nextArea.toLowerCase(),
    ),
  ];
  profilePrimaryArea = nextArea;
  renderPicker(state);
}

function toggleProfileAreaDetail() {
  const detail = $("#profile-area-detail");
  const willOpen = detail.hidden;
  detail.hidden = !willOpen;
  $("#toggle-profile-area-detail").textContent = willOpen ? "Скрыть уточнение" : "Уточнить";
  if (willOpen) tagPickers.get("locations")?.search.focus();
}

function renderSearchSuggestions() {
  const placeholder = searchSuggestions.length ? "Выберите направление" : "Заполните целевые роли в профиле";
  const options = searchSuggestions
    .map((item, index) => `<option value="${index}">${escapeHtml(item.label)}</option>`)
    .join("");
  $("#hh-suggestion").innerHTML = `<option value="">${placeholder}</option>${options}`;
  $("#hh-text").innerHTML = `<option value="">${placeholder}</option>${searchSuggestions
    .map((item) => `<option value="${escapeAttr(item.query)}">${escapeHtml(item.query)}</option>`)
    .join("")}`;
}

async function generateSearchSuggestions() {
  searchSuggestions = await api("/api/search/suggestions");
  renderSearchSuggestions();
  if (!searchSuggestions.length) {
    $("#suggestion-reason").textContent = "Добавьте целевые роли или навыки во вкладке «Профиль».";
    toast("Сначала заполните карьерный профиль");
    return;
  }
  $("#hh-suggestion").value = "0";
  applySearchSuggestion(0);
  toast(`Собрано направлений: ${searchSuggestions.length}`);
}

function applySearchSuggestion(index) {
  const item = searchSuggestions[index];
  if (!item) return;
  $("#hh-text").value = item.query;
  $("#suggestion-reason").textContent = item.reason;
}

async function saveProfile() {
  const form = $("#profile-form");
  const payload = Object.fromEntries(new FormData(form).entries());
  await api("/api/profile", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  toast("Профиль сохранен, вакансии пересчитаны");
  await loadDashboard();
}

async function loadDashboard() {
  const [funnel, scenarios, runs] = await Promise.all([
    api("/api/funnel"), api("/api/search/scenarios"), api("/api/search/runs"),
  ]);
  $("#funnel").innerHTML = funnel
    .map(
      (item) => `
        <div class="funnel-card">
          <strong>${item.count}</strong>
          <span>${item.label}</span>
        </div>
      `,
    )
    .join("");
  const active = runs.filter((run) => ["queued", "running", "stopping"].includes(run.status));
  $("#search-summary").textContent = active.length
    ? `Прямой API в работе: ${active.length}. Обработано: ${active.reduce((sum, run) => sum + run.processed, 0)}.`
    : `Готово сценариев: ${scenarios.filter((item) => item.enabled).length}. Сбор откроется в обычном браузере.`;
  loadLetterBatchProgress().catch(() => {});
}

const runStatusLabels = {
  queued: "В очереди", running: "Идет поиск", stopping: "Останавливается",
  stopped: "Остановлен", done: "Готово", error: "Ошибка",
};

async function loadSearchState() {
  const [scenarios, runs, plan] = await Promise.all([
    api("/api/search/scenarios"), api("/api/search/runs"), api("/api/search/browser-plan"),
  ]);
  browserPlan = plan.items || [];
  $("#scenario-list").innerHTML = scenarios.length
    ? `<div class="scenario-list-head"><h3 class="subsection-title">Сохраненные сценарии · ${scenarios.length}</h3><button id="delete-all-scenarios" class="danger" type="button">Удалить все</button></div>${scenarios.map((item) => `
      <div class="scenario-row">
        <input class="scenario-enabled" type="checkbox" aria-label="Включить сценарий" data-id="${item.id}" ${item.enabled ? "checked" : ""} />
        <span><strong>${escapeHtml(item.name)}${item.source === "ai-intent" ? '<em class="scenario-origin">ИИ</em>' : ""}</strong><small>${escapeHtml(item.area_name)} · свежесть ${item.period} дн. · ${escapeHtml(workFormatLabels[item.work_format || ""] || "Любой формат")}${item.salary ? ` · от ${formatNumber(item.salary)} ₽` : ""}</small>${item.reason ? `<small class="scenario-reason">${escapeHtml(item.reason)}</small>` : ""}</span>
        <select class="scenario-work-format" data-id="${item.id}" aria-label="Формат работы для сценария ${escapeAttr(item.name)}">
          ${Object.entries(workFormatLabels).map(([value, label]) => `<option value="${value}" ${value === (item.work_format || "") ? "selected" : ""}>${label}</option>`).join("")}
        </select>
        <button class="scenario-open secondary" type="button" data-id="${item.id}" ${item.enabled ? "" : "disabled"}>Открыть</button>
        <button class="scenario-delete danger" type="button" data-id="${item.id}" data-name="${escapeAttr(item.name)}">Удалить</button>
      </div>`).join("")}`
    : '<div class="note">Сценариев пока нет. Возьмите роли из профиля или опишите желаемую работу.</div>';
  $$(".scenario-enabled").forEach((node) => node.addEventListener("change", async () => {
    await api(`/api/search/scenarios/${node.dataset.id}`, { method: "POST", body: JSON.stringify({ enabled: node.checked }) });
    await Promise.all([loadSearchState(), loadDashboard()]);
  }));
  $$(".scenario-work-format").forEach((node) => node.addEventListener("change", async () => {
    node.disabled = true;
    try {
      await api(`/api/search/scenarios/${node.dataset.id}`, {
        method: "POST",
        body: JSON.stringify({ work_format: node.value }),
      });
      toast(`Формат сохранен: ${workFormatLabels[node.value]}`);
      await loadSearchState();
    } catch (error) {
      node.disabled = false;
      toast(error.message);
    }
  }));
  $$(".scenario-open").forEach((node) => node.addEventListener("click", () => {
    openBrowserAssist(Number(node.dataset.id)).catch((error) => toast(error.message));
  }));
  $$(".scenario-delete").forEach((node) => node.addEventListener("click", () => {
    deleteSearchScenario(Number(node.dataset.id), node.dataset.name).catch((error) => toast(error.message));
  }));
  $("#delete-all-scenarios")?.addEventListener("click", () => {
    deleteAllSearchScenarios(scenarios.length).catch((error) => toast(error.message));
  });
  $("#search-run-list").innerHTML = runs.length
    ? `<h3 class="subsection-title">Последние запуски API</h3>${runs.slice(0, 12).map((run) => `
      <div class="run-row ${escapeAttr(run.status)}">
        <div><strong>${escapeHtml(run.scenario_name)}</strong><small>${runStatusLabels[run.status] || run.status}${run.error ? ` · ${escapeHtml(run.error)}` : ""}</small></div>
        <span>${run.processed}/${run.found || "?"} · новых ${run.imported}</span>
      </div>`).join("")}` : "";
}

async function deleteSearchScenario(scenarioId, name) {
  if (!window.confirm(`Удалить сценарий «${name}»? Собранные вакансии останутся в базе.`)) return;
  await api(`/api/search/scenarios/${scenarioId}/delete`, { method: "POST", body: "{}" });
  toast("Сценарий удален");
  await Promise.all([loadSearchState(), loadDashboard()]);
}

async function deleteAllSearchScenarios(count) {
  if (!count) {
    toast("Список сценариев уже пуст");
    return;
  }
  const confirmed = window.confirm(
    `Удалить все поисковые сценарии (${count})? Вакансии, профиль и письма останутся. Действие нельзя отменить.`,
  );
  if (!confirmed) return;
  const result = await api("/api/search/scenarios/delete-all", {
    method: "POST",
    body: JSON.stringify({ confirm: "DELETE_ALL_SEARCH_SCENARIOS" }),
  });
  toast(`Удалено сценариев: ${result.deleted}`);
  await Promise.all([loadSearchState(), loadDashboard()]);
}

async function createIntentScenarios() {
  const intent = fieldValue("#search-intent").trim();
  if (intent.length < 20) throw new Error("Опишите желаемую работу немного подробнее.");
  const areaId = fieldValue("#hh-area") || fieldValue("#hh-area-primary") || "1";
  const area = hhAreas.find((item) => String(item.id) === String(areaId));
  const button = $("#create-intent-scenarios");
  const status = $("#intent-status");
  button.disabled = true;
  button.textContent = "Ollama анализирует...";
  status.textContent = "Сопоставляю описание с профилем и примерами вакансий. Это может занять до нескольких минут.";
  try {
    const result = await api("/api/search/scenarios/from-intent", {
      method: "POST",
      body: JSON.stringify({
        intent,
        area_id: areaId,
        area_name: area?.name || $("#hh-area-primary").selectedOptions[0]?.textContent || "Москва",
        salary: fieldValue("#hh-salary"),
        period: fieldValue("#hh-period"),
        result_limit: fieldValue("#hh-result-limit"),
        only_with_salary: fieldChecked("#hh-only-salary"),
        work_format: fieldValue("#hh-work-format"),
      }),
    });
    const names = result.items.map((item) => item.query).join(", ");
    status.textContent = `Создано ${result.created}, обновлено ${result.updated}. Модель ${result.model}: ${names}`;
    toast(`ИИ подготовил сценариев: ${result.items.length}`);
    await Promise.all([loadSearchState(), loadDashboard()]);
  } catch (error) {
    status.textContent = error.message;
    throw error;
  } finally {
    button.disabled = false;
    button.textContent = "Создать сценарии";
  }
}

async function saveSearchScenarios() {
  if (!searchSuggestions.length) await generateSearchSuggestions();
  const areaId = fieldValue("#hh-area") || fieldValue("#hh-area-primary") || "1";
  const area = hhAreas.find((item) => String(item.id) === String(areaId));
  const payload = {
    contact: fieldValue("#hh-contact").trim(),
    area_id: areaId,
    area_name: area?.name || $("#hh-area-primary").selectedOptions[0]?.textContent || "Москва",
    salary: fieldValue("#hh-salary"),
    period: fieldValue("#hh-period"),
    result_limit: fieldValue("#hh-result-limit"),
    only_with_salary: fieldChecked("#hh-only-salary"),
    work_format: fieldValue("#hh-work-format"),
  };
  const result = await api("/api/search/scenarios/from-profile", { method: "POST", body: JSON.stringify(payload) });
  toast(`Сценарии сохранены: ${result.total}`);
  await Promise.all([loadSearchState(), loadDashboard()]);
}

async function openBrowserAssist(scenarioId = null) {
  const popup = window.open("", "_blank");
  if (!popup) throw new Error("Браузер заблокировал новую вкладку. Разрешите всплывающие окна для Career Bot.");
  popup.document.title = "Career Bot";
  popup.document.body.textContent = "Открываю безопасный поиск hh.ru...";
  try {
    const plan = await api("/api/search/browser-plan");
    browserPlan = plan.items || [];
    const target = scenarioId
      ? browserPlan.find((item) => Number(item.id) === Number(scenarioId))
      : browserPlan[0];
    if (!target) throw new Error("Нет включенных поисковых сценариев.");
    popup.opener = null;
    popup.location.replace(target.url);
    toast(`Открыт сценарий: ${target.name}`);
  } catch (error) {
    popup.close();
    throw error;
  }
}

async function runApiSearch() {
  const result = await api("/api/search/run-all", { method: "POST", body: "{}" });
  toast(`API-сценариев запущено: ${result.queued}`);
  await Promise.all([loadSearchState(), loadDashboard()]);
}

async function stopAutoSearch() {
  const result = await api("/api/search/stop", { method: "POST", body: "{}" });
  toast(result.stopping ? "Поиск останавливается" : "Активного поиска нет");
  await Promise.all([loadSearchState(), loadDashboard()]);
}

async function generateBatchLetters() {
  const payload = { min_score: fieldValue("#batch-min-score") || 65, scope: fieldValue("#batch-scope"), limit: 100 };
  const result = await api("/api/vacancies/batch-letter", { method: "POST", body: JSON.stringify(payload) });
  const skipped = result.skipped_incomplete ? ` Без полного описания пропущено: ${result.skipped_incomplete}.` : "";
  toast(`В очередь писем: ${result.queued}.${skipped}`);
  await Promise.all([loadVacancies(), loadLetterBatchProgress()]);
}

async function loadLetterBatchProgress() {
  const panel = $("#letter-batch-progress");
  if (!panel) return;
  const progress = await api("/api/letters/progress");
  if (!progress.total) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  const completed = progress.done + progress.error;
  const state = progress.active
    ? `Готово ${progress.done} из ${progress.total} · в очереди: ${progress.queued}${progress.running ? " · ИИ пишет: 1" : ""}`
    : `Партия завершена: готово ${progress.done} из ${progress.total}${progress.error ? ` · ошибок: ${progress.error}` : ""}`;
  panel.innerHTML = `${escapeHtml(state)}<progress value="${completed}" max="${progress.total}"></progress>`;
}

async function approveSelectedLetters() {
  const ids = Array.from(selectedLettersForApproval);
  if (!ids.length) throw new Error("Отметьте хотя бы одно готовое письмо.");
  const result = await api("/api/vacancies/batch-approve-letter", { method: "POST", body: JSON.stringify({ ids }) });
  selectedLettersForApproval.clear();
  toast(`Подтверждено писем: ${result.approved}. Теперь для них доступна подготовка отклика.`);
  await loadVacancies();
}

async function approveAllLetters() {
  if (!window.confirm("Одобрить все уже подготовленные письма? Их можно будет использовать для подготовки откликов на hh.ru.")) return;
  const result = await api("/api/vacancies/batch-approve-letter", { method: "POST", body: JSON.stringify({ all: true }) });
  selectedLettersForApproval.clear();
  toast(`Одобрено подготовленных писем: ${result.approved}.`);
  await loadVacancies();
}

async function startBatchApply() {
  throw new Error("Автоотправка временно отключена. В карточке вакансии используйте «Диагностика без отправки».");
  const confirmed = window.confirm(
    "Запустить пакет простых откликов? Career Bot обработает до 40 одобренных писем: вставит только текст сопроводительного письма и отправит отклик, если форма не требует вопросов, тестов или других действий. Сложные формы будут пропущены.",
  );
  if (!confirmed) return;
  const popup = window.open("", "_blank");
  if (!popup) throw new Error("Браузер заблокировал вкладку hh.ru. Разрешите всплывающие окна для Career Bot и запустите пакет снова.");
  try {
    popup.document.title = "Career Bot";
    popup.document.body.textContent = "Готовлю пакет откликов...";
    const limit = Math.max(1, Math.min(40, Number(fieldValue("#batch-apply-limit")) || 40));
    const result = await api("/api/vacancies/batch-apply-session", { method: "POST", body: JSON.stringify({ limit }) });
    popup.location.replace(result.url);
    toast(`Запущен пакет: ${result.total} откликов. Расширение ведет их в одной вкладке hh.ru.`);
    await loadApplyBatchProgress();
  } catch (error) {
    popup.close();
    throw error;
  }
}

async function loadApplyBatchProgress() {
  const panel = $("#apply-batch-progress");
  if (!panel) return;
  const progress = await api("/api/apply/batches/latest");
  $("#pause-batch-apply").hidden = !progress.active;
  $("#resume-batch-apply").hidden = progress.status !== "paused" || !progress.pending;
  if (!progress.total) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  const completed = (progress.sent || 0) + (progress.skipped || 0) + (progress.needs_manual || 0) + (progress.failed || 0);
  const parts = [`Отправлено: ${progress.sent || 0} из ${progress.total}`];
  if (progress.status === "paused") parts.unshift("Пакет остановлен");
  if (progress.pending) parts.push(`осталось: ${progress.pending}`);
  if (progress.running) parts.push("обрабатывается: 1");
  if (progress.needs_manual) parts.push(`ручная проверка: ${progress.needs_manual}`);
  if (progress.skipped) parts.push(`пропущено: ${progress.skipped}`);
  if (progress.failed) parts.push(`ошибки: ${progress.failed}`);
  panel.innerHTML = `${escapeHtml(parts.join(" · "))}<progress value="${completed}" max="${progress.total}"></progress>`;
}

async function loadApplyDiagnostic() {
  const panel = $("#apply-diagnostic-report");
  if (!panel) return;
  const report = await api("/api/apply/diagnostic/latest");
  panel.hidden = !report.payload;
  if (!report.payload) return;
  const payload = JSON.parse(report.payload);
  panel.textContent = `${report.title} · ${report.created_at}\n${JSON.stringify(payload, null, 2)}`;
}

async function pauseApplyBatch() {
  await api("/api/apply/batches/pause", { method: "POST", body: "{}" });
  toast("Очередь остановлена. Закройте старую вкладку рассылки hh.ru: уже начатое нажатие нельзя отменить.");
  await loadApplyBatchProgress();
}

async function resumeApplyBatch() {
  throw new Error("Возобновление отправки отключено до завершения диагностики.");
  if (!window.confirm("Продолжить отправку только нетронутых вакансий? Закройте старую вкладку рассылки. Прерванные отклики повторяться не будут.")) return;
  const popup = window.open("", "_blank");
  if (!popup) throw new Error("Разрешите открытие вкладки для Career Bot.");
  try {
    const result = await api("/api/apply/batches/resume", { method: "POST", body: "{}" });
    popup.opener = null;
    popup.location.replace(result.url);
    await loadApplyBatchProgress();
  } catch (error) {
    popup.close();
    throw error;
  }
}

function fillStatusFilter() {
  const select = $("#filter-status");
  Object.entries(statusLabels).forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  });
}

function queryString() {
  const params = new URLSearchParams();
  const q = $("#filter-q").value.trim();
  const status = $("#filter-status").value;
  const eligibility = $("#filter-eligibility").value;
  const minScore = $("#filter-min-score").value;
  const source = $("#filter-source").value.trim();
  const sort = $("#filter-sort")?.value || "score";
  if (q) params.set("q", q);
  if (status) params.set("status", status);
  if (eligibility) params.set("eligibility", eligibility);
  if (minScore) params.set("min_score", minScore);
  if (source) params.set("source", source);
  if (sort && sort !== "score") params.set("sort", sort);
  const text = params.toString();
  return text ? `?${text}` : "";
}

function vacancyDetailIsBeingUsed() {
  const detail = $("#vacancy-detail");
  if (!detail) return false;
  return detail.matches(":hover") || detail.contains(document.activeElement);
}

async function loadVacancies({ background = false } = {}) {
  if (background && vacancyDetailIsBeingUsed()) return false;
  const requestId = ++vacancyLoadSequence;
  const list = $("#vacancy-list");
  const feedback = $("#filter-feedback");
  vacancyLoadsInFlight += 1;
  list.setAttribute("aria-busy", "true");
  list.classList.add("filter-loading");
  feedback.textContent = "Обновляю список...";
  try {
    const nextVacancies = await api(`/api/vacancies${queryString()}`);
    if (requestId !== vacancyLoadSequence) return false;
    // A user may move into the detail panel while the background request is in flight.
    // Do not replace controls underneath an active pointer or keyboard focus.
    if (background && vacancyDetailIsBeingUsed()) return false;
    vacancies = nextVacancies;
    renderVacancyList();
    feedback.textContent = `Показано вакансий: ${vacancies.length}`;
    if (selectedId) {
      const selected = vacancies.find((item) => item.id === selectedId);
      selected ? renderDetail(selected) : clearDetail();
    }
    return true;
  } catch (error) {
    if (requestId !== vacancyLoadSequence) return false;
    feedback.textContent = `Не удалось обновить список: ${error.message}`;
    throw error;
  } finally {
    vacancyLoadsInFlight = Math.max(0, vacancyLoadsInFlight - 1);
    if (requestId === vacancyLoadSequence) {
      list.removeAttribute("aria-busy");
      list.classList.remove("filter-loading");
    }
  }
}

function refreshVacancyFilters() {
  window.clearTimeout(vacancyFilterTimer);
  vacancyFilterTimer = null;
  loadVacancies().catch((error) => toast(error.message));
}

function scheduleVacancyFilterRefresh() {
  window.clearTimeout(vacancyFilterTimer);
  vacancyFilterTimer = window.setTimeout(refreshVacancyFilters, 180);
}

function renderVacancyList() {
  const list = $("#vacancy-list");
  if (!vacancies.length) {
    list.innerHTML = '<div class="note">Пока нет вакансий под выбранные фильтры.</div>';
    return;
  }
  list.innerHTML = vacancies
    .map(
      (item) => `
        <div class="vacancy-item ${item.id === selectedId ? "active" : ""}" data-id="${item.id}">
          <label class="checkline"><input class="approve-select" type="checkbox" data-id="${item.id}" ${selectedLettersForApproval.has(item.id) ? "checked" : ""} ${item.cover_letter ? "" : "disabled"} /> В пакет</label>
          <h3>${escapeHtml(item.title)}</h3>
          <p>${escapeHtml([item.company, item.location].filter(Boolean).join(" · ") || item.source)}</p>
          <div class="meta">
            <span class="pill score">${item.score}/100</span>
            <span class="pill eligibility-${escapeAttr(item.eligibility?.status || "review")}">${escapeHtml(item.eligibility?.label || "Нужно проверить")}</span>
            <span class="pill">${statusLabels[item.status] || item.status}</span>
            <span class="pill">${escapeHtml(item.source || "manual")}</span>
            ${["queued", "running"].includes(item.letter_job_status) ? `<span class="pill queue-pill">${item.letter_job_status === "queued" ? "В очереди" : "ИИ пишет"}</span>` : ""}
          </div>
        </div>
      `,
    )
    .join("");
  $$(".vacancy-item").forEach((node) =>
    node.addEventListener("click", () => {
      selectedId = Number(node.dataset.id);
      const vacancy = vacancies.find((item) => item.id === selectedId);
      renderVacancyList();
      renderDetail(vacancy);
    }),
  );
  $$(".approve-select").forEach((box) => box.addEventListener("click", (event) => {
    event.stopPropagation();
    const id = Number(box.dataset.id);
    if (box.checked) selectedLettersForApproval.add(id); else selectedLettersForApproval.delete(id);
  }));
}

function clearDetail() {
  $("#vacancy-detail").className = "detail empty";
  $("#vacancy-detail").textContent = "Выберите вакансию";
}

function renderDetail(vacancy) {
  const url = vacancy.url ? `<a href="${escapeAttr(vacancy.url)}" target="_blank" rel="noreferrer">Открыть источник</a>` : "";
  const aiAllowed = Boolean(currentUser?.can_use_ai);
  const evidence = (vacancy.letter_evidence || [])
    .map((item) => {
      const verification = ["exact", "close", "warning"].includes(item.verification) ? item.verification : "exact";
      const labels = { exact: "Подтверждено", close: "Близкий пересказ", warning: "Нужно проверить" };
      return `<div class="evidence-item ${verification}">
        <div class="evidence-head"><strong>${escapeHtml(item.requirement || "Основание")}</strong><span>${labels[verification]}</span></div>
        <p>${escapeHtml(item.quote)}</p>
        ${item.claim ? `<small>${escapeHtml(item.claim)}</small>` : ""}
        ${item.note ? `<small>${escapeHtml(item.note)}</small>` : ""}
      </div>`;
    })
    .join("");
  const insights = vacancy.insights || {};
  const requirements = (insights.requirements || [])
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
  const keywordChips = (insights.keywords || [])
    .map((item) => `<span class="insight-chip">${escapeHtml(item)}</span>`)
    .join("");
  const matchedChips = (insights.matched_keywords || [])
    .map((item) => `<span class="insight-chip matched">${escapeHtml(item)}</span>`)
    .join("");
  const queueLabels = { queued: "В очереди", running: "ИИ пишет письмо", done: "Письмо готово", error: "Ошибка генерации" };
  const queueStatus = vacancy.letter_job_status || "";
  const queueBusy = queueStatus === "queued" || queueStatus === "running";
  const eligibility = vacancy.eligibility || { label: "Нужно проверить", status: "review", checks: [] };
  const eligibilityChecks = (eligibility.checks || [])
    .map((check) => `<li class="check-${escapeAttr(check.status)}"><strong>${escapeHtml(check.criterion)}:</strong> ${escapeHtml(check.reason)}</li>`)
    .join("");
  const scoreParts = vacancy.score_components || {};
  const scoreBreakdown = [
    ["Задачи", scoreParts.task_fit, 35], ["Перспектива", scoreParts.prospects, 25],
    ["Интерес", scoreParts.interest, 20], ["Условия", scoreParts.conditions, 15], ["Данные", scoreParts.data_quality, 5],
  ].map(([label, value, max]) => `<span>${escapeHtml(label)}<br><strong>${Number(value || 0)}/${max}</strong></span>`).join("");
  const plannedFacts = (vacancy.evidence_plan?.selected_facts || [])
    .map((fact) => `<li><strong>${escapeHtml(fact.experience_type || "Подтверждённый факт")}</strong><br>
      <small>Источник: ${escapeHtml(fact.source_label || "")}</small><br>
      ${fact.what_did?.length ? `Что делал: ${escapeHtml(fact.what_did.slice(0, 2).join("; "))}<br>` : ""}
      ${fact.results?.length ? `Результат: ${escapeHtml(fact.results.slice(0, 1).join(""))}` : ""}</li>`)
    .join("");
  const tierLabels = { deep: "Глубокое письмо", short: "Короткое письмо", manual: "Ручное решение", blocked: "Исключено" };
  $("#vacancy-detail").className = "detail";
  $("#vacancy-detail").innerHTML = `
    <h3>${escapeHtml(vacancy.title)}</h3>
    <p>${escapeHtml([vacancy.company, vacancy.location, vacancy.salary].filter(Boolean).join(" · "))}</p>
    <div class="meta">
      <span class="pill score">${vacancy.score}/100</span>
      <span class="pill tier-${escapeAttr(vacancy.generation_tier || "manual")}">${escapeHtml(tierLabels[vacancy.generation_tier] || "Ручное решение")}</span>
      <span class="pill eligibility-${escapeAttr(eligibility.status)}">${escapeHtml(eligibility.label)}</span>
      <span class="pill">${statusLabels[vacancy.status] || vacancy.status}</span>
      <span class="pill">${escapeHtml(vacancy.source || "manual")}</span>
      ${url}
    </div>
    <div class="score-breakdown">${scoreBreakdown}</div>
    ${plannedFacts ? `<div class="eligibility-panel"><h4>Факты для письма</h4><ul>${plannedFacts}</ul></div>` : ""}
    <div class="detail-actions">
      <select id="detail-status">
        ${Object.entries(statusLabels)
          .map(([value, label]) => `<option value="${value}" ${value === vacancy.status ? "selected" : ""}>${label}</option>`)
          .join("")}
      </select>
      <button id="save-status">Сменить статус</button>
      <button id="generate-letter" class="secondary" ${aiAllowed && !queueBusy ? "" : "disabled"} title="${aiAllowed ? "Добавить генерацию в очередь" : "AI-генерация отключена для тестировщика"}">${aiAllowed ? (queueLabels[queueStatus] || (vacancy.cover_letter ? "Перегенерировать письмо" : "Сгенерировать письмо")) : "AI недоступен"}</button>
      <button id="approve-letter" class="secondary" ${vacancy.cover_letter && !vacancy.letter_approved ? "" : "disabled"}>${vacancy.letter_approved ? "Письмо одобрено" : "Одобрить письмо"}</button>
      <button id="safe-apply" ${vacancy.letter_approved && vacancy.url.includes("hh.ru/vacancy/") ? "" : "disabled"}>Подготовить отклик на hh.ru</button>
      <button id="diagnose-apply" ${vacancy.letter_approved ? "" : "disabled"}>Диагностика без отправки</button>
      <button id="archive-vacancy" class="archive-action" ${vacancy.status === "archived" ? "disabled" : ""}>${vacancy.status === "archived" ? "В архиве" : "Архивировать"}</button>
      <button id="delete-vacancy" class="danger">Удалить</button>
    </div>
    <div class="eligibility-panel"><h4>Проверка обязательных условий</h4>${eligibilityChecks ? `<ul>${eligibilityChecks}</ul>` : "<p>Недостаточно данных для проверки.</p>"}</div>
    <div class="vacancy-insights">
      <div class="insight-heading">
        <div><span class="eyebrow">АНАЛИЗ ВАКАНСИИ</span><h4>Что ищет работодатель</h4></div>
        <span class="data-quality ${insights.description_complete ? "complete" : "thin"}">${insights.description_complete ? "Полное описание" : "Мало данных"}</span>
      </div>
      ${requirements ? `<ul>${requirements}</ul>` : '<p class="muted-copy">Требования не распознаны. Повторно добавьте вакансию через обновленное расширение hh.ru.</p>'}
      ${keywordChips ? `<h5>Ключевые слова вакансии</h5><div class="insight-chips">${keywordChips}</div>` : ""}
      ${matchedChips ? `<h5>Подтверждены вашим профилем</h5><div class="insight-chips">${matchedChips}</div>` : '<p class="muted-copy">Явные совпадения с профилем пока не найдены.</p>'}
      <p class="insight-note">В письмо попадают только ключевые слова, подтвержденные вашим профилем. Простое повторение текста вакансии не повышает качество отклика.</p>
    </div>
    <h4>Объяснение скоринга</h4>
    <div class="explain">${escapeHtml((vacancy.score_explanation || []).join("\n"))}</div>
    <h4>Сопроводительное письмо</h4>
    ${queueStatus ? `<div class="queue-status ${escapeAttr(queueStatus)}">${escapeHtml(queueLabels[queueStatus] || queueStatus)}${vacancy.letter_job_error ? `: ${escapeHtml(vacancy.letter_job_error)}` : ""}</div>` : ""}
    <textarea id="letter-editor" class="letter-editor" ${vacancy.cover_letter ? "" : "disabled"}>${escapeHtml(vacancy.cover_letter || "Письмо еще не создано.")}</textarea>
    ${vacancy.cover_letter ? `<div class="detail-actions"><button id="save-letter-text" class="secondary">Сохранить изменения</button></div>
      <div class="regenerate-letter-panel"><span>Не понравился вариант?</span><button id="regenerate-letter" class="secondary" ${aiAllowed && !queueBusy ? "" : "disabled"}>↻ Перегенерировать письмо</button></div>` : ""}
    ${evidence ? `<h4>Проверка фактов</h4><div class="letter-evidence">${evidence}</div>` : ""}
    <h4>Описание</h4>
    <div class="description">${escapeHtml(vacancy.description)}</div>
    <h4>Заметки</h4>
    <textarea id="detail-notes">${escapeHtml(vacancy.notes || "")}</textarea>
    <div class="detail-actions">
      <button id="save-notes" class="secondary">Сохранить заметки</button>
    </div>
  `;

  $("#save-status").addEventListener("click", async () => {
    const updated = await api(`/api/vacancies/${vacancy.id}/status`, {
      method: "POST",
      body: JSON.stringify({ status: $("#detail-status").value }),
    });
    toast("Статус обновлен");
    await loadVacancies();
    renderDetail(updated);
  });

  $("#archive-vacancy").addEventListener("click", async () => {
    const updated = await api(`/api/vacancies/${vacancy.id}/status`, {
      method: "POST",
      body: JSON.stringify({ status: "archived" }),
    });
    toast("Вакансия перемещена в архив");
    await loadVacancies();
    renderDetail(updated);
  });

  $("#delete-vacancy").addEventListener("click", async () => {
    if (!window.confirm(`Удалить вакансию «${vacancy.title}»? Это действие нельзя отменить.`)) return;
    await api(`/api/vacancies/${vacancy.id}/delete`, {
      method: "POST",
      body: JSON.stringify({ confirm: "DELETE_VACANCY" }),
    });
    selectedId = null;
    await Promise.all([loadVacancies(), loadDashboard()]);
    clearDetail();
    toast("Вакансия удалена");
  });

  if (aiAllowed) {
    const queueLetter = async (button) => {
      button.disabled = true;
      button.textContent = "Добавляю в очередь...";
      try {
        await api(`/api/vacancies/${vacancy.id}/letter`, {
          method: "POST",
          body: JSON.stringify({}),
        });
        toast("Генерация добавлена в очередь. Можно открыть другую вакансию.");
        await loadVacancies();
        const updated = vacancies.find((item) => item.id === vacancy.id);
        if (updated) renderDetail(updated);
      } catch (error) {
        button.disabled = false;
        button.textContent = vacancy.cover_letter ? "↻ Перегенерировать письмо" : "Сгенерировать письмо";
        toast(error.message);
      }
    };
    $("#generate-letter").addEventListener("click", () => queueLetter($("#generate-letter")));
    const regenerateButton = $("#regenerate-letter");
    if (regenerateButton) regenerateButton.addEventListener("click", () => queueLetter(regenerateButton));
  }

  $("#diagnose-apply").addEventListener("click", async () => {
    const popup = window.open("", "_blank");
    if (!popup) return toast("Разрешите открытие вкладок для Career Bot.");
    try {
      const result = await api(`/api/vacancies/${vacancy.id}/diagnostic-session`, { method: "POST", body: "{}" });
      popup.opener = null;
      popup.location.replace(result.url);
      toast("Диагностика запущена. Она не нажимает кнопки hh.ru и не отправляет отклики.");
    } catch (error) {
      popup.close();
      toast(error.message);
    }
  });
  $("#safe-apply").addEventListener("click", async () => {
    const result = await api(`/api/vacancies/${vacancy.id}/apply-session`, { method: "POST", body: "{}" });
    window.open(result.url, "_blank", "noopener,noreferrer");
    toast("Открыта подготовка отклика. Само открытие не означает отправку.");
    await Promise.all([loadVacancies(), loadDashboard()]);
  });

  $("#approve-letter").addEventListener("click", async () => {
    const updated = await api(`/api/vacancies/${vacancy.id}/approve-letter`, { method: "POST", body: "{}" });
    renderDetail(updated);
    toast("Письмо одобрено для Safe Apply");
  });

  if (vacancy.cover_letter) {
    $("#save-letter-text").addEventListener("click", async () => {
      const updated = await api(`/api/vacancies/${vacancy.id}/letter-text`, {
        method: "POST",
        body: JSON.stringify({ letter: $("#letter-editor").value }),
      });
      renderDetail(updated);
      toast("Изменения сохранены. Одобрите итоговое письмо заново.");
    });
  }

  $("#save-notes").addEventListener("click", async () => {
    await api(`/api/vacancies/${vacancy.id}/notes`, {
      method: "POST",
      body: JSON.stringify({ notes: $("#detail-notes").value }),
    });
    toast("Заметки сохранены");
  });
}

async function deleteAllVacancies() {
  if (!vacancies.length) {
    toast("Список вакансий уже пуст");
    return;
  }
  const confirmed = window.confirm(
    "Удалить все вакансии текущего пользователя вместе с письмами и заметками? Профиль и настройки ИИ сохранятся. Действие нельзя отменить.",
  );
  if (!confirmed) return;
  const result = await api("/api/vacancies/delete-all", {
    method: "POST",
    body: JSON.stringify({ confirm: "DELETE_ALL_VACANCIES" }),
  });
  selectedId = null;
  await Promise.all([loadVacancies(), loadDashboard()]);
  clearDetail();
  toast(`Удалено вакансий: ${result.deleted}`);
}

async function importVacancies() {
  const result = await api("/api/import", {
    method: "POST",
    body: JSON.stringify({
      source: $("#import-source").value,
      format: $("#import-format").value,
      text: $("#import-text").value,
    }),
  });
  toast(`Импортировано: ${result.created}`);
  $("#import-text").value = "";
  await loadDashboard();
}

function runHhSearch() {
  const text = fieldValue("#hh-text").trim();
  if (!text) {
    toast("Введите поисковый запрос");
    return;
  }
  const params = new URLSearchParams({ text });
  const area = fieldValue("#hh-area").trim();
  const salary = fieldValue("#hh-salary").trim();
  const period = fieldValue("#hh-period").trim();
  if (area) params.set("area", area);
  if (salary) params.set("salary", salary);
  if (period) params.set("period", period);
  if (fieldChecked("#hh-only-salary")) params.set("only_with_salary", "true");
  params.set("order_by", "publication_time");
  window.open(`https://hh.ru/search/vacancy?${params.toString()}`, "_blank", "noopener,noreferrer");
}

function syncSearchArea() {
  const name = fieldValue("#hh-area-name").trim();
  const match = hhAreas.find((area) => area.name.toLowerCase() === name.toLowerCase());
  $("#hh-area").value = match?.id || fieldValue("#hh-area-primary");
}

function syncPrimarySearchArea() {
  $("#hh-area").value = fieldValue("#hh-area-primary") || "1";
  if (!$("#area-detail").hidden && fieldValue("#hh-area-name").trim()) syncSearchArea();
}

function toggleAreaDetail() {
  const detail = $("#area-detail");
  const willOpen = detail.hidden;
  detail.hidden = !willOpen;
  $("#toggle-area-detail").textContent = willOpen ? "Скрыть уточнение" : "Уточнить";
  if (willOpen) {
    $("#hh-area-name").focus();
    return;
  }
  $("#hh-area-name").value = "";
  syncPrimarySearchArea();
}

async function setupHhButton() {
  await api("/api/setup/hh-extension", { method: "POST", body: "{}" });
  toast("Открываю установку кнопки для hh.ru");
}

function renderSearchResults(result) {
  if (!hhSearchResults.length) {
    $("#search-results").innerHTML = '<div class="note">hh.ru ничего не вернул по этому запросу.</div>';
    return;
  }
  $("#search-results").innerHTML = `
    <p class="muted">Показано ${hhSearchResults.length} из ${result.found || hhSearchResults.length}. Отсортировано по нашему скорингу.</p>
    ${hhSearchResults
      .map(
        (item, index) => `
          <div class="search-item">
            <div>
              <h3>${escapeHtml(item.title)}</h3>
              <p>${escapeHtml([item.company, item.location, item.salary].filter(Boolean).join(" · "))}</p>
              <div class="meta">
                <span class="pill score">${item.score}/100</span>
                <span class="pill">hh-api</span>
                ${item.url ? `<a href="${escapeAttr(item.url)}" target="_blank" rel="noreferrer">Открыть</a>` : ""}
              </div>
            </div>
            <button class="secondary import-one-search" data-index="${index}">Добавить</button>
          </div>
        `,
      )
      .join("")}
  `;
  $$(".import-one-search").forEach((button) =>
    button.addEventListener("click", async () => {
      const item = hhSearchResults[Number(button.dataset.index)];
      await importSearchItems([item]);
      button.textContent = "Добавлено";
      button.disabled = true;
    }),
  );
}

async function importSearchItems(items) {
  if (!items.length) {
    toast("Нет найденных вакансий для добавления");
    return;
  }
  const result = await api("/api/import", {
    method: "POST",
    body: JSON.stringify({
      source: "hh-api",
      format: "json",
      text: JSON.stringify(items),
    }),
  });
  toast(`Добавлено в базу: ${result.created}`);
  await loadDashboard();
}

async function saveManualVacancy(event) {
  event.preventDefault();
  const form = $("#manual-form");
  const payload = Object.fromEntries(new FormData(form).entries());
  payload.source = "manual";
  await api("/api/vacancies", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  $("#manual-dialog").close();
  form.reset();
  toast("Вакансия добавлена");
  await loadVacancies();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}

function bindEvents() {
  $$(".nav").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
  $("#save-profile").addEventListener("click", saveProfile);
  $("#ai-settings-form").addEventListener("submit", (event) => saveAiSettings(event).catch((error) => toast(error.message)));
  $("#ai-provider").addEventListener("change", () => syncAiProvider(true));
  $("#clear-ai-key").addEventListener("click", () => clearAiKey().catch((error) => toast(error.message)));
  $("#refresh-dashboard").addEventListener("click", loadDashboard);
  $("#start-browser-assist").addEventListener("click", () => openBrowserAssist().catch((error) => toast(error.message)));
  $("#generate-batch-letters").addEventListener("click", () => generateBatchLetters().catch((error) => toast(error.message)));
  $("#approve-selected-letters")?.addEventListener("click", () => approveSelectedLetters().catch((error) => toast(error.message)));
  $("#approve-all-letters")?.addEventListener("click", () => approveAllLetters().catch((error) => toast(error.message)));
  $("#start-batch-apply")?.addEventListener("click", () => startBatchApply().catch((error) => toast(error.message)));
  $("#pause-batch-apply")?.addEventListener("click", () => pauseApplyBatch().catch((error) => toast(error.message)));
  $("#resume-batch-apply")?.addEventListener("click", () => resumeApplyBatch().catch((error) => toast(error.message)));
  $("#run-hh-search").addEventListener("click", runHhSearch);
  $("#generate-search-suggestions").addEventListener("click", generateSearchSuggestions);
  $("#create-intent-scenarios").addEventListener("click", () => createIntentScenarios().catch((error) => toast(error.message)));
  $("#save-search-scenarios").addEventListener("click", () => saveSearchScenarios().catch((error) => toast(error.message)));
  $("#run-browser-assist").addEventListener("click", () => openBrowserAssist().catch((error) => toast(error.message)));
  $("#run-api-search").addEventListener("click", () => runApiSearch().catch((error) => toast(error.message)));
  $("#stop-api-search").addEventListener("click", () => stopAutoSearch().catch((error) => toast(error.message)));
  $("#hh-suggestion").addEventListener("change", (event) => applySearchSuggestion(Number(event.target.value)));
  $("#hh-text").addEventListener("change", () => {
    const item = searchSuggestions.find((suggestion) => suggestion.query === $("#hh-text").value);
    if (item) $("#suggestion-reason").textContent = item.reason;
  });
  $("#hh-area-name").addEventListener("input", () => {
    syncSearchArea();
    requestAreaSuggestions($("#hh-area-name").value, syncSearchArea);
  });
  $("#hh-area-name").addEventListener("change", syncSearchArea);
  $("#hh-area-primary").addEventListener("change", syncPrimarySearchArea);
  $("#toggle-area-detail").addEventListener("click", toggleAreaDetail);
  $("#profile-area-primary").addEventListener("change", updateProfilePrimaryArea);
  $("#toggle-profile-area-detail").addEventListener("click", toggleProfileAreaDetail);
  $("#setup-hh-button").addEventListener("click", setupHhButton);
  $("#import-vacancies").addEventListener("click", importVacancies);
  $("#filter-status").addEventListener("change", refreshVacancyFilters);
  $("#filter-eligibility").addEventListener("change", refreshVacancyFilters);
  $("#filter-sort")?.addEventListener("change", refreshVacancyFilters);
  [$("#filter-min-score"), $("#filter-q"), $("#filter-source")].forEach((node) => {
    node.addEventListener("input", scheduleVacancyFilterRefresh);
    node.addEventListener("change", refreshVacancyFilters);
    node.addEventListener("search", refreshVacancyFilters);
    node.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      refreshVacancyFilters();
    });
  });
  $("#add-vacancy").addEventListener("click", () => $("#manual-dialog").showModal());
  $("#delete-all-vacancies").addEventListener("click", () => deleteAllVacancies().catch((error) => toast(error.message)));
  $("#save-manual").addEventListener("click", saveManualVacancy);
  $("#resume-pdf").addEventListener("change", (event) => uploadResumePdf(event.target.files?.[0]).catch((error) => toast(error.message)));
}

async function bootApp() {
  fillStatusFilter();
  const healthPromise = api("/api/health")
    .then((health) => { $("#app-version").textContent = `Career Bot · v${health.version}`; })
    .catch(() => { $("#app-version").textContent = "Career Bot"; });
  await Promise.all([loadCatalog(), loadAreas(), healthPromise]);
  initTagPickers();
  bindEvents();
  await Promise.all([loadProfile(), loadDashboard()]);
  vacancyPollTimer = window.setInterval(async () => {
    if (!$("#vacancies").classList.contains("active")) return;
    if (vacancyLoadsInFlight) return;
    if (vacancyDetailIsBeingUsed()) return;
    loadLetterBatchProgress().catch(() => {});
    loadApplyBatchProgress().catch(() => {});
    loadApplyDiagnostic().catch(() => {});
    const hasActiveLetterJobs = vacancies.some((item) => ["queued", "running"].includes(item.letter_job_status));
    if (!hasActiveLetterJobs) return;
    const previous = vacancies.map((item) => `${item.id}:${item.letter_job_status}`).join("|");
    await loadVacancies({ background: true });
    const next = vacancies.map((item) => `${item.id}:${item.letter_job_status}`).join("|");
    if (previous !== next && selectedId) {
      const selected = vacancies.find((item) => item.id === selectedId);
      if (selected) renderDetail(selected);
    }
  }, 2500);
  searchPollTimer = window.setInterval(async () => {
    if (!$("#dashboard").classList.contains("active") && !$("#search").classList.contains("active")) return;
    await Promise.all([
      $("#dashboard").classList.contains("active") ? loadDashboard() : Promise.resolve(),
      $("#search").classList.contains("active") ? loadSearchState() : Promise.resolve(),
    ]);
  }, 2500);
}

startAuth().catch((error) => {
  showAuthView("login");
  showAuthError(error.message);
});
