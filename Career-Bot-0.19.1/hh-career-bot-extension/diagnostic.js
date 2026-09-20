// Diagnostic mode never clicks site controls or submits forms.
(() => {
  const token = new URLSearchParams(location.hash.slice(1)).get("careerBotDiagnostic");
  if (!token) return;

  const isVisible = (element) => Boolean(element.getClientRects().length && getComputedStyle(element).visibility !== "hidden" && getComputedStyle(element).display !== "none");
  const deepQuery = (selector) => {
    const found = [];
    const visit = (root) => {
      found.push(...root.querySelectorAll(selector));
      root.querySelectorAll("*").forEach((element) => { if (element.shadowRoot) visit(element.shadowRoot); });
    };
    visit(document);
    return [...new Set(found)];
  };
  const labelOf = (element) => (element.getAttribute("aria-label") || element.getAttribute("placeholder") || (element.matches("button,a,[role=button]") ? element.textContent : "") || "").trim().replace(/\s+/g, " ").slice(0, 120);
  const isTextCandidate = (element) => element.matches("textarea,input:not([type]),input[type=text],input[type=search],input[type=email],[contenteditable],[role=textbox]");
  const describe = (element) => ({
    tag: element.tagName, qa: element.getAttribute("data-qa"), role: element.getAttribute("role"),
    type: element.getAttribute("type"), name: element.getAttribute("name"), label: labelOf(element),
    disabled: Boolean(element.disabled || element.getAttribute("aria-disabled") === "true"),
    readonly: Boolean(element.readOnly || element.getAttribute("aria-readonly") === "true"),
    editable: Boolean(isTextCandidate(element) && !element.disabled && !element.readOnly && element.getAttribute("aria-disabled") !== "true"),
    contenteditable: element.getAttribute("contenteditable"), inShadowRoot: element.getRootNode() !== document,
  });
  const panel = document.createElement("aside");
  panel.style.cssText = "position:fixed;bottom:16px;left:16px;z-index:2147483647;background:#fff;color:#111;padding:16px;border:3px solid #2864dc;max-width:400px;font:14px sans-serif;box-shadow:0 4px 24px #555";
  const info = document.createElement("p");
  info.textContent = "Диагностика без отправки. Откройте форму вручную; бот запишет только признаки интерфейса.";
  panel.append(info);
  const capture = document.createElement("button");
  capture.type = "button";
  capture.textContent = "Записать поля и кнопки";
  const fill = document.createElement("button");
  fill.type = "button";
  fill.textContent = "Вставить одобренное письмо без отправки";
  fill.disabled = true;
  panel.append(capture, fill);
  document.body.append(panel);
  let letter = "";

  function blockers(hasOpenTextSurface) {
    // A vacancy page contains search filters, feedback widgets and arbitrary
    // words from the job description. They are not an application form. Only
    // inspect blockers after a real text surface has appeared.
    if (!hasOpenTextSurface) return [];
    const text = (document.body?.innerText || "").toLowerCase();
    const found = [];
    if (/(?:ответьте\s+на\s+вопрос|вопрос(?:ы)?\s+работодател|мини-?интервью|видеоинтервью|пройдите\s+тест|тестовое\s+задани|заполните\s+анкет)/i.test(text)) found.push("Дополнительный вопрос, тест или анкета работодателя.");
    if (deepQuery("select,input[type=radio],input[type=checkbox]").some((element) => isVisible(element) && !panel.contains(element))) found.push("В форме есть дополнительный выбор пользователя.");
    return found;
  }

  function inspect() {
    const scopes = deepQuery('[role="dialog"],dialog,[aria-modal="true"],form').filter((element) => !panel.contains(element) && isVisible(element));
    const allFields = deepQuery("textarea,input,[contenteditable],[role=textbox]").filter((element) => !panel.contains(element) && isTextCandidate(element) && isVisible(element));
    const fields = allFields.filter((element) => describe(element).editable);
    const buttons = deepQuery('button,a,[role="button"]').filter((element) => !panel.contains(element) && isVisible(element))
      .filter((element) => /отклик|сопровод|отправ|чат|добавить письмо|сообщени/i.test(labelOf(element))).slice(0, 80);
    return { scopes, allFields, fields, buttons, blockers: blockers(allFields.length > 0) };
  }

  function report(stage, match = null) {
    const found = inspect();
    const data = {
      extensionVersion: chrome.runtime.getManifest().version, stage, path: location.pathname,
      fieldCount: found.fields.length, fields: found.allFields.slice(0, 20).map(describe),
      buttons: found.buttons.map(describe), scopes: found.scopes.slice(0, 20).map(describe),
      blockers: found.blockers, exactLetterMatch: match,
    };
    chrome.runtime.sendMessage({ type: "career-bot-diagnostic-report", token, report: data }, (result) => {
      const error = chrome.runtime.lastError;
      if (error || !result?.ok) {
        info.textContent = "Не удалось сохранить отчёт: " + (error?.message || result?.error || "нет ответа");
        return;
      }
      const details = [result.route ? `Сценарий: ${result.route}.` : "", result.blockers?.length ? result.blockers.join(" ") : ""].filter(Boolean).join(" ");
      info.textContent = `Отчёт сохранён. Активных полей: ${found.fields.length}. ${details} Отправка не выполнялась.`;
    });
  }

  capture.addEventListener("click", () => report("manual_capture"));
  fill.addEventListener("click", () => {
    const { fields, blockers: foundBlockers } = inspect();
    if (fields.length !== 1 || foundBlockers.length) return report("ambiguous_field");
    const field = fields[0];
    if (field instanceof HTMLTextAreaElement || field instanceof HTMLInputElement) {
      const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(field), "value")?.set;
      if (setter) setter.call(field, letter); else field.value = letter;
    } else {
      field.focus();
      field.textContent = letter;
    }
    field.dispatchEvent(new Event("input", { bubbles: true }));
    field.dispatchEvent(new Event("change", { bubbles: true }));
    window.setTimeout(() => report("after_fill", field.isConnected && (field.value ?? field.textContent) === letter), 700);
  });

  chrome.runtime.sendMessage({ type: "career-bot-get-apply-session", token }, (result) => {
    const error = chrome.runtime.lastError;
    if (error || !result?.ok || !result.diagnostic) {
      info.textContent = "Диагностическая сессия недоступна. Перезапустите проверку из Career Bot.";
      return;
    }
    letter = result.letter;
    fill.disabled = false;
    report("loaded");
  });
})();
