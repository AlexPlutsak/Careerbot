const BUTTON_CLASS = "career-bot-hh-add";
const CARD_SELECTORS = [
  '[data-qa="serp-item"]',
  '[data-qa="vacancy-serp__vacancy"]',
  '[data-qa="vacancy-serp__vacancy-card"]',
];
const TITLE_SELECTOR =
  '[data-qa="serp-item__title"], [data-qa="vacancy-serp__vacancy-title"], a[href*="/vacancy/"]';
const RESPONSE_SELECTOR = [
  '[data-qa="vacancy-serp__vacancy_response"]',
  '[data-qa="vacancy-serp__vacancy-response"]',
  '[data-qa="vacancy-response-link-top"]',
  'a[href*="vacancy_response"]',
].join(", ");

function parseExperienceYears(value) {
  const text = cleanText(value).toLowerCase();
  const years = Number(text.match(/(\d+)\s*(?:год|года|лет)/)?.[1] || 0);
  const months = Number(text.match(/(\d+)\s*(?:месяц|месяца|месяцев)/)?.[1] || 0);
  return years || months ? String(Math.round((years + months / 12) * 10) / 10) : "";
}

function cleanMultiline(value) {
  const ignored = /^(редактировать|\+?\s*добавить|скрыть|развернуть|показать полностью|поднять в поиске|обновить дату публикации)$/i;
  const lines = String(value || "")
    .replace(/[\u2028\u2029]/g, "\n")
    .split(/\r?\n/)
    .map((line) => line.replace(/\s+/g, " ").trim())
    .filter((line) => line && !ignored.test(line));
  return lines.filter((line, index) => line !== lines[index - 1]).join("\n");
}

const RESUME_SECTIONS = [
  { key: "experience", title: "Опыт работы", selectors: ['[data-qa="resume-block-experience"]'], headings: ["опыт работы"] },
  { key: "education", title: "Образование", selectors: ['[data-qa="resume-block-education"]'], headings: ["образование"] },
  { key: "courses", title: "Повышение квалификации и курсы", selectors: ['[data-qa="resume-block-additional-education"]', '[data-qa="resume-block-courses"]'], headings: ["повышение квалификации, курсы", "курсы"] },
  { key: "tests", title: "Тесты и экзамены", selectors: ['[data-qa="resume-block-attestation-education"]', '[data-qa="resume-block-tests"]'], headings: ["тесты, экзамены", "тесты и экзамены"] },
  { key: "certificates", title: "Сертификаты", selectors: ['[data-qa="resume-block-certificate"]', '[data-qa="resume-block-certificates"]'], headings: ["сертификаты"] },
  { key: "languages", title: "Языки", selectors: ['[data-qa="resume-block-language"]', '[data-qa="resume-block-languages"]'], headings: ["знание языков", "языки"] },
  { key: "skills", title: "Ключевые навыки", selectors: ['[data-qa="resume-block-skills"]', '[data-qa="resume-block-skill-set"]', '[data-qa="resume-block-skills-content"]'], headings: ["ключевые навыки", "навыки"] },
  { key: "about", title: "Обо мне", selectors: ['[data-qa="resume-block-about"]'], headings: ["обо мне"] },
  { key: "driving", title: "Опыт вождения", selectors: ['[data-qa="resume-block-driver-license"]', '[data-qa="resume-block-driving"]'], headings: ["опыт вождения"] },
  { key: "recommendations", title: "Рекомендации", selectors: ['[data-qa="resume-block-recommendation"]'], headings: ["рекомендации"] },
  { key: "portfolio", title: "Портфолио", selectors: ['[data-qa="resume-block-portfolio"]'], headings: ["портфолио"] },
  { key: "citizenship", title: "Гражданство и разрешение на работу", selectors: ['[data-qa="resume-block-citizenship"]', '[data-qa="resume-personal-citizenship"]'], headings: ["гражданство", "разрешение на работу"] },
];

const PROFILE_TEXT_SECTIONS = [
  { key: "experience", title: "Опыт работы", pattern: /^опыт работы(?:\s*:\s*.+)?$/i },
  { key: "education", title: "Образование", pattern: /^образование$/i },
  { key: "courses", title: "Повышение квалификации и курсы", pattern: /^повышение квалификации\s*[,и]\s*курсы$/i },
  { key: "tests", title: "Тесты и экзамены", pattern: /^тесты и экзамены$/i },
  { key: "certificates", title: "Сертификаты", pattern: /^сертификаты$/i },
  { key: "driving", title: "Опыт вождения", pattern: /^опыт вождения$/i },
  { key: "languages", title: "Языки", pattern: /^языки$/i },
  { key: "skills", title: "Ключевые навыки", pattern: /^ключевые навыки$/i },
  { key: "about", title: "Обо мне", pattern: /^обо мне$/i },
  { key: "recommendations", title: "Рекомендации", pattern: /^рекомендации$/i },
  { key: "portfolio", title: "Портфолио", pattern: /^портфолио$/i },
];

const PROFILE_SECTION_STOP = /^(подтверждение навыков и языков|курсы по профессии|похожие резюме|рекомендованные вакансии)/i;
const PROFILE_UI_NOISE = /^(hh pro|продвижение, подсветка резюме|готовое резюме|доверьте составление резюме|репетиция собеседования|подготовьтесь к собеседованию|карьерная консультация|получите советы|мои резюме|заказать резюме|создать резюме|статистика за неделю|показы|просмотры|приглашения|резюме редко попадает|поднимите его|заказать рекомендацию|\d+\s+вакансий|посмотреть|перейти к курсу|ещё\s*[−-]|hh\d+|с нуля|продвинутый)\b.*$/i;

function cleanProfileSection(definition, rawLines) {
  const headingPatterns = PROFILE_TEXT_SECTIONS.map((item) => item.pattern);
  const lines = rawLines
    .map((line) => cleanText(line))
    .filter((line) => line && !headingPatterns.some((pattern) => pattern.test(line)))
    .filter((line) => !PROFILE_UI_NOISE.test(line))
    .filter((line) => !/^[-−]?\d+%$/.test(line) && !/^\d[\d\s]*\s*₽/.test(line));
  if (definition.key === "courses") {
    const hasCourseFacts = lines.some((line) =>
      /(?:университет|академ|институт|школ|курс|сертифик|повышение|обучение|год|месяц)/i.test(line) &&
      !/(?:карьерн|резюме|ваканси|промокод|₽|скидк)/i.test(line),
    );
    if (!hasCourseFacts) return [];
  }
  return lines.filter((line, index) => line !== lines[index - 1]);
}

function resumeSectionsFromProfileText(root) {
  const scope = root.querySelector("main") || root.body || root.documentElement;
  const lines = cleanMultiline(scope?.innerText || scope?.textContent).split("\n").filter(Boolean);
  const boundaries = [];
  let stopped = false;
  lines.forEach((line, index) => {
    if (stopped) return;
    const definition = PROFILE_TEXT_SECTIONS.find((item) => item.pattern.test(line));
    if (definition) boundaries.push({ index, definition });
    else if (PROFILE_SECTION_STOP.test(line)) {
      boundaries.push({ index, definition: null });
      stopped = true;
    }
  });

  const sections = [];
  boundaries.forEach((boundary, boundaryIndex) => {
    if (!boundary.definition) return;
    const end = boundaries[boundaryIndex + 1]?.index ?? lines.length;
    const contentLines = cleanProfileSection(boundary.definition, lines.slice(boundary.index + 1, end));
    if (!contentLines.length) return;
    const text = [boundary.definition.title, ...contentLines].join("\n").slice(0, 16000);
    sections.push({ key: boundary.definition.key, title: boundary.definition.title, text });
  });
  return sections;
}

function findResumeSection(root, definition) {
  for (const selector of definition.selectors) {
    const element = root.querySelector(selector);
    if (element && cleanMultiline(element.innerText || element.textContent).length > definition.title.length) return element;
  }
  const headings = Array.from(root.querySelectorAll("h1, h2, h3, h4, h5, h6, [data-qa], main div, main span"));
  const heading = headings.find((element) => {
    const text = cleanText(element.textContent).toLowerCase();
    return text.length < 100 && definition.headings.some((value) => text === value || text.startsWith(`${value} `));
  });
  if (!heading) return null;
  let candidate = heading.parentElement;
  for (let depth = 0; candidate && depth < 4; depth += 1, candidate = candidate.parentElement) {
    const text = cleanMultiline(candidate.innerText || candidate.textContent);
    if (text.length > cleanText(heading.textContent).length + 10 && text.length < 12000) return candidate;
  }
  return heading.parentElement;
}

function findExactText(root, values) {
  const wanted = values.map((value) => value.toLowerCase());
  return Array.from(root.querySelectorAll("h1, h2, h3, h4, h5, h6, [data-qa], main div, main span, main a"))
    .find((element) => wanted.includes(cleanText(element.textContent).toLowerCase()));
}

function profileResumeTitle(root) {
  const direct = pageText(root, [
    '[data-qa="resume-block-title-position"]',
    '[data-qa="resume-title"]',
    '[data-qa*="resume-title"]',
  ]);
  if (direct) return direct;
  const heading = findExactText(root, ["Мои резюме"]);
  let scope = heading?.parentElement;
  for (let depth = 0; scope && depth < 4; depth += 1, scope = scope.parentElement) {
    const candidates = Array.from(scope.querySelectorAll('a[href*="resume"], h2, h3, h4, strong'));
    const title = candidates.map((element) => cleanText(element.textContent)).find((text) =>
      text && text.length < 140 &&
      !/^(мои резюме|создать резюме|заказать резюме|поднять в поиске|статистика за неделю)$/i.test(text),
    );
    if (title) return title;
  }
  return "";
}

function profileValueAfterLabel(root, labels) {
  const scope = root.querySelector("main") || root.body || root.documentElement;
  const lines = cleanMultiline(scope?.innerText || scope?.textContent).split("\n").filter(Boolean);
  const wanted = labels.map((label) => label.toLowerCase());
  const index = lines.findIndex((line) => wanted.includes(line.toLowerCase()));
  return index >= 0 ? (lines[index + 1] || "") : "";
}

function resumeSectionsFromDocument(root) {
  if (root === document && /^\/applicant\/profile\/me\/?$/i.test(location.pathname)) {
    return resumeSectionsFromProfileText(root);
  }
  const sections = [];
  const used = new Set();
  RESUME_SECTIONS.forEach((definition) => {
    const element = findResumeSection(root, definition);
    if (!element || used.has(element)) return;
    const text = cleanMultiline(element.innerText || element.textContent).slice(0, 16000);
    if (!text) return;
    used.add(element);
    sections.push({ key: definition.key, title: definition.title, text });
  });
  return sections;
}

function profileFromDocument(root) {
  const isProfilePage = root === document && /^\/applicant\/profile\/me\/?$/i.test(location.pathname);
  const targetRole = profileResumeTitle(root);
  const name = pageText(root, [
    '[data-qa="resume-personal-name"]',
    '[data-qa="resume-personal-name-title"]',
    "h1",
  ]).replace(/\s+\d+\s*(?:лет|года|год).*$/i, "").trim();
  const locationValue = pageText(root, [
    '[data-qa="resume-personal-address"]',
    '[data-qa="resume-personal-address-text"]',
  ]) || (isProfilePage ? profileValueAfterLabel(root, ["Где ищете работу", "Где живёте"]) : "");
  const sections = resumeSectionsFromDocument(root);
  const skillSection = sections.find((section) => section.key === "skills");
  const skills = isProfilePage
    ? cleanMultiline(skillSection?.text).split("\n").slice(1).filter((value) => value.length < 100)
    : pageTexts(root, [
        '[data-qa="skills-element"]',
        '[data-qa="resume-block-skills-content"] [data-qa="bloko-tag__text"]',
      ]).filter((value) => value.length < 100);
  const experienceText = sections.find((section) => section.key === "experience")?.text || "";
  const experienceHeading = pageText(root, [
    '[data-qa="resume-block-experience"] h2',
    '[data-qa="resume-block-experience"] h3',
  ]) || experienceText.match(/Опыт работы[^\n]{0,80}/i)?.[0] || "";
  const header = [
    name ? `Имя: ${name}` : "",
    targetRole ? `Целевая роль: ${targetRole}` : "",
    locationValue ? `Регион: ${locationValue}` : "",
  ].filter(Boolean).join("\n");
  const resumeText = [
    header,
    ...sections.map((section) => `## ${section.title}\n${section.text}`),
  ].filter(Boolean).join("\n\n").slice(0, 60000);
  return {
    profile: {
      name,
      target_roles: targetRole,
      locations: locationValue,
      skills: skills.join(", "),
      experience_years: parseExperienceYears(experienceHeading),
      work_history: experienceText.slice(0, 30000),
      hh_resume_title: targetRole,
      resume_text: resumeText,
    },
    sections: sections.map((section) => section.title),
    characters: resumeText.length,
  };
}

function profileFromPage() {
  return profileFromDocument(document);
}

function makeProfileImportButton(loadProfile, label = "Импортировать профиль в Career Bot") {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "career-bot-hh-add career-bot-profile-import";
  button.textContent = label;
  button.addEventListener("click", async (event) => {
    event.preventDefault();
    event.stopPropagation();
    button.disabled = true;
    button.textContent = "Читаю резюме...";
    let imported;
    try {
      imported = await loadProfile();
    } catch (error) {
      button.disabled = false;
      button.textContent = "Повторить импорт";
      button.title = error.message;
      button.classList.add("career-bot-hh-error");
      return;
    }
    button.textContent = "Импортирую...";
    chrome.runtime.sendMessage({ type: "career-bot-import-profile", ...imported }, (response) => {
      if (chrome.runtime.lastError || !response?.ok) {
        button.disabled = false;
        button.textContent = "Повторить импорт";
        button.title = response?.error || chrome.runtime.lastError?.message || "Career Bot не ответил";
        button.classList.add("career-bot-hh-error");
        return;
      }
      button.textContent = `Импортировано · ${response.sectionsCount} разделов`;
      button.title = response.summary || "Профиль сохранен в локальном Career Bot";
      button.classList.add("career-bot-hh-done");
    });
  });
  return button;
}

function enhanceResumePage() {
  if (/^\/applicant\/profile\/me\/?$/i.test(location.pathname)) return;
  if (!document.querySelector('[data-qa="resume-block-title-position"]') || document.querySelector(".career-bot-profile-import")) return;
  const title = document.querySelector('[data-qa="resume-block-title-position"], h1');
  const button = makeProfileImportButton(async () => profileFromPage());
  (title.parentElement || title).append(button);
}

async function profileFromUrl(url) {
  const response = await fetchWithTimeout(url, { credentials: "include", headers: { Accept: "text/html" } }, 10000);
  if (!response.ok) throw new Error(`hh.ru вернул ${response.status}`);
  const root = new DOMParser().parseFromString(await response.text(), "text/html");
  const imported = profileFromDocument(root);
  if (!imported.profile.resume_text) throw new Error("Не удалось прочитать разделы резюме. Откройте его полностью и повторите импорт.");
  return imported;
}

function enhanceResumeList() {
  if (!/\/applicant\/resumes?/i.test(location.pathname)) return;
  document.querySelectorAll('a[href*="/resume/"]').forEach((link) => {
    const url = new URL(link.href, location.href);
    const card = link.closest('[data-qa*="resume"], article, li') || link.parentElement;
    if (!card || card.querySelector(".career-bot-profile-import")) return;
    const button = makeProfileImportButton(() => profileFromUrl(url.href), "В Career Bot");
    button.dataset.resumeUrl = url.href;
    card.append(button);
  });
}

function isApplicantProfileWithResume() {
  if (/^\/applicant\/profile\/me\/?$/i.test(location.pathname)) return true;
  const text = cleanText(document.body?.innerText).toLowerCase();
  return text.includes("мои резюме") && text.includes("опыт работы") && text.includes("образование");
}

function enhanceApplicantProfile() {
  if (!isApplicantProfileWithResume() || document.querySelector(".career-bot-profile-floating")) return;
  const button = makeProfileImportButton(async () => profileFromPage(), "Импортировать резюме в Career Bot");
  button.classList.add("career-bot-profile-floating");
  document.body.append(button);
}

function textOf(root, selector) {
  return (root.querySelector(selector)?.textContent || "").replace(/\s+/g, " ").trim();
}

function vacancyFromCard(card) {
  const titleLink = card.querySelector(TITLE_SELECTOR);
  return {
    title: (titleLink?.textContent || "Вакансия hh.ru").trim(),
    company: textOf(card, '[data-qa="vacancy-serp__vacancy-employer"]'),
    location: textOf(card, '[data-qa="vacancy-serp__vacancy-address"]'),
    salary: textOf(card, '[data-qa="vacancy-serp__vacancy-compensation"]'),
    url: titleLink?.href || location.href,
    source: "hh-browser-safe",
    description: (card.innerText || "").replace(/\s+/g, " ").trim().slice(0, 8000),
  };
}

function cleanText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function isExtensionContextInvalid(error) {
  return /extension context invalidated|context invalidated/i.test(String(error?.message || error || ""));
}

function reloadAfterExtensionUpdate(statusElement) {
  if (statusElement) statusElement.textContent = "Расширение обновилось · перезагружаю страницу…";
  window.setTimeout(() => location.reload(), 500);
}

function pageText(root, selectors) {
  for (const selector of selectors) {
    const value = cleanText(root.querySelector(selector)?.textContent);
    if (value) return value;
  }
  return "";
}

function pageTexts(root, selectors) {
  const values = [];
  selectors.forEach((selector) => {
    root.querySelectorAll(selector).forEach((element) => {
      const value = cleanText(element.textContent);
      if (value && !values.includes(value)) values.push(value);
    });
  });
  return values;
}

async function fetchWithTimeout(url, options = {}, timeoutMs = 6000) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    window.clearTimeout(timer);
  }
}

function vacancyFromDocument(root, url, fallback = {}) {
  const description = pageText(root, [
    '[data-qa="vacancy-description"]',
    '[data-qa="vacancy-description-text"]',
    ".vacancy-description",
  ]);
  const skills = pageTexts(root, [
    '[data-qa="skills-element"]',
    '[data-qa="bloko-tag__text"]',
  ]).filter((value) => value.length <= 100);
  const experience = pageText(root, [
    '[data-qa="vacancy-experience"]',
    '[data-qa="vacancy-view-experience"]',
  ]);
  const employment = pageText(root, ['[data-qa="vacancy-view-employment-mode"]']);
  const workFormat = pageText(root, [
    '[data-qa="vacancy-view-work-format"]',
    '[data-qa="vacancy-view-schedule"]',
  ]);
  const detailParts = [
    description,
    skills.length ? `Ключевые навыки: ${skills.join(", ")}.` : "",
    experience ? `Опыт: ${experience}.` : "",
    employment ? `Занятость: ${employment}.` : "",
    workFormat ? `Формат работы: ${workFormat}.` : "",
  ].filter(Boolean);

  return {
    ...fallback,
    title: pageText(root, ['[data-qa="vacancy-title"]', "h1"]) || fallback.title,
    company: pageText(root, ['[data-qa="vacancy-company-name"]']) || fallback.company,
    location: pageText(root, [
      '[data-qa="vacancy-view-location"]',
      '[data-qa="vacancy-view-raw-address"]',
    ]) || fallback.location,
    salary: pageText(root, ['[data-qa="vacancy-salary"]']) || fallback.salary,
    url,
    source: "hh-browser-safe",
    description: detailParts.join("\n\n").slice(0, 20000) || fallback.description,
    details_loaded: description.length > 200,
  };
}

async function loadVacancyDetails(vacancy) {
  const vacancyUrl = new URL(vacancy.url, location.href);
  if (!/^(?:[a-z0-9-]+\.)?hh\.ru$/i.test(vacancyUrl.hostname)) return vacancy;

  try {
    const response = await fetchWithTimeout(vacancyUrl.href, {
      credentials: "include",
      headers: { Accept: "text/html" },
    }, 6000);
    if ([403, 429].includes(response.status)) {
      return {
        ...vacancy,
        collection_limited: true,
        collection_error: `hh.ru временно не отдает детали карточки (HTTP ${response.status})`,
      };
    }
    if (!response.ok) throw new Error(`hh.ru returned ${response.status}`);
    const html = await response.text();
    const root = new DOMParser().parseFromString(html, "text/html");
    const hasVacancyContent = Boolean(root.querySelector(
      '[data-qa="vacancy-description"], [data-qa="vacancy-title"], .vacancy-description',
    ));
    const visibleText = cleanText(root.body?.textContent).slice(0, 2500);
    const explicitCaptchaControl = root.querySelector(
      'form[action*="captcha"], input[name*="captcha"], iframe[src*="captcha"], [data-qa="captcha-page"]',
    );
    const captchaUrl = /(?:captcha|account\/verification|security-check)/i.test(response.url || "");
    const captchaText = /(?:пройдите проверку|подтвердите, что вы не робот|проверка безопасности)/i.test(visibleText);
    if (!hasVacancyContent && captchaText && (explicitCaptchaControl || captchaUrl)) {
      return {
        ...vacancy,
        collection_blocked: true,
        collection_error: "hh.ru вернул страницу проверки для фонового чтения карточки",
        collection_blocked_url: vacancyUrl.href,
      };
    }
    const finalUrl = response.url || vacancyUrl.href;
    return vacancyFromDocument(root, finalUrl, vacancy);
  } catch (_error) {
    return vacancy;
  }
}

function hasVacancyTitle(element) {
  return Boolean(element?.querySelector?.(TITLE_SELECTOR));
}

function closestVacancyCard(element) {
  const knownCard = element.closest(CARD_SELECTORS.join(", "));
  if (knownCard) return knownCard;

  // hh.ru uses a few unlabelled card variants (including promoted vacancies).
  // Walk upwards from the response control until we find a compact block with
  // one vacancy title, stopping before a shared search-results container.
  let candidate = element.parentElement;
  while (candidate && candidate !== document.body) {
    if (hasVacancyTitle(candidate)) {
      const vacancyLinks = candidate.querySelectorAll('a[href*="/vacancy/"]');
      if (vacancyLinks.length <= 4) return candidate;
    }
    candidate = candidate.parentElement;
  }
  return null;
}

function responseControls() {
  const controls = new Set(document.querySelectorAll(RESPONSE_SELECTOR));
  document.querySelectorAll("a, button").forEach((element) => {
    const text = (element.textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
    if (text === "откликнуться") controls.add(element);
  });
  return controls;
}

function attachButton(card, response) {
  if (!card || card.querySelector(`.${BUTTON_CLASS}`)) return;
  const action = response?.parentElement || card.querySelector("footer") || card;
  action.append(makeButton(() => vacancyFromCard(card)));
}

function vacancyFromPage() {
  return vacancyFromDocument(document, location.href, {
    title: textOf(document, '[data-qa="vacancy-title"]') || document.title,
    company: textOf(document, '[data-qa="vacancy-company-name"]'),
    location:
      textOf(document, '[data-qa="vacancy-view-location"]') ||
      textOf(document, '[data-qa="vacancy-view-raw-address"]'),
    salary: textOf(document, '[data-qa="vacancy-salary"]'),
    url: location.href,
    source: "hh-browser-safe",
    description: textOf(document, '[data-qa="vacancy-description"]') || document.title,
  });
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "career-bot-extract-rendered-vacancy") return false;
  try {
    sendResponse({ ok: true, vacancy: vacancyFromPage() });
  } catch (error) {
    sendResponse({ ok: false, error: error.message });
  }
  return false;
});

function makeButton(getVacancy) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = BUTTON_CLASS;
  button.textContent = "В Career Bot";
  button.title = "Добавить вакансию в локальный Career Bot";
  button.addEventListener("click", async (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (button.disabled) return;
    button.disabled = true;
    button.classList.remove("career-bot-hh-error", "career-bot-hh-done", "career-bot-hh-duplicate");
    button.textContent = "Читаю вакансию...";
    const vacancy = await loadVacancyDetails(await Promise.resolve(getVacancy()));
    button.textContent = "Добавляю...";
    const responseTimer = window.setTimeout(() => {
      button.disabled = false;
      button.textContent = "Повторить";
      button.title = "Расширение не ответило. Обновите его на странице edge://extensions и повторите.";
      button.classList.add("career-bot-hh-error");
    }, 45000);
    chrome.runtime.sendMessage(
      { type: "career-bot-add-vacancy", vacancy },
      (response) => {
        window.clearTimeout(responseTimer);
        if (chrome.runtime.lastError || !response?.ok) {
          button.disabled = false;
          button.textContent = "Повторить";
          button.title = response?.error || chrome.runtime.lastError?.message || "Career Bot не ответил";
          button.classList.add("career-bot-hh-error");
          return;
        }
        button.classList.remove("career-bot-hh-error");
        button.title = response.detailsLoaded
          ? "Полное описание вакансии сохранено в Career Bot"
          : "Вакансия сохранена, но hh.ru не предоставил полное описание";
        button.textContent = response.updated
          ? `Обновлено · ${response.score}/100`
          : response.duplicate ? "Уже добавлена" : response.detailsLoaded
            ? `Добавлено · ${response.score}/100`
            : "Добавлено без деталей";
        button.classList.add(response.duplicate && !response.updated ? "career-bot-hh-duplicate" : "career-bot-hh-done");
      },
    );
  });
  return button;
}

function enhanceCards() {
  const cards = vacancyCards();
  cards.forEach((card) => {
    if (card.querySelector(`.${BUTTON_CLASS}`)) return;
    attachButton(card, card.querySelector(RESPONSE_SELECTOR));
  });
}

function vacancyCards() {
  const cards = new Set();
  CARD_SELECTORS.forEach((selector) => document.querySelectorAll(selector).forEach((card) => cards.add(card)));
  document.querySelectorAll(TITLE_SELECTOR).forEach((title) => {
    const card = title.closest(CARD_SELECTORS.join(", ")) || closestVacancyCard(title);
    if (card) cards.add(card);
  });

  responseControls().forEach((response) => {
    const card = closestVacancyCard(response);
    if (card) {
      cards.add(card);
      attachButton(card, response);
    }
  });
  return cards;
}

function sendVacancyToCareerBotOnce(vacancy) {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => reject(new Error("Career Bot не ответил за 45 секунд")), 45000);
    try {
      chrome.runtime.sendMessage({ type: "career-bot-add-vacancy", vacancy }, (response) => {
        window.clearTimeout(timer);
        if (chrome.runtime.lastError || !response?.ok) {
          reject(new Error(response?.error || chrome.runtime.lastError?.message || "Career Bot не ответил"));
          return;
        }
        resolve(response);
      });
    } catch (error) {
      window.clearTimeout(timer);
      reject(error);
    }
  });
}

async function sendVacancyToCareerBot(vacancy) {
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      return await sendVacancyToCareerBotOnce(vacancy);
    } catch (error) {
      if (!/database is locked/i.test(error.message) || attempt === 3) throw error;
      await new Promise((resolve) => window.setTimeout(resolve, attempt * 1200));
    }
  }
  throw new Error("Не удалось сохранить вакансию");
}

let bulkCollectionRunning = false;
let bulkCollectionStop = false;
let browserAssistAutoStarted = false;

function browserAssistScenarioId() {
  const queryId = new URLSearchParams(location.search).get("career_bot_assist");
  const hashId = new URLSearchParams(location.hash.replace(/^#/, "")).get("careerBotAssist");
  const value = queryId || hashId;
  return /^\d+$/.test(value || "") ? Number(value) : null;
}

function browserAssistResultLimit() {
  const value = Number(new URLSearchParams(location.search).get("career_bot_limit") || 50);
  return Number.isFinite(value) ? Math.max(1, Math.min(200, Math.trunc(value))) : 50;
}

function rememberVisibleVacancies(collected) {
  vacancyCards().forEach((card) => {
    const vacancy = vacancyFromCard(card);
    const key = String(vacancy.url).match(/\/vacancy\/(\d+)/)?.[1] || vacancy.url;
    if (key && !collected.has(key)) collected.set(key, vacancy);
  });
}

async function collectLazyLoadedVacancies(status, targetCount) {
  const collected = new Map();
  let stableRounds = 0;
  let previousCount = -1;
  const originalTop = window.scrollY;

  for (let round = 0; round < 30 && collected.size < targetCount; round += 1) {
    if (bulkCollectionStop) break;
    rememberVisibleVacancies(collected);
    status.textContent = `Загружаю выдачу hh.ru · найдено ${collected.size} из ${targetCount}`;
    stableRounds = collected.size === previousCount ? stableRounds + 1 : 0;
    previousCount = collected.size;

    const nearBottom = window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 300;
    if (nearBottom && stableRounds >= 3) break;
    window.scrollBy({ top: Math.max(window.innerHeight * 0.85, 700), behavior: "auto" });
    await new Promise((resolve) => window.setTimeout(resolve, 650));
  }

  rememberVisibleVacancies(collected);
  window.scrollTo({ top: originalTop, behavior: "auto" });
  return Array.from(collected.values()).slice(0, targetCount);
}

function pageRequiresManualCheck() {
  if (vacancyCards().size > 0) return false;
  const text = String(document.body?.innerText || "").slice(0, 5000);
  const captchaText = /(?:пройдите проверку|подтвердите, что вы не робот|проверка безопасности)/i.test(text);
  const captchaUrl = /(?:captcha|account\/verification|security-check)/i.test(location.href);
  const visibleControl = Array.from(document.querySelectorAll(
    'form[action*="captcha"], input[name*="captcha"], iframe[src*="captcha"], [data-qa="captcha-page"]',
  )).some((element) => {
    const style = window.getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return !element.hidden && style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
  });
  return captchaText && (captchaUrl || visibleControl);
}

function addManualCheckAction(panel, url) {
  let action = panel.querySelector(".career-bot-manual-check");
  if (!action) {
    action = document.createElement("button");
    action.type = "button";
    action.className = "career-bot-manual-check";
    action.textContent = "Открыть проблемную вакансию";
    panel.append(action);
  }
  action.onclick = () => window.open(url, "_blank", "noopener,noreferrer");
}

function getBrowserPlan() {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ type: "career-bot-get-browser-plan" }, (response) => {
      if (chrome.runtime.lastError || !response?.ok) {
        reject(new Error(response?.error || chrome.runtime.lastError?.message || "Career Bot не ответил"));
        return;
      }
      resolve(response.items || []);
    });
  });
}

async function addNextScenarioAction(panel, status, scenarioId, resultText) {
  if (!scenarioId) return;
  try {
    const plan = await getBrowserPlan();
    const currentIndex = plan.findIndex((item) => Number(item.id) === Number(scenarioId));
    const next = currentIndex >= 0 ? plan[currentIndex + 1] : null;
    let nextButton = panel.querySelector(".career-bot-next-scenario");
    if (!nextButton) {
      nextButton = document.createElement("button");
      nextButton.type = "button";
      nextButton.className = "career-bot-next-scenario";
      panel.append(nextButton);
    }
    if (!next) {
      status.textContent = `${resultText} · все сценарии обработаны`;
      nextButton.remove();
      return;
    }
    nextButton.textContent = "Остаться здесь";
    nextButton.title = "Отменить автоматический переход к следующему сценарию";
    let secondsLeft = 3;
    status.textContent = `${resultText} · следующий сценарий через ${secondsLeft} сек.`;
    const countdown = window.setInterval(() => {
      secondsLeft -= 1;
      if (secondsLeft > 0) {
        status.textContent = `${resultText} · следующий сценарий через ${secondsLeft} сек.`;
      }
    }, 1000);
    const navigation = window.setTimeout(() => {
      window.clearInterval(countdown);
      location.assign(next.url);
    }, 3000);
    nextButton.onclick = () => {
      window.clearInterval(countdown);
      window.clearTimeout(navigation);
      status.textContent = `${resultText} · автоматический переход отменен`;
      nextButton.remove();
    };
  } catch (error) {
    status.textContent = `${resultText} · следующий сценарий не загружен: ${error.message}`;
  }
}

function enhanceBulkCollector() {
  if (!/\/search\/vacancy/i.test(location.pathname) || document.querySelector(".career-bot-bulk-collector")) return;
  const assistScenarioId = browserAssistScenarioId();
  const panel = document.createElement("div");
  panel.className = "career-bot-bulk-collector";
  const status = document.createElement("span");
  status.textContent = assistScenarioId
    ? "Browser Assist готовит сбор этой выдачи"
    : "Собрать видимые вакансии с полными описаниями";
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "Собрать страницу";
  button.addEventListener("click", async () => {
    if (bulkCollectionRunning) {
      bulkCollectionStop = true;
      button.disabled = true;
      button.textContent = "Останавливаю...";
      return;
    }
    panel.classList.remove("career-bot-bulk-error");
    panel.querySelector(".career-bot-manual-check")?.remove();
    bulkCollectionRunning = true;
    bulkCollectionStop = false;
    button.textContent = "Остановить";
    const targetCount = assistScenarioId ? browserAssistResultLimit() : 50;
    const unique = await collectLazyLoadedVacancies(status, targetCount);
    if (!unique.length) {
      status.textContent = "На странице не найдено карточек вакансий";
      bulkCollectionRunning = false;
      button.textContent = "Собрать снова";
      return;
    }
    let added = 0;
    let duplicates = 0;
    let incomplete = 0;
    try {
      for (let index = 0; index < unique.length; index += 1) {
        if (bulkCollectionStop) break;
        status.textContent = `Читаю ${index + 1} из ${unique.length} · добавлено ${added}`;
        // Batch collection uses the public vacancy API in the service worker.
        // Fetching dozens of authenticated HTML pages looks suspicious to hh.ru
        // and causes invisible verification pages on otherwise normal vacancies.
        const response = await sendVacancyToCareerBot(unique[index]);
        if (response.duplicate) duplicates += 1;
        else added += 1;
        if (!response.detailsLoaded) incomplete += 1;
        await new Promise((resolve) => window.setTimeout(resolve, 900 + Math.floor(Math.random() * 500)));
      }
      if (!panel.classList.contains("career-bot-bulk-error")) {
        const resultText = bulkCollectionStop
          ? `Остановлено · новых ${added} · дублей ${duplicates}`
          : `Готово · новых ${added} · дублей ${duplicates}${incomplete ? ` · без деталей ${incomplete}` : ""}`;
        status.textContent = resultText;
        if (!bulkCollectionStop) await addNextScenarioAction(panel, status, assistScenarioId, resultText);
      }
    } catch (error) {
      if (isExtensionContextInvalid(error)) {
        reloadAfterExtensionUpdate(status);
        return;
      }
      panel.classList.add("career-bot-bulk-error");
      status.textContent = `Сбор остановлен: ${error.message}`;
    } finally {
      bulkCollectionRunning = false;
      bulkCollectionStop = false;
      button.disabled = false;
      button.textContent = "Собрать снова";
    }
  });
  panel.append(status, button);
  document.body.append(panel);

  if (assistScenarioId && !browserAssistAutoStarted) {
    browserAssistAutoStarted = true;
    let attempts = 0;
    const startWhenReady = () => {
      attempts += 1;
      if (pageRequiresManualCheck()) {
        panel.classList.add("career-bot-bulk-error");
        status.textContent = "hh.ru просит ручную проверку. Пройдите ее и обновите страницу.";
        button.textContent = "Повторить после проверки";
        return;
      }
      if (vacancyCards().size > 0) {
        status.textContent = "Browser Assist начинает сбор видимых вакансий";
        button.click();
        return;
      }
      if (attempts >= 40) {
        status.textContent = "Карточки не появились. Обновите страницу или измените параметры поиска.";
        return;
      }
      window.setTimeout(startWhenReady, 500);
    };
    window.setTimeout(startWhenReady, 600);
  }
}

function showLoadedMarker() {
  if (document.querySelector(".career-bot-hh-loaded")) return;
  const marker = document.createElement("div");
  marker.className = "career-bot-hh-loaded";
  marker.textContent = "Career Bot включен";
  marker.title = "Расширение Career Bot работает на этой странице";
  document.body.append(marker);
  window.setTimeout(() => marker.classList.add("career-bot-hh-loaded-hide"), 4000);
}

function showApplyMarker(message, error = false) {
  let marker = document.querySelector(".career-bot-apply-marker");
  if (!marker) {
    marker = document.createElement("div");
    marker.className = "career-bot-apply-marker";
    document.body.append(marker);
  }
  marker.classList.toggle("career-bot-apply-error", error);
  marker.textContent = message;
}

function setNativeValue(element, value) {
  if (element instanceof HTMLTextAreaElement || element instanceof HTMLInputElement) {
    const prototype = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;
    if (setter) setter.call(element, value);
    else element.value = value;
  } else {
    element.textContent = value;
  }
  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.dispatchEvent(new Event("change", { bubbles: true }));
}

function fillApprovedLetter(letter, successMessage = "Career Bot вставил письмо. Выберите резюме, проверьте данные и отправьте отклик вручную.") {
  const selectors = [
    '[data-qa="vacancy-response-letter-input"]',
    '[data-qa="vacancy-response-popup-form-letter-input"]',
    'textarea[name="letter"]',
    'textarea[name*="letter"]',
    'textarea[placeholder*="сопровод"]',
    'textarea[aria-label*="сопровод"]',
    '[contenteditable="true"][aria-label*="сопровод"]',
  ];
  let field = document.querySelector(selectors.join(", "));
  if (!field) {
    const coverScope = Array.from(document.querySelectorAll('[role="dialog"], form, section, aside')).find((element) =>
      cleanText(element.textContent).toLowerCase().includes("сопроводительн"),
    );
    field = coverScope?.querySelector('textarea, [contenteditable="true"][role="textbox"]');
  }
  field = field || chatMessageField();
  if (!field) return false;
  setNativeValue(field, letter);
  field.focus();
  showApplyMarker(successMessage);
  return true;
}

function chatMessageField() {
  return document.querySelector([
    '[data-qa*="chat"] textarea',
    '[data-qa*="chat"] [contenteditable="true"]',
    '[data-qa*="message"] textarea',
    '[data-qa*="message"] [contenteditable="true"]',
    'textarea[placeholder*="сообщени"]',
    'textarea[aria-label*="сообщени"]',
    '[contenteditable="true"][placeholder*="сообщени"]',
    '[contenteditable="true"][aria-label*="сообщени"]',
  ].join(", "));
}

function openEmployerChat() {
  const control = Array.from(document.querySelectorAll("button, a, [role='button']")).find((element) => {
    if (!visible(element)) return false;
    const text = cleanText(element.textContent).toLowerCase();
    return text.includes("открыть чат") || text.includes("написать сообщение") || text.includes("чат с работодателем");
  });
  if (!control) return false;
  control.click();
  return true;
}

function clickAddCoverLetter() {
  const candidates = Array.from(document.querySelectorAll("button, a, [role='button']"));
  const control = candidates.find((element) => {
    const text = cleanText(element.textContent).toLowerCase();
    return text.includes("добавить сопроводительное") || text.includes("сопроводительное письмо");
  });
  if (control) {
    control.click();
    return true;
  }
  return openEmployerChat();
}

function selectHhResume(title) {
  const wanted = cleanText(title).toLowerCase();
  if (!wanted) return false;
  const candidates = Array.from(document.querySelectorAll(
    '[data-qa*="resume"], label, button, [role="radio"], [role="option"]',
  ));
  const option = candidates.find((element) => {
    const text = cleanText(element.textContent).toLowerCase();
    return text && (text === wanted || text.includes(wanted)) && !text.includes("создать резюме");
  });
  if (!option) return false;
  const control = option.matches('button, [role="radio"], [role="option"]')
    ? option
    : option.querySelector('input, button, [role="radio"]') || option;
  control.click();
  return true;
}

function pause(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function visible(element) {
  return Boolean(element && (element.offsetWidth || element.offsetHeight || element.getClientRects().length));
}

function coverLetterField() {
  const direct = document.querySelector([
    '[data-qa="vacancy-response-letter-input"]',
    '[data-qa="vacancy-response-popup-form-letter-input"]',
    'textarea[name="letter"]',
    'textarea[name*="letter"]',
    'textarea[placeholder*="сопровод"]',
    'textarea[aria-label*="сопровод"]',
    '[contenteditable="true"][aria-label*="сопровод"]',
  ].join(", "));
  if (direct) return direct;
  // В актуальной форме hh.ru текстовое поле может не иметь отдельного data-qa.
  // Надёжнее ограничить поиск модальным окном с подписью о сопроводительном письме.
  const modal = Array.from(document.querySelectorAll('[role="dialog"], form, section, aside')).find((element) =>
    cleanText(element.textContent).toLowerCase().includes("сопроводительн"),
  );
  return modal?.querySelector('textarea, [contenteditable="true"][role="textbox"], [contenteditable="true"]') || null;
}

function responseTextField() {
  return coverLetterField() || chatMessageField();
}

function applyScope(field) {
  return field?.closest('[role="dialog"], form, section, aside') || field?.parentElement || document.body;
}

function startApplicationButton() {
  const direct = document.querySelector('[data-qa="vacancy-response-link-top"], [data-qa="vacancy-response-link-bottom"]');
  if (visible(direct)) return direct;
  return Array.from(document.querySelectorAll('button, a, [role="button"]')).find((element) => {
    if (!visible(element) || element.closest('[role="dialog"]')) return false;
    const text = cleanText(element.textContent).toLowerCase();
    return text === "откликнуться" || text === "отправить отклик";
  });
}

function hasExtraStep(scope, field) {
  const text = cleanText(scope?.innerText || "").toLowerCase();
  const questionWords = /(?:ответьте\s+на\s+вопрос|вопрос(?:ы)?\s+работодател|мини-?интервью|видеоинтервью|пройдите\s+тест|тестовое\s+задани|заполните\s+анкет)/i;
  if (questionWords.test(text)) return true;
  const extraInputs = Array.from(scope.querySelectorAll('input:not([type="hidden"]), select, textarea, [contenteditable="true"]'))
    .filter((element) => visible(element) && !element.disabled)
    .filter((element) => element !== field)
    .filter((element) => !element.matches('input[type="submit"], input[type="button"]'));
  return extraInputs.length > 0;
}

function finalApplyButton(scope) {
  const explicit = scope.querySelector('[data-qa*="vacancy-response"][data-qa*="submit"], button[type="submit"]');
  if (visible(explicit)) return explicit;
  return Array.from(scope.querySelectorAll('button, [role="button"]')).find((element) => {
    if (!visible(element) || element.disabled) return false;
    const text = cleanText(element.textContent).toLowerCase();
    return text === "откликнуться" || text === "отправить отклик" || text === "отправить";
  });
}

function applySucceeded() {
  const text = cleanText(document.body?.innerText || "").toLowerCase();
  return /(?:отклик отправлен|вы откликнулись|ваш отклик отправлен|отклик успешно отправлен)/i.test(text);
}

function messageSent() {
  const text = cleanText(document.body?.innerText || "").toLowerCase();
  return /(?:сообщение отправлено|сообщение доставлено|вы отправили сообщение)/i.test(text);
}

function reportBatchResult(sessionToken, outcome, reason) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({
      type: "career-bot-report-batch-apply-result",
      sessionToken,
      outcome,
      reason,
    }, (response) => resolve(response || { ok: false, error: chrome.runtime.lastError?.message || "Расширение не получило ответ" }));
  });
}

function continueBatch(batchToken) {
  chrome.runtime.sendMessage({ type: "career-bot-get-batch-apply-next", batchToken }, (response) => {
    if (chrome.runtime.lastError || !response?.ok) {
      showApplyMarker(response?.error || "Не удалось продолжить пакет откликов. Вернитесь в Career Bot и проверьте прогресс.", true);
      return;
    }
    if (response.done) {
      showApplyMarker(`Пакет откликов завершен: обработано ${response.total}. Вернитесь в Career Bot за итогами.`);
      return;
    }
    window.location.replace(response.item.url);
  });
}

async function runSimpleBatchApply(sessionToken, batchToken, letter) {
  throw new Error("Автоотправка отключена до завершения диагностики.");
  const checkActive = () => new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ type: "career-bot-get-apply-session", token: sessionToken }, (response) => {
      const error = chrome.runtime.lastError;
      if (error || !response?.ok) reject(new Error(response?.error || error?.message || "Пакет остановлен."));
      else resolve();
    });
  });
  await checkActive();
  let field = responseTextField();
  if (!field) {
    const opener = startApplicationButton();
    if (!opener) {
      const result = await reportBatchResult(sessionToken, "skipped", "Не найдена стандартная кнопка «Откликнуться».");
      if (result.ok) continueBatch(batchToken);
      return;
    }
    opener.click();
    for (let attempt = 0; attempt < 20 && !field; attempt += 1) {
      await pause(350);
      field = responseTextField();
    }
  }
  if (!field) {
    const result = await reportBatchResult(sessionToken, "needs_manual", "После открытия отклика не найдено поле сопроводительного письма.");
    if (result.ok) continueBatch(batchToken);
    return;
  }
  const scope = applyScope(field);
  if (hasExtraStep(scope, field)) {
    const result = await reportBatchResult(sessionToken, "needs_manual", "Форма содержит вопрос, анкету или дополнительное поле.");
    if (result.ok) continueBatch(batchToken);
    return;
  }
  fillApprovedLetter(letter, "Career Bot вставил одобренное письмо и проверяет простую форму отклика...");
  const submit = finalApplyButton(scope);
  if (!submit) {
    const result = await reportBatchResult(sessionToken, "needs_manual", "Не найдена стандартная финальная кнопка отправки.");
    if (result.ok) continueBatch(batchToken);
    return;
  }
  await checkActive();
  submit.click();
  for (let attempt = 0; attempt < 28; attempt += 1) {
    await pause(350);
    if (applySucceeded() || messageSent()) {
      const result = await reportBatchResult(sessionToken, "sent", "");
      if (result.ok) continueBatch(batchToken);
      return;
    }
  }
  const result = await reportBatchResult(sessionToken, "needs_manual", "После отправки не удалось надежно подтвердить результат на странице.");
  if (result.ok) continueBatch(batchToken);
}

function prepareBatchApply() {
  return; // Disabled until diagnostic verification on the real hh.ru form.
  const params = new URLSearchParams(location.hash.slice(1));
  const batchToken = params.get("careerBotBatch");
  if (!batchToken || params.get("careerBotApply") || window.__careerBotBatchStarted) return;
  window.__careerBotBatchStarted = true;
  showApplyMarker("Career Bot запускает пакет простых откликов...");
  continueBatch(batchToken);
}

function prepareSafeApply() {
  const params = new URLSearchParams(location.hash.slice(1));
  const token = params.get("careerBotApply");
  const batchToken = params.get("careerBotBatch");
  if (!token || window.__careerBotApplyStarted) return;
  if (batchToken) {
    showApplyMarker("Автоотправка отключена. Используйте диагностику в Career Bot.", true);
    return;
  }
  window.__careerBotApplyStarted = true;
  showApplyMarker("Career Bot готовит отклик...");
  chrome.runtime.sendMessage({ type: "career-bot-get-apply-session", token }, (response) => {
    if (chrome.runtime.lastError || !response?.ok) {
      showApplyMarker(response?.error || "Не удалось получить письмо из локального Career Bot.", true);
      return;
    }
    if (response.auto_submit && batchToken) {
      runSimpleBatchApply(token, batchToken, response.letter).catch((error) => {
        showApplyMarker(error.message || "Ошибка пакетного отклика.", true);
      });
      return;
    }
    selectHhResume(response.hh_resume_title);
    if (fillApprovedLetter(response.letter)) return;
    clickAddCoverLetter();
    showApplyMarker("Письмо готово. Нажмите «Откликнуться» на hh.ru — Career Bot добавит сопроводительное в открывшийся чат.");
    let attempts = 0;
    const timer = window.setInterval(() => {
      attempts += 1;
      const filled = fillApprovedLetter(response.letter);
      if (!filled) clickAddCoverLetter();
      if (filled || attempts >= 150) {
        window.clearInterval(timer);
        if (attempts >= 150) {
          showApplyMarker("Откройте «Добавить сопроводительное». Career Bot вставит письмо, когда поле появится.", true);
        }
      }
    }, 400);
  });
}

function enhanceVacancyPage() {
  const title = document.querySelector('[data-qa="vacancy-title"]');
  if (!title || document.querySelector(`.${BUTTON_CLASS}[data-page-button="true"]`)) return;
  const responseButton = document.querySelector('[data-qa="vacancy-response-link-top"]');
  const host = responseButton?.parentElement || title.parentElement;
  const button = makeButton(vacancyFromPage);
  button.dataset.pageButton = "true";
  host.append(button);
}

function enhance() {
  showLoadedMarker();
  enhanceResumePage();
  enhanceResumeList();
  enhanceApplicantProfile();
  enhanceCards();
  enhanceBulkCollector();
  enhanceVacancyPage();
  prepareBatchApply();
  prepareSafeApply();
}

let scheduled = false;
const observer = new MutationObserver(() => {
  if (scheduled) return;
  scheduled = true;
  window.requestAnimationFrame(() => {
    scheduled = false;
    enhance();
  });
});

enhance();
chrome.runtime.sendMessage({ type: "career-bot-sync-areas" }, () => void chrome.runtime.lastError);
observer.observe(document.documentElement, { childList: true, subtree: true });
