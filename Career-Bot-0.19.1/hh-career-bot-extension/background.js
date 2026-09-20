function fetchWithTimeout(url, options = {}, timeoutMs = 6000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return fetch(url, { ...options, signal: controller.signal })
    .finally(() => clearTimeout(timer));
}

function waitForTabComplete(tabId, timeoutMs = 20000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      reject(new Error("vacancy tab timed out"));
    }, timeoutMs);
    const listener = (updatedTabId, changeInfo) => {
      if (updatedTabId !== tabId || changeInfo.status !== "complete") return;
      clearTimeout(timer);
      chrome.tabs.onUpdated.removeListener(listener);
      setTimeout(resolve, 1200);
    };
    chrome.tabs.onUpdated.addListener(listener);
  });
}

function extractVacancyFromRenderedTab(tabId) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, { type: "career-bot-extract-rendered-vacancy" }, (response) => {
      if (chrome.runtime.lastError || !response?.ok) {
        reject(new Error(chrome.runtime.lastError?.message || response?.error || "vacancy extraction failed"));
        return;
      }
      resolve(response.vacancy);
    });
  });
}

async function loadVacancyThroughRenderedTab(vacancy) {
  let tab;
  try {
    tab = await chrome.tabs.create({ url: vacancy.url, active: false });
    await waitForTabComplete(tab.id);
    const rendered = await extractVacancyFromRenderedTab(tab.id);
    return String(rendered?.description || "").length > String(vacancy.description || "").length + 100
      ? rendered
      : vacancy;
  } catch (_error) {
    return vacancy;
  } finally {
    if (tab?.id) chrome.tabs.remove(tab.id).catch(() => {});
  }
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "career-bot-diagnostic-report") {
    fetchWithTimeout(`http://127.0.0.1:8765/api/apply/session/${encodeURIComponent(message.token || "")}/diagnostic`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(message.report),
    }, 5000).then(async (response) => {
      const data = await response.json();
      sendResponse({ ok: response.ok, ...data });
    }).catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }
  if (message?.type === "career-bot-get-browser-plan") {
    fetchWithTimeout("http://127.0.0.1:8765/api/search/browser-plan", {}, 10000)
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Не удалось получить сценарии Career Bot");
        sendResponse({ ok: true, ...data });
      })
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }

  if (message?.type === "career-bot-import-profile") {
    fetchWithTimeout("http://127.0.0.1:8765/api/profile/hh-import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source: "hh-browser-safe",
        profile: message.profile || {},
        sections: Array.isArray(message.sections) ? message.sections : [],
        characters: Number(message.characters || 0),
      }),
    }, 10000)
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Career Bot не принял профиль");
        sendResponse({
          ok: true,
          importedFields: data.imported_fields || [],
          sectionsCount: Number(data.sections_count || 0),
          summary: data.summary || "",
        });
      })
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }

  if (message?.type === "career-bot-get-apply-session") {
    fetch(`http://127.0.0.1:8765/api/apply/session/${encodeURIComponent(message.token || "")}`)
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Не удалось загрузить письмо");
        sendResponse({ ok: true, ...data });
      })
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }

  if (message?.type === "career-bot-get-batch-apply-next") {
    fetch(`http://127.0.0.1:8765/api/apply/batches/${encodeURIComponent(message.batchToken || "")}/next`)
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Не удалось продолжить пакет откликов");
        sendResponse({ ok: true, ...data });
      })
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }

  if (message?.type === "career-bot-report-batch-apply-result") {
    fetch(`http://127.0.0.1:8765/api/apply/session/${encodeURIComponent(message.sessionToken || "")}/result`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ outcome: message.outcome, reason: message.reason || "" }),
    })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Не удалось сохранить результат отклика");
        sendResponse({ ok: true, ...data });
      })
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }

  if (message?.type === "career-bot-sync-areas") {
    fetch("https://api.hh.ru/areas", { headers: { Accept: "application/json" } })
      .then((response) => response.json())
      .then((areas) => fetch("http://127.0.0.1:8765/api/hh/areas/cache", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ areas }),
      }))
      .then((response) => response.json())
      .then((result) => sendResponse({ ok: true, count: result.count }))
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }

  if (message?.type !== "career-bot-add-vacancy") return false;

  const vacancyId = String(message.vacancy?.url || "").match(/\/vacancy\/(\d+)/)?.[1];
  const alreadyDetailed = Boolean(message.vacancy?.details_loaded) ||
    String(message.vacancy?.description || "").length > 1000;
  const vacancyPromise = vacancyId && !alreadyDetailed
    ? fetchWithTimeout(`https://api.hh.ru/vacancies/${vacancyId}`, { headers: { Accept: "application/json" } }, 12000)
        .then((response) => response.ok ? response.json() : Promise.reject(new Error("hh vacancy unavailable")))
        .then((item) => {
          const fullDescription = String(item.description || "")
            .replace(/<br\s*\/?>/gi, "\n")
            .replace(/<\/p>/gi, "\n")
            .replace(/<[^>]+>/g, " ")
            .replace(/&nbsp;/g, " ")
            .replace(/&amp;/g, "&")
            .replace(/&quot;/g, '"')
            .replace(/&#39;/g, "'")
            .replace(/[ \t]+/g, " ")
            .replace(/\n\s+/g, "\n")
            .trim();
          const details = [
            fullDescription,
            item.key_skills?.length
              ? `Ключевые навыки: ${item.key_skills.map((skill) => skill.name).filter(Boolean).join(", ")}.`
              : "",
            item.experience?.name ? `Опыт: ${item.experience.name}.` : "",
            item.employment_form?.name || item.employment?.name
              ? `Занятость: ${item.employment_form?.name || item.employment?.name}.`
              : "",
            item.work_format?.length
              ? `Формат работы: ${item.work_format.map((format) => format.name).filter(Boolean).join(", ")}.`
              : "",
          ].filter(Boolean).join("\n\n");
          return fullDescription.length > 200
            ? { ...message.vacancy, description: details.slice(0, 20000), details_loaded: true }
            : message.vacancy;
        })
        .catch(() => message.vacancy)
    : Promise.resolve(message.vacancy);

  vacancyPromise
    .then((vacancy) => {
      const hasDetails = Boolean(vacancy?.details_loaded) || String(vacancy?.description || "").length > 1000;
      return vacancyId && !hasDetails ? loadVacancyThroughRenderedTab(vacancy) : vacancy;
    })
    .then(async (vacancy) => {
      const response = await fetchWithTimeout("http://127.0.0.1:8765/api/vacancies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(vacancy),
      }, 35000);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Career Bot не принял вакансию");
      return { data, vacancy };
    })
    .then(({ data, vacancy }) => {
      sendResponse({
        ok: true,
        duplicate: Boolean(data.duplicate),
        updated: Boolean(data.updated),
        score: data.score,
        detailsLoaded: Boolean(vacancy.details_loaded) || String(vacancy.description || "").length > 1000,
      });
    })
    .catch((error) => sendResponse({ ok: false, error: error.message }));

  return true;
});
