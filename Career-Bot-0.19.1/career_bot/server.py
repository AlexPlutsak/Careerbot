from __future__ import annotations

import csv
import base64
import ctypes
import html
from collections import Counter
from ctypes import wintypes
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import subprocess
import threading
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = Path(__file__).resolve().parent / "static"
DATA_DIR = ROOT / "data"
RESUME_DIR = DATA_DIR / "resumes"
DB_PATH = Path(os.environ.get("CAREER_BOT_DB_PATH", DATA_DIR / "career_bot.sqlite"))
HH_API_BASE = "https://api.hh.ru"
OPENAI_API_BASE = "https://api.openai.com/v1/responses"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
OLLAMA_API_BASE = os.environ.get("OLLAMA_API_BASE", "http://127.0.0.1:11434")
APP_VERSION = "0.21.7"
SEARCH_WORK_FORMATS = {"", "REMOTE", "HYBRID", "ON_SITE"}
SESSION_DAYS = 30
PASSWORD_ITERATIONS = 310_000
DEFAULT_AI_MODEL = "gpt-4o-mini"
DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite"
DEFAULT_OLLAMA_MODEL = "qwen3:8b"
OLLAMA_LETTER_CONTEXT = 6144
LETTER_GENERATION_TIMEOUT = 300
CRYPTPROTECT_LOCAL_MACHINE = 0x4

DEFAULT_STRATEGY_ROLES = "Junior Project Manager, Project Coordinator, Project Assistant, Junior Product Manager, Product Analyst, Marketing Analyst, Research Analyst, Operations Coordinator, Marketing Project Manager, Business Development Assistant, UX/Product Research Assistant, Координатор образовательных и креативных проектов"
DEFAULT_STRATEGY_INDUSTRIES = "Продукт и IT, Digital и маркетинг, Креативные индустрии, Fashion и fashion-tech, Исследования и аналитика, Стартапы, Образовательные проекты, Новые бизнес-направления, Урбанистика"
DEFAULT_STRATEGY_PRIORITIES = "Гибкий график и совместимость с университетом, сильная команда или наставник, понятный продукт, развитие навыков, кросс-функциональные задачи, аналитика и обратная связь, запуск нового направления, постепенный рост ответственности"
DEFAULT_STRATEGY_HARD_STOPS = "Полный офис 5/2 8 часов, негибкий график, релокация, холодные продажи, чистая поддержка, монотонный документооборот, только таблицы без влияния на решения, непрозрачные условия, нет руководителя или понятных обязанностей"

FALLBACK_HH_AREAS = [
    {"id": "113", "name": "Россия"},
    {"id": "1", "name": "Москва"},
    {"id": "2", "name": "Санкт-Петербург"},
    {"id": "2019", "name": "Московская область"},
    {"id": "145", "name": "Ленинградская область"},
    {"id": "3", "name": "Екатеринбург"},
    {"id": "4", "name": "Новосибирск"},
    {"id": "66", "name": "Нижний Новгород"},
    {"id": "88", "name": "Казань"},
    {"id": "76", "name": "Ростов-на-Дону"},
    {"id": "53", "name": "Краснодар"},
    {"id": "99", "name": "Уфа"},
    {"id": "104", "name": "Челябинск"},
    {"id": "54", "name": "Красноярск"},
    {"id": "72", "name": "Пермь"},
    {"id": "68", "name": "Омск"},
    {"id": "78", "name": "Самара"},
    {"id": "84", "name": "Сочи"},
]

MANAGEMENT_ROLE_CATALOG = [
    {"name": "Project Manager", "group": "Проекты", "searches": ["Project Manager", "Менеджер проектов", "Руководитель проектов"], "skills": ["Управление проектами", "Планирование", "Управление рисками", "Бюджетирование", "Agile", "Scrum", "Jira", "Управление командой", "Работа со стейкхолдерами"]},
    {"name": "Руководитель проектов", "group": "Проекты", "searches": ["Руководитель проектов", "Менеджер проектов", "Project Manager"], "skills": ["Управление проектами", "Планирование", "Управление рисками", "Бюджетирование", "Проектная документация", "Управление командой", "Работа со стейкхолдерами"]},
    {"name": "Координатор проектов", "group": "Проекты", "searches": ["Координатор проектов", "Junior Project Manager", "Ассистент руководителя проектов"], "skills": ["Координация проектов", "Планирование", "Документооборот", "Jira", "Excel", "Коммуникация", "Контроль сроков"]},
    {"name": "Program Manager", "group": "Проекты", "searches": ["Program Manager", "Руководитель программы проектов", "Директор программы"], "skills": ["Управление программами", "Стратегическое планирование", "Управление портфелем", "Бюджетирование", "Управление рисками", "Работа со стейкхолдерами"]},
    {"name": "PMO Manager", "group": "Проекты", "searches": ["PMO Manager", "Руководитель проектного офиса", "Менеджер проектного офиса"], "skills": ["Управление проектным офисом", "Методология управления проектами", "Портфель проектов", "Отчетность", "Управление рисками", "Бюджетирование"]},
    {"name": "Product Manager", "group": "Продукт", "searches": ["Product Manager", "Менеджер продукта", "Продакт-менеджер"], "skills": ["Управление продуктом", "Product discovery", "CustDev", "Аналитика продукта", "Юнит-экономика", "A/B-тестирование", "Roadmap", "Приоритизация", "SQL", "Работа со стейкхолдерами"]},
    {"name": "Product Owner", "group": "Продукт", "searches": ["Product Owner", "Владелец продукта", "Менеджер продукта"], "skills": ["Управление бэклогом", "Постановка задач", "Приоритизация", "Scrum", "Agile", "Аналитика продукта", "Работа с командой разработки", "User stories"]},
    {"name": "Head of Product", "group": "Продукт", "searches": ["Head of Product", "Руководитель продуктового направления", "Директор по продукту"], "skills": ["Продуктовая стратегия", "Управление продуктовой командой", "P&L", "Аналитика продукта", "Портфель продуктов", "Управление изменениями", "Работа со стейкхолдерами"]},
    {"name": "Delivery Manager", "group": "Проекты", "searches": ["Delivery Manager", "Руководитель delivery", "Менеджер по управлению поставкой"], "skills": ["Управление поставкой", "Управление командой", "Agile", "Планирование ресурсов", "SLA", "Управление рисками", "Работа с заказчиком"]},
    {"name": "Scrum Master", "group": "Проекты", "searches": ["Scrum Master", "Agile Coach"], "skills": ["Scrum", "Agile", "Фасилитация", "Ретроспективы", "Командная динамика", "Управление конфликтами", "Коучинг команды"]},
    {"name": "Operations Manager", "group": "Операции", "searches": ["Operations Manager", "Операционный менеджер", "Руководитель операционного направления"], "skills": ["Операционное управление", "Оптимизация процессов", "Регламенты", "KPI", "Бюджетирование", "Управление командой", "Аналитика", "Excel"]},
    {"name": "Руководитель операционного направления", "group": "Операции", "searches": ["Руководитель операционного направления", "Операционный менеджер", "Operations Manager"], "skills": ["Операционное управление", "Оптимизация процессов", "Управление командой", "KPI", "Бюджетирование", "Управление изменениями"]},
    {"name": "Business Development Manager", "group": "Развитие", "searches": ["Business Development Manager", "Менеджер по развитию бизнеса", "Руководитель по развитию бизнеса"], "skills": ["Развитие бизнеса", "Переговоры", "Партнерства", "Анализ рынка", "Финансовое моделирование", "Презентации", "CRM"]},
    {"name": "Customer Success Manager", "group": "Клиенты", "searches": ["Customer Success Manager", "Менеджер по работе с клиентами", "Менеджер клиентского успеха"], "skills": ["Customer Success", "Работа с клиентами", "Удержание клиентов", "Онбординг", "CRM", "Аналитика", "Переговоры"]},
    {"name": "Account Manager", "group": "Клиенты", "searches": ["Account Manager", "Менеджер по работе с ключевыми клиентами", "Key Account Manager"], "skills": ["Управление клиентами", "Переговоры", "CRM", "Развитие клиентов", "Презентации", "Планирование продаж"]},
    {"name": "Руководитель отдела продаж", "group": "Продажи", "searches": ["Руководитель отдела продаж", "Head of Sales", "Директор по продажам"], "skills": ["Управление продажами", "Управление командой", "План продаж", "CRM", "KPI", "Переговоры", "Аналитика продаж"]},
    {"name": "Категорийный менеджер", "group": "Коммерция", "searches": ["Категорийный менеджер", "Category Manager", "Руководитель категории"], "skills": ["Управление категорией", "Ассортиментная матрица", "Ценообразование", "Анализ продаж", "Переговоры с поставщиками", "Excel"]},
    {"name": "Бренд-менеджер", "group": "Маркетинг", "searches": ["Бренд-менеджер", "Brand Manager", "Старший бренд-менеджер"], "skills": ["Управление брендом", "Маркетинговая стратегия", "Исследование рынка", "Медиапланирование", "Бюджетирование", "Аналитика"]},
    {"name": "Руководитель направления", "group": "Управление", "searches": ["Руководитель направления", "Директор направления", "Head of Department"], "skills": ["Стратегическое планирование", "Управление командой", "Бюджетирование", "KPI", "Управление изменениями", "Аналитика"]},
    {"name": "Team Lead", "group": "Управление", "searches": ["Team Lead", "Руководитель команды", "Тимлид"], "skills": ["Управление командой", "Постановка задач", "Менторинг", "Обратная связь", "Планирование", "Управление конфликтами"]},
]

PROFILE_CATALOG = {
    "work_formats": ["Удаленно", "Гибрид", "На месте работодателя", "Разъездной формат"],
    "strengths": ["Системное мышление", "Стратегическое мышление", "Лидерство", "Самостоятельность", "Ответственность", "Коммуникация", "Переговоры", "Фасилитация", "Управление конфликтами", "Принятие решений", "Работа в условиях неопределенности", "Ориентация на результат", "Аналитическое мышление", "Клиентоориентированность", "Быстрое обучение"],
    "constraints": ["Без ночных смен", "Без релокации", "Без командировок", "Без холодных продаж", "Только официальное оформление", "Только полная занятость", "Не рассматриваю офис", "Не рассматриваю разъездной формат", "Не рассматриваю проектную занятость", "Не рассматриваю продажи"],
}

STATUSES = [
    "found",
    "matched",
    "letter_ready",
    "applied",
    "interview",
    "offer",
    "rejected",
    "archived",
]

STATUS_LABELS = {
    "found": "Найдено",
    "matched": "Подходит",
    "letter_ready": "Письмо готово",
    "applied": "Отклик отправлен",
    "interview": "Интервью",
    "offer": "Оффер",
    "rejected": "Отказ",
    "archived": "Архив",
}

STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "или",
    "для",
    "как",
    "это",
    "что",
    "при",
    "над",
    "под",
    "без",
    "опыт",
    "работа",
    "работы",
    "команда",
    "команде",
    "вакансия",
    "требования",
    "обязанности",
}

# Это не список «ключевых слов для поиска». Категории описывают смысл задач
# разными формулировками: например, «реестр закупок» и «контроль заказов» оба
# относятся к операционному контуру. Благодаря этому факт не теряется только
# из-за того, что работодатель и кандидат использовали разные слова.
LETTER_CONCEPTS: dict[str, tuple[str, ...]] = {
    "operations": ("операц", "заказ", "статус", "поставк", "закуп", "логист", "реестр", "процесс", "срок"),
    "coordination": ("координ", "организ", "синхрон", "многозадач", "распредел", "участник", "команд"),
    "analytics": ("анализ", "данн", "метрик", "excel", "таблиц", "модел", "исслед", "статист"),
    "product": ("продукт", "mvp", "гипотез", "пользовател", "воронк", "конверс", "образц", "ассортимент"),
    "communication": ("поставщик", "клиент", "партнер", "партнёр", "переговор", "запрос", "переписк", "английск"),
    "documentation": ("документ", "отчет", "отчёт", "презентац", "тз", "счет", "счёт", "договор"),
    "marketing": ("маркет", "кампан", "аудитор", "позиционир", "бренд", "промо"),
    "events": ("мероприят", "фестив", "конференц", "выезд", "логистик"),
    "leadership": ("руковод", "лидир", "управлял", "команд", "ответственност"),
    "tools": ("sap", "jira", "powerpoint", "word", "amplitude", "sql", "crm"),
}

LETTER_ACTION_MARKERS = (
    "координир", "организ", "обработ", "контрол", "анализ", "разработ", "созда",
    "собрал", "подготов", "запуст", "увелич", "сниз", "провел", "провёл",
    "отслеж", "соглас", "исслед", "руковод",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


APPLY_STAGES = frozenset({
    "queued", "opening", "application_created", "letter_form_open", "letter_inserted",
    "sending", "sent_confirmed", "needs_manual", "unknown_result", "diagnostic",
})


def classify_diagnostic_report(report: dict[str, Any]) -> tuple[str, str, list[str]]:
    """Classify a HH screen from non-sensitive UI metadata.

    This deliberately returns a route *hint*, never permission to submit.  The
    extension must later prove every state transition on the live page.
    """
    fields = report.get("fields") if isinstance(report.get("fields"), list) else []
    buttons = report.get("buttons") if isinstance(report.get("buttons"), list) else []
    blockers = report.get("blockers") if isinstance(report.get("blockers"), list) else []
    blockers = [str(item)[:80] for item in blockers if str(item).strip()][:5]
    field_qas = {str(item.get("qa") or "") for item in fields if isinstance(item, dict)}
    button_qas = {str(item.get("qa") or "") for item in buttons if isinstance(item, dict)}
    labels = " ".join(str(item.get("label") or "").lower() for item in buttons if isinstance(item, dict))
    has_letter_field = any("letter" in qa or "cover" in qa for qa in field_qas)
    has_attach = "responded-success-attach-cover-letter" in button_qas or "приложить сопровод" in labels
    # A generic header button named "Чаты" is not the conversation for this
    # vacancy. Only HH's response-topic control is evidence of that route.
    has_chat = "vacancy-response-link-view-topic" in button_qas
    if blockers:
        return "manual", "needs_manual", blockers
    if has_letter_field:
        return "direct_letter_form", "letter_form_open", []
    if has_attach:
        return "post_application_letter", "application_created", []
    if has_chat:
        return "vacancy_chat", "application_created", []
    return "unknown", "unknown_result", ["Не распознана стандартная форма HH."]


def pause_apply_batch(conn: sqlite3.Connection, token: str) -> None:
    ts = now_iso()
    conn.execute("update apply_sessions set status = 'needs_manual', error = ?, updated_at = ? where batch_token = ? and status = 'running'",
                 ("Обработка прервана. Проверьте отклик на hh.ru перед повторной отправкой.", ts, token))
    conn.execute("update apply_sessions set expires_at = ? where batch_token = ?", (ts, token))
    conn.execute("update apply_batches set status = 'paused', expires_at = ? where token = ?", (ts, token))


def resume_apply_batch(conn: sqlite3.Connection, batch: sqlite3.Row) -> dict[str, Any]:
    old_token = batch["token"]
    if batch["status"] != "paused":
        raise ValueError("Сначала остановите активный пакет.")
    rows = conn.execute("select s.token, v.url from apply_sessions s join vacancies v on v.id = s.vacancy_id where s.batch_token = ? and s.status = 'pending' order by s.rowid", (old_token,)).fetchall()
    if not rows:
        raise ValueError("В пакете нет нетронутых вакансий для продолжения.")
    token = secrets.token_urlsafe(24)
    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    conn.execute("update apply_batches set token = ?, status = 'running', expires_at = ? where token = ?", (token, expires, old_token))
    conn.execute("update apply_sessions set batch_token = ? where batch_token = ?", (token, old_token))
    for row in rows:
        conn.execute("update apply_sessions set token = ?, expires_at = ?, updated_at = ? where token = ?",
                     (secrets.token_urlsafe(24), expires, now_iso(), row["token"]))
    return {"ok": True, "remaining": len(rows), "url": str(rows[0]["url"]).split("#", 1)[0] + "#careerBotBatch=" + token}


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, expected_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(actual, bytes.fromhex(expected_hex))
    except (ValueError, TypeError):
        return False


def public_user(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    user = dict(row)
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "role": user["role"],
        "can_use_ai": bool(user["can_use_ai"]),
        "ai_unlimited": bool(user["ai_unlimited"]),
    }


class DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob_from_bytes(value: bytes) -> tuple[DataBlob, Any]:
    buffer = ctypes.create_string_buffer(value)
    blob = DataBlob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    return blob, buffer


def protect_secret(value: str) -> bytes:
    if os.name != "nt":
        raise RuntimeError("Защищенное хранение ключа сейчас поддерживается только в Windows.")
    source, source_buffer = _blob_from_bytes(value.encode("utf-8"))
    output = DataBlob()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(source), "Career Bot AI key", None, None, None, CRYPTPROTECT_LOCAL_MACHINE, ctypes.byref(output)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)
        _ = source_buffer


def unprotect_secret(value: bytes) -> str:
    if os.name != "nt":
        raise RuntimeError("Защищенное хранение ключа сейчас поддерживается только в Windows.")
    source, source_buffer = _blob_from_bytes(bytes(value))
    output = DataBlob()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(source), None, None, None, None, 0, ctypes.byref(output)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)
        _ = source_buffer


def flatten_hh_areas(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for item in items:
        if item.get("id") and item.get("name"):
            result.append({"id": str(item["id"]), "name": str(item["name"])})
        children = item.get("areas")
        if isinstance(children, list):
            result.extend(flatten_hh_areas(children))
    unique = {item["id"]: item for item in result}
    return sorted(unique.values(), key=lambda item: (item["name"] != "Россия", item["name"].lower()))


def get_hh_areas() -> list[dict[str, str]]:
    try:
        with db() as conn:
            cached = conn.execute("select payload from reference_cache where key = 'hh_areas'").fetchone()
        if cached:
            areas = json.loads(cached["payload"])
            if isinstance(areas, list) and len(areas) > len(FALLBACK_HH_AREAS):
                return areas
    except (sqlite3.Error, json.JSONDecodeError):
        pass
    request = Request(
        f"{HH_API_BASE}/areas",
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 CareerBotDesktop",
        },
    )
    try:
        with urlopen(request, timeout=8) as response:
            raw = json.loads(response.read().decode("utf-8"))
        areas = flatten_hh_areas(raw if isinstance(raw, list) else [])
        if areas:
            cache_hh_areas(areas)
        return areas or FALLBACK_HH_AREAS
    except Exception:
        return FALLBACK_HH_AREAS


def cache_hh_areas(items: list[dict[str, Any]]) -> int:
    areas = flatten_hh_areas(items)
    if not areas:
        return 0
    with db() as conn:
        conn.execute(
            "insert into reference_cache (key, payload, updated_at) values ('hh_areas', ?, ?) "
            "on conflict(key) do update set payload = excluded.payload, updated_at = excluded.updated_at",
            (json.dumps(areas, ensure_ascii=False), now_iso()),
        )
    return len(areas)


def suggest_hh_areas(query: str) -> list[dict[str, str]]:
    query = query.strip()
    if not query:
        return get_hh_areas()[:30]
    request = Request(
        f"{HH_API_BASE}/suggests/area_leaves?{urlencode({'text': query})}",
        headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0 CareerBotDesktop"},
    )
    try:
        with urlopen(request, timeout=8) as response:
            raw = json.loads(response.read().decode("utf-8"))
        return [
            {"id": str(item["id"]), "name": str(item["text"])}
            for item in raw.get("items", [])
            if item.get("id") and item.get("text")
        ]
    except Exception:
        lowered = query.lower()
        return [item for item in FALLBACK_HH_AREAS if lowered in item["name"].lower()]


def profile_search_suggestions(profile: dict[str, Any]) -> list[dict[str, str]]:
    roles = split_list(profile.get("target_roles", ""))
    locations = split_list(profile.get("locations", ""))
    suggestions: list[dict[str, str]] = []
    for role in roles[:6]:
        catalog_role = next(
            (item for item in MANAGEMENT_ROLE_CATALOG if item["name"].lower() == role.lower()),
            None,
        )
        searches = catalog_role["searches"] if catalog_role else [role]
        for query in searches:
            suggestions.append({
                "label": query,
                "query": query,
                "reason": f"Реальное название вакансии для направления «{role}»",
            })
    unique = {item["query"].lower(): item for item in suggestions}
    return [
        {**item, "location_hint": locations[0] if locations else ""}
        for item in list(unique.values())[:18]
    ]


def get_profile_catalog() -> dict[str, Any]:
    all_skills = sorted({skill for role in MANAGEMENT_ROLE_CATALOG for skill in role["skills"]})
    return {
        "roles": MANAGEMENT_ROLE_CATALOG,
        "skills": all_skills,
        **PROFILE_CATALOG,
    }


def db() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma busy_timeout = 30000")
    conn.execute("pragma foreign_keys = on")
    return conn


def init_db() -> None:
    with db() as conn:
        conn.execute("pragma journal_mode = wal")
        conn.execute("pragma synchronous = normal")
        conn.executescript(
            """
            create table if not exists profile (
                id integer primary key check (id = 1),
                name text default '',
                target_roles text default '',
                locations text default '',
                salary_expectation text default '',
                work_format text default '',
                skills text default '',
                strengths text default '',
                constraints text default '',
                resume_text text default '',
                updated_at text not null
            );

            create table if not exists vacancies (
                id integer primary key autoincrement,
                title text not null,
                company text default '',
                location text default '',
                salary text default '',
                url text default '',
                source text default 'manual',
                description text not null,
                status text not null default 'found',
                score integer not null default 0,
                score_explanation text not null default '[]',
                cover_letter text default '',
                notes text default '',
                created_at text not null,
                updated_at text not null
            );

            create table if not exists events (
                id integer primary key autoincrement,
                vacancy_id integer,
                event_type text not null,
                payload text default '{}',
                created_at text not null,
                foreign key(vacancy_id) references vacancies(id)
            );

            create table if not exists reference_cache (
                key text primary key,
                payload text not null,
                updated_at text not null
            );

            create table if not exists users (
                id integer primary key autoincrement,
                username text not null unique collate nocase,
                display_name text not null,
                password_hash text not null,
                role text not null check (role in ('owner', 'tester')),
                can_use_ai integer not null default 0,
                ai_unlimited integer not null default 0,
                created_at text not null
            );

            create table if not exists sessions (
                token_hash text primary key,
                user_id integer not null,
                expires_at text not null,
                created_at text not null,
                foreign key(user_id) references users(id) on delete cascade
            );

            create table if not exists user_profiles (
                id integer primary key autoincrement,
                user_id integer not null unique,
                name text default '',
                target_roles text default '',
                locations text default '',
                salary_expectation text default '',
                work_format text default '',
                skills text default '',
                strengths text default '',
                constraints text default '',
                experience_years text default '',
                work_history text default '',
                hh_resume_title text default '',
                hh_imported_at text default '',
                hh_import_summary text default '',
                strategy_roles text default '',
                strategy_industries text default '',
                strategy_priorities text default '',
                strategy_hard_stops text default '',
                resume_text text default '',
                updated_at text not null,
                foreign key(user_id) references users(id) on delete cascade
            );

            create table if not exists ai_settings (
                user_id integer primary key,
                provider text not null default 'openai',
                model text not null default 'gpt-4o-mini',
                api_key_encrypted blob,
                gemini_api_key_encrypted blob,
                updated_at text not null,
                foreign key(user_id) references users(id) on delete cascade
            );

            create table if not exists ai_usage (
                id integer primary key autoincrement,
                user_id integer not null,
                vacancy_id integer,
                model text not null,
                provider text not null default 'openai',
                input_tokens integer not null default 0,
                output_tokens integer not null default 0,
                total_tokens integer not null default 0,
                created_at text not null,
                foreign key(user_id) references users(id) on delete cascade,
                foreign key(vacancy_id) references vacancies(id) on delete set null
            );

            create table if not exists letter_jobs (
                id integer primary key autoincrement,
                user_id integer not null,
                vacancy_id integer not null,
                batch_id integer,
                status text not null default 'queued',
                error text default '',
                created_at text not null,
                updated_at text not null,
                foreign key(user_id) references users(id) on delete cascade,
                foreign key(vacancy_id) references vacancies(id) on delete cascade
            );

            create table if not exists letter_batches (
                id integer primary key autoincrement,
                user_id integer not null,
                total integer not null default 0,
                created_at text not null,
                foreign key(user_id) references users(id) on delete cascade
            );

            create table if not exists apply_sessions (
                token text primary key,
                user_id integer not null,
                vacancy_id integer not null,
                letter text not null,
                expires_at text not null,
                created_at text not null
            );

            create table if not exists apply_batches (
                token text primary key,
                user_id integer not null,
                total integer not null default 0,
                status text not null default 'running',
                created_at text not null,
                expires_at text not null,
                finished_at text default '',
                foreign key(user_id) references users(id) on delete cascade
            );

            create table if not exists search_scenarios (
                id integer primary key autoincrement,
                user_id integer not null,
                name text not null,
                query text not null,
                area_id text default '1',
                area_name text default 'Москва',
                salary integer default 0,
                period integer default 7,
                only_with_salary integer not null default 0,
                contact text default '',
                result_limit integer not null default 50,
                work_format text not null default '',
                enabled integer not null default 1,
                source text not null default 'profile',
                intent_text text default '',
                reason text default '',
                created_at text not null,
                updated_at text not null,
                foreign key(user_id) references users(id) on delete cascade
            );

            create table if not exists search_runs (
                id integer primary key autoincrement,
                user_id integer not null,
                scenario_id integer not null,
                status text not null default 'queued',
                found integer not null default 0,
                processed integer not null default 0,
                imported integer not null default 0,
                duplicates integer not null default 0,
                error text default '',
                started_at text default '',
                finished_at text default '',
                created_at text not null,
                foreign key(user_id) references users(id) on delete cascade,
                foreign key(scenario_id) references search_scenarios(id) on delete cascade
            );

            """
        )
        vacancy_columns = {row["name"] for row in conn.execute("pragma table_info(vacancies)").fetchall()}
        if "user_id" not in vacancy_columns:
            conn.execute("alter table vacancies add column user_id integer")
        if "letter_evidence" not in vacancy_columns:
            conn.execute("alter table vacancies add column letter_evidence text default '[]'")
        if "letter_job_status" not in vacancy_columns:
            conn.execute("alter table vacancies add column letter_job_status text default ''")
        if "letter_job_error" not in vacancy_columns:
            conn.execute("alter table vacancies add column letter_job_error text default ''")
        if "letter_approved" not in vacancy_columns:
            conn.execute("alter table vacancies add column letter_approved integer not null default 0")
        if "score_components" not in vacancy_columns:
            conn.execute("alter table vacancies add column score_components text default '{}'")
        if "generation_tier" not in vacancy_columns:
            conn.execute("alter table vacancies add column generation_tier text default ''")
        if "letter_quality" not in vacancy_columns:
            conn.execute("alter table vacancies add column letter_quality text default ''")
        if "letter_generated_at" not in vacancy_columns:
            conn.execute("alter table vacancies add column letter_generated_at text default ''")
        letter_job_columns = {row["name"] for row in conn.execute("pragma table_info(letter_jobs)").fetchall()}
        if "batch_id" not in letter_job_columns:
            conn.execute("alter table letter_jobs add column batch_id integer")
        apply_session_columns = {row["name"] for row in conn.execute("pragma table_info(apply_sessions)").fetchall()}
        for field, definition in (
            ("batch_token", "text default ''"),
            ("status", "text not null default 'pending'"),
            ("error", "text default ''"),
            ("updated_at", "text default ''"),
            ("stage", "text not null default 'queued'"),
            ("route", "text not null default ''"),
            ("diagnostic_json", "text not null default ''"),
            ("letter_hash", "text not null default ''"),
        ):
            if field not in apply_session_columns:
                conn.execute(f"alter table apply_sessions add column {field} {definition}")
        profile_columns = {row["name"] for row in conn.execute("pragma table_info(user_profiles)").fetchall()}
        if "resume_file_name" not in profile_columns:
            conn.execute("alter table user_profiles add column resume_file_name text default ''")
        if "resume_file_path" not in profile_columns:
            conn.execute("alter table user_profiles add column resume_file_path text default ''")
        for field in ("experience_years", "work_history", "hh_resume_title", "hh_imported_at", "hh_import_summary"):
            if field not in profile_columns:
                conn.execute(f"alter table user_profiles add column {field} text default ''")
        for field, default in (
            ("strategy_roles", DEFAULT_STRATEGY_ROLES),
            ("strategy_industries", DEFAULT_STRATEGY_INDUSTRIES),
            ("strategy_priorities", DEFAULT_STRATEGY_PRIORITIES),
            ("strategy_hard_stops", DEFAULT_STRATEGY_HARD_STOPS),
        ):
            if field not in profile_columns:
                conn.execute(f"alter table user_profiles add column {field} text default ''")
            conn.execute(f"update user_profiles set {field} = ? where trim({field}) = ''", (default,))
        ai_settings_columns = {row["name"] for row in conn.execute("pragma table_info(ai_settings)").fetchall()}
        if "gemini_api_key_encrypted" not in ai_settings_columns:
            conn.execute("alter table ai_settings add column gemini_api_key_encrypted blob")
        ai_usage_columns = {row["name"] for row in conn.execute("pragma table_info(ai_usage)").fetchall()}
        if "provider" not in ai_usage_columns:
            conn.execute("alter table ai_usage add column provider text not null default 'openai'")
        scenario_columns = {row["name"] for row in conn.execute("pragma table_info(search_scenarios)").fetchall()}
        if "source" not in scenario_columns:
            conn.execute("alter table search_scenarios add column source text not null default 'profile'")
        if "intent_text" not in scenario_columns:
            conn.execute("alter table search_scenarios add column intent_text text default ''")
        if "reason" not in scenario_columns:
            conn.execute("alter table search_scenarios add column reason text default ''")
        if "work_format" not in scenario_columns:
            conn.execute("alter table search_scenarios add column work_format text not null default ''")
        conn.execute(
            """
            insert or ignore into profile (
                id, name, target_roles, locations, salary_expectation,
                work_format, skills, strengths, constraints, resume_text, updated_at
            ) values (1, '', '', '', '', '', '', '', '', '', ?)
            """,
            (now_iso(),),
        )


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    for field in ("score_explanation", "letter_evidence", "score_components"):
        if field not in item:
            continue
        try:
            item[field] = json.loads(item[field] or "[]")
        except json.JSONDecodeError:
            item[field] = []
    return item


def vacancy_insights(profile: dict[str, Any], vacancy: dict[str, Any]) -> dict[str, Any]:
    description = re.sub(r"\s+", " ", str(vacancy.get("description", ""))).strip()
    chunks = [
        chunk.strip(" •-–—:;.")
        for chunk in re.split(r"(?<=[.!?])\s+|[\n•]+", description)
        if len(chunk.strip()) >= 25
    ]
    requirement_markers = (
        "треб", "опыт", "знан", "умени", "навык", "обязан", "задач", "нужно", "ожида", "работа с",
    )
    requirements = [chunk for chunk in chunks if any(marker in chunk.lower() for marker in requirement_markers)][:6]
    if not requirements:
        requirements = chunks[:4]

    profile_text = " ".join(str(profile.get(field, "")) for field in PROFILE_FIELDS)
    profile_tokens = tokenize(profile_text)
    raw_vacancy_tokens = [
        word.strip(".,;:()[]{}")
        for word in re.findall(r"[A-Za-zА-Яа-я0-9+#.-]{2,}", f"{vacancy.get('title', '')} {description}".lower())
    ]
    token_frequencies = Counter(word for word in raw_vacancy_tokens if word and word not in STOPWORDS)
    vacancy_tokens = set(token_frequencies)
    common = profile_tokens & vacancy_tokens
    keyword_candidates = []
    for token in vacancy_tokens:
        if len(token) < 3 or token.isdigit():
            continue
        frequency = token_frequencies[token]
        score = frequency * 3 + (4 if token in common else 0) + (2 if re.search(r"[A-Za-z+#]", token) else 0)
        keyword_candidates.append((score, token))
    keywords = [token for _, token in sorted(keyword_candidates, key=lambda item: (-item[0], item[1]))[:14]]
    matched = [token for token in keywords if token in common][:10]
    return {
        "requirements": requirements,
        "keywords": keywords,
        "matched_keywords": matched,
        "description_complete": vacancy_has_full_description(vacancy),
    }


def enrich_vacancy(profile: dict[str, Any], row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    item = row_to_dict(row) if isinstance(row, sqlite3.Row) else dict(row)
    result = score_vacancy(profile, item)
    item["score"] = result.score
    item["score_explanation"] = result.explanation
    item["score_components"] = result.components
    item["generation_tier"] = result.generation_tier
    item["evidence_plan"] = build_letter_evidence_plan(profile, item)
    item["insights"] = vacancy_insights(profile, item)
    item["eligibility"] = assess_eligibility(profile, item)
    return item


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[A-Za-zА-Яа-я0-9+#.-]{2,}", text.lower())
    return {word.strip(".,;:()[]{}") for word in words if word not in STOPWORDS}


def split_list(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,;\n]+", text or "") if part.strip()]


def merge_list_text(current: str, imported: str) -> str:
    values: list[str] = []
    seen: set[str] = set()
    for value in [*split_list(current), *split_list(imported)]:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        values.append(value)
    return ", ".join(values)


def merge_imported_section(current: str, imported: str, title: str) -> str:
    marker = f"## {title}\n"
    base = str(current or "").split(marker, 1)[0].rstrip()
    imported = str(imported or "").strip()
    return f"{base}\n\n{marker}{imported}".strip() if imported else base


HH_PROFILE_NOISE = re.compile(
    r"^(?:hh pro|продвижение, подсветка резюме|готовое резюме|доверьте составление резюме|"
    r"репетиция собеседования|подготовьтесь к собеседованию|карьерная консультация|получите советы|"
    r"мои резюме|заказать резюме|создать резюме|статистика за неделю|показы|просмотры|приглашения|"
    r"резюме редко попадает|поднимите его|заказать рекомендацию|\d+\s+вакансий|посмотреть|"
    r"перейти к курсу|ещё\s*[−-]|hh\d+|с нуля|продвинутый)\b.*$",
    re.IGNORECASE,
)


def sanitize_hh_profile_text(value: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in str(value or "").replace("\u2028", "\n").splitlines()]
    cleaned: list[str] = []
    skip_promotions = False
    for line in lines:
        if re.match(r"^(?:подтверждение навыков и языков|курсы по профессии|похожие резюме|рекомендованные вакансии)", line, re.IGNORECASE):
            skip_promotions = True
            continue
        if skip_promotions:
            if re.match(r"^##\s+", line):
                skip_promotions = False
            else:
                continue
        if not line or HH_PROFILE_NOISE.match(line) or re.match(r"^(?:[-−]?\d+%|\d[\d\s]*\s*₽)", line):
            continue
        if cleaned and line.casefold() == cleaned[-1].casefold():
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def parse_years(value: Any) -> float | None:
    match = re.search(r"\d+(?:[.,]\d+)?", str(value or ""))
    return float(match.group(0).replace(",", ".")) if match else None


def required_experience(text: str) -> tuple[float | None, str]:
    normalized = re.sub(r"\s+", " ", str(text or "").lower())
    if "без опыта" in normalized:
        return 0.0, "Без опыта"
    patterns = (
        (r"(?:опыт[^.]{0,35})?(?:от|не менее|более)\s*(\d+)\s*(?:лет|года|год)", None),
        (r"опыт[^.]{0,25}?(\d+)\s*[–—-]\s*(\d+)\s*(?:лет|года|год)", "range"),
    )
    for pattern, kind in patterns:
        match = re.search(pattern, normalized)
        if match:
            minimum = float(match.group(1))
            label = f"От {int(minimum)} лет" if kind is None else f"{match.group(1)}–{match.group(2)} года"
            return minimum, label
    return None, "Не указано"


def assess_eligibility(profile: dict[str, Any], vacancy: dict[str, Any]) -> dict[str, Any]:
    description = f"{vacancy.get('title', '')}\n{vacancy.get('description', '')}"
    candidate_years = parse_years(profile.get("experience_years"))
    minimum_years, requirement_label = required_experience(description)
    checks: list[dict[str, str]] = []
    hard_fail = False
    uncertain = not vacancy_has_full_description(vacancy)

    if minimum_years is None:
        checks.append({"criterion": "Опыт", "status": "review", "reason": "Требование к стажу не распознано."})
        uncertain = True
    elif candidate_years is None:
        checks.append({"criterion": "Опыт", "status": "review", "reason": f"Вакансия: {requirement_label}. Укажите стаж в профиле."})
        uncertain = True
    elif candidate_years + 0.01 < minimum_years:
        checks.append({"criterion": "Опыт", "status": "fail", "reason": f"Нужно {requirement_label}, в профиле {candidate_years:g} года."})
        hard_fail = True
    else:
        checks.append({"criterion": "Опыт", "status": "pass", "reason": f"Нужно {requirement_label}, в профиле {candidate_years:g} года."})

    constraints = split_list(profile.get("constraints", ""))
    hits = [item for item in constraints if item.lower() in description.lower()]
    if hits:
        checks.append({"criterion": "Ограничения", "status": "fail", "reason": f"Найдены: {', '.join(hits[:3])}."})
        hard_fail = True
    elif constraints:
        checks.append({"criterion": "Ограничения", "status": "pass", "reason": "Явных конфликтов не найдено."})

    roles = split_list(profile.get("target_roles", ""))
    if roles and not any(role.lower() in description.lower() for role in roles):
        checks.append({"criterion": "Целевая роль", "status": "review", "reason": "Нет точного совпадения с выбранными ролями."})
        uncertain = True

    score = int(vacancy.get("score", 0) or 0)
    if hard_fail or score < 40:
        status = "mismatch"
    elif uncertain or score < 60:
        status = "review"
    else:
        status = "match"
    labels = {"match": "Подходит", "review": "Нужно проверить", "mismatch": "Не подходит"}
    return {"status": status, "label": labels[status], "checks": checks}


@dataclass
class ScoreResult:
    score: int
    explanation: list[str]
    components: dict[str, int]
    generation_tier: str


def score_vacancy(profile: dict[str, Any], vacancy: dict[str, Any]) -> ScoreResult:
    title = str(vacancy.get("title", ""))
    description = str(vacancy.get("description", ""))
    combined = f"{title}\n{description}".lower()
    vacancy_concepts = letter_concepts(combined)
    explanation: list[str] = []
    components: dict[str, int] = {}

    # Gate: only explicit deal-breakers exclude a vacancy. Missing data means review,
    # not an automatic rejection.
    hard_patterns = {
        "полный офис 5/2": ("5/2", "полное присутствие", "только офис"),
        "негибкий график": ("строго 5/2", "фиксированный график", "с 9 до 18"),
        "релокация": ("релокац", "переезд обязател"),
        "холодные продажи": ("холодн", "поиск клиентов"),
        "чистая поддержка": ("служба поддержки", "техническая поддержка", "call-центр"),
    }
    hard_hits = [label for label, markers in hard_patterns.items() if any(marker in combined for marker in markers)]
    if hard_hits:
        components = {"task_fit": 0, "prospects": 0, "interest": 0, "conditions": 0, "data_quality": 0}
        explanation.append("Стоп-фактор: " + ", ".join(hard_hits) + ". Вакансия исключена из автогенерации.")
        return ScoreResult(0, explanation, components, "blocked")

    # 1/5: task fit is based on evidence cards, not a generic keyword list.
    evidence_plan = build_letter_evidence_plan(profile, vacancy)
    selected = evidence_plan.get("selected_facts", [])
    matched_concepts = set().union(*(set(item.get("concepts", [])) for item in selected)) if selected else set()
    task_fit = min(35, len(matched_concepts & vacancy_concepts) * 9 + min(12, len(selected) * 6))
    components["task_fit"] = task_fit
    explanation.append(f"Соответствие задачам и подтверждённым фактам: {task_fit}/35.")

    prospect_markers = ("наставник", "обучен", "развити", "карьерн", "новое направлен", "запуск", "продукт", "кросс-функ", "аналитик", "обратн")
    prospect_hits = sum(marker in combined for marker in prospect_markers)
    prospects = min(25, prospect_hits * 4 + (3 if "стаж" in combined or "junior" in combined else 0))
    components["prospects"] = prospects
    explanation.append(f"Перспективность роли и среды: {prospects}/25.")

    role_terms = split_list(profile.get("strategy_roles", "")) + split_list(profile.get("target_roles", ""))
    industry_terms = split_list(profile.get("strategy_industries", ""))
    interest_hits = [term for term in [*role_terms, *industry_terms] if term.lower() in combined]
    # Concept coverage protects against different wording: product/marketing/research etc.
    desired_concepts = letter_concepts(" ".join(role_terms + industry_terms))
    interest = min(20, len(interest_hits) * 4 + len(desired_concepts & vacancy_concepts) * 3)
    components["interest"] = interest
    explanation.append(f"Интерес к роли и сфере: {interest}/20.")

    flexible = any(marker in combined for marker in ("гибрид", "удален", "удалён", "гибк", "частичн", "неполная занятость", "стажировк"))
    location_ok = not profile.get("locations") or any(loc.lower() in f"{vacancy.get('location', '')} {combined}" for loc in split_list(profile.get("locations", "")))
    conditions = (10 if flexible else 2) + (5 if location_ok else 0)
    components["conditions"] = conditions
    explanation.append(f"Условия и совместимость с учёбой: {conditions}/15.")

    complete = vacancy_has_full_description(vacancy)
    clear_role = bool(title.strip() and str(vacancy.get("company", "")).strip())
    data_quality = (3 if complete else 1) + (2 if clear_role else 0)
    components["data_quality"] = data_quality
    explanation.append(f"Качество карточки вакансии: {data_quality}/5.")

    score = sum(components.values())
    tier = "deep" if score >= 80 else "short" if score >= 65 else "manual"
    recommendation = {"deep": "Лучший приоритет: глубокое письмо.", "short": "Хороший приоритет: короткое точное письмо.", "manual": "Ниже порога автогенерации: оставлено для ручного решения."}[tier]
    explanation.append(recommendation)
    return ScoreResult(score, explanation, components, tier)


PROFILE_FIELDS = [
    "name",
    "target_roles",
    "locations",
    "salary_expectation",
    "work_format",
    "skills",
    "strengths",
    "constraints",
    "experience_years",
    "work_history",
    "hh_resume_title",
    "strategy_roles",
    "strategy_industries",
    "strategy_priorities",
    "strategy_hard_stops",
    "resume_text",
]


def ensure_user_profile(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute(
        """insert or ignore into user_profiles
        (user_id, strategy_roles, strategy_industries, strategy_priorities, strategy_hard_stops, updated_at)
        values (?, ?, ?, ?, ?, ?)""",
        (user_id, DEFAULT_STRATEGY_ROLES, DEFAULT_STRATEGY_INDUSTRIES, DEFAULT_STRATEGY_PRIORITIES,
         DEFAULT_STRATEGY_HARD_STOPS, now_iso()),
    )


def get_profile(conn: sqlite3.Connection, user_id: int) -> dict[str, Any]:
    ensure_user_profile(conn, user_id)
    row = conn.execute("select * from user_profiles where user_id = ?", (user_id,)).fetchone()
    profile = row_to_dict(row)
    profile["resume_file_uploaded"] = bool(profile.get("resume_file_path"))
    profile.pop("resume_file_path", None)
    return profile


def queue_letter_job(conn: sqlite3.Connection, user_id: int, vacancy_id: int, batch_id: int | None = None) -> dict[str, Any]:
    current = conn.execute(
        "select * from letter_jobs where user_id = ? and vacancy_id = ? and status in ('queued', 'running') "
        "order by id desc limit 1",
        (user_id, vacancy_id),
    ).fetchone()
    if current:
        return dict(current)
    ts = now_iso()
    cursor = conn.execute(
        "insert into letter_jobs (user_id, vacancy_id, batch_id, status, created_at, updated_at) values (?, ?, ?, 'queued', ?, ?)",
        (user_id, vacancy_id, batch_id, ts, ts),
    )
    conn.execute(
        "update vacancies set letter_job_status = 'queued', letter_job_error = '', updated_at = ? where id = ?",
        (ts, vacancy_id),
    )
    return dict(conn.execute("select * from letter_jobs where id = ?", (cursor.lastrowid,)).fetchone())


def process_letter_job(job_id: int) -> None:
    with db() as conn:
        job = conn.execute("select * from letter_jobs where id = ?", (job_id,)).fetchone()
        if not job or job["status"] != "queued":
            return
        user_id, vacancy_id = int(job["user_id"]), int(job["vacancy_id"])
        vacancy_row = conn.execute(
            "select * from vacancies where id = ? and user_id = ?", (vacancy_id, user_id)
        ).fetchone()
        if not vacancy_row:
            conn.execute("update letter_jobs set status = 'error', error = ?, updated_at = ? where id = ?", ("Вакансия удалена", now_iso(), job_id))
            return
        vacancy = row_to_dict(vacancy_row)
        profile = get_profile(conn, user_id)
        vacancy["generation_tier"] = "deep" if int(vacancy.get("score", 0) or 0) >= 80 else "short"
        provider, api_key, model = get_ai_credentials(conn, user_id)
        contact_row = conn.execute(
            "select contact from search_scenarios where user_id = ? and trim(contact) != '' order by updated_at desc limit 1",
            (user_id,),
        ).fetchone()
        hh_contact = str(contact_row["contact"] or "") if contact_row else ""
        conn.execute("update letter_jobs set status = 'running', updated_at = ? where id = ?", (now_iso(), job_id))
        conn.execute("update vacancies set letter_job_status = 'running', letter_job_error = '' where id = ?", (vacancy_id,))

    # Мягко обогащаем сокращённую карточку через открытый API hh.ru. Ошибка API не
    # блокирует письмо: в этом случае модель продолжает работу с сохранённой карточкой.
    hh_match = re.search(r"/vacancy/(\d+)", str(vacancy.get("url", "")))
    if hh_match and not vacancy_has_full_description(vacancy):
        try:
            enriched = fetch_hh_vacancy(hh_match.group(1), hh_contact)
            if len(str(enriched.get("description", ""))) > len(str(vacancy.get("description", ""))) + 100:
                vacancy = {**vacancy, **enriched, "id": vacancy_id, "user_id": user_id}
                score = score_vacancy(profile, vacancy)
                with db() as conn:
                    conn.execute(
                        """update vacancies set title = ?, company = ?, location = ?, salary = ?, url = ?, source = ?,
                        description = ?, score = ?, score_explanation = ?, updated_at = ? where id = ? and user_id = ?""",
                        (
                            vacancy["title"], vacancy["company"], vacancy["location"], vacancy["salary"],
                            vacancy["url"], vacancy["source"], vacancy["description"], score.score,
                            json.dumps(score.explanation, ensure_ascii=False), now_iso(), vacancy_id, user_id,
                        ),
                    )
        except Exception:
            pass

    if provider == "ollama":
        operation = lambda: generate_ollama_letter(profile, vacancy, model)
    elif provider == "gemini":
        operation = lambda: generate_gemini_letter(profile, vacancy, api_key, model)
    else:
        operation = lambda: generate_ai_letter(profile, vacancy, api_key, model)
    letter, evidence, usage = run_with_timeout(operation, LETTER_GENERATION_TIMEOUT)
    soft_issues = [issue for issue in letter_style_issues(letter, str(profile.get("name", ""))) if issue not in HARD_LETTER_ISSUES]
    letter_quality = "needs_review" if soft_issues else "ready"
    if soft_issues:
        evidence.append({
            "requirement": "Стиль письма",
            "claim": "; ".join(soft_issues[:3]),
            "quote": "Автоматическая мягкая проверка",
            "verification": "warning",
            "note": "Письмо сохранено, но перед отправкой стоит быстро прочитать его.",
        })

    with db() as conn:
        current_job = conn.execute("select status from letter_jobs where id = ?", (job_id,)).fetchone()
        if not current_job or current_job["status"] != "running":
            return
        ts = now_iso()
        conn.execute(
            """update vacancies set cover_letter = ?, letter_evidence = ?, letter_quality = ?, letter_generated_at = ?, status = 'letter_ready',
            letter_job_status = 'done', letter_job_error = '', letter_approved = 0, updated_at = ? where id = ? and user_id = ?""",
            (letter, json.dumps(evidence, ensure_ascii=False), letter_quality, ts, ts, vacancy_id, user_id),
        )
        conn.execute("update letter_jobs set status = 'done', updated_at = ? where id = ?", (ts, job_id))
        conn.execute(
            """insert into ai_usage
            (user_id, vacancy_id, provider, model, input_tokens, output_tokens, total_tokens, created_at)
            values (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, vacancy_id, provider, model, usage["input_tokens"], usage["output_tokens"], usage["total_tokens"], ts),
        )
        conn.execute(
            "insert into events(vacancy_id, event_type, payload, created_at) values (?, 'letter_generated', ?, ?)",
            (vacancy_id, json.dumps({"provider": provider, "model": model, "usage": usage}, ensure_ascii=False), ts),
        )


def run_with_timeout(operation: Callable[[], tuple[str, list[dict[str, str]], dict[str, int]]], timeout: int):
    """Run a provider call with a wall-clock deadline, even if HTTP keeps the socket active."""
    result: list[tuple[str, list[dict[str, str]], dict[str, int]]] = []
    failure: list[BaseException] = []

    def target() -> None:
        try:
            result.append(operation())
        except BaseException as exc:  # propagate provider errors to the queue worker
            failure.append(exc)

    thread = threading.Thread(target=target, name="letter-generation", daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise TimeoutError(f"Генерация письма превысила лимит {timeout} секунд и была остановлена.")
    if failure:
        raise failure[0]
    if not result:
        raise ValueError("Провайдер не вернул результат генерации.")
    return result[0]


def letter_queue_worker() -> None:
    while True:
        job_id = None
        try:
            with db() as conn:
                row = conn.execute("select id from letter_jobs where status = 'queued' order by id limit 1").fetchone()
                job_id = int(row["id"]) if row else None
            if job_id is not None:
                try:
                    process_letter_job(job_id)
                except Exception as exc:
                    with db() as conn:
                        job = conn.execute("select vacancy_id from letter_jobs where id = ?", (job_id,)).fetchone()
                        error = str(exc)[:1000]
                        conn.execute("update letter_jobs set status = 'error', error = ?, updated_at = ? where id = ?", (error, now_iso(), job_id))
                        if job:
                            conn.execute("update vacancies set letter_job_status = 'error', letter_job_error = ? where id = ?", (error, int(job["vacancy_id"])))
            else:
                time.sleep(0.8)
        except Exception:
            try:
                (DATA_DIR / "letter-worker-error.log").write_text(
                    f"{now_iso()}\n{traceback.format_exc()}\n", encoding="utf-8"
                )
            except Exception:
                pass
            time.sleep(1.5)


def rescore_all(conn: sqlite3.Connection, user_id: int) -> None:
    profile = get_profile(conn, user_id)
    rows = conn.execute("select * from vacancies where user_id = ?", (user_id,)).fetchall()
    for row in rows:
        vacancy = row_to_dict(row)
        result = score_vacancy(profile, vacancy)
        conn.execute(
            """update vacancies set score = ?, score_explanation = ?, score_components = ?, generation_tier = ?,
            updated_at = ? where id = ? and user_id = ?""",
            (result.score, json.dumps(result.explanation, ensure_ascii=False), json.dumps(result.components, ensure_ascii=False),
             result.generation_tier, now_iso(), vacancy["id"], user_id),
        )


def generate_letter(profile: dict[str, Any], vacancy: dict[str, Any]) -> str:
    name = profile.get("name", "").strip()
    roles = split_list(profile.get("target_roles", ""))
    skills = split_list(profile.get("skills", ""))
    strengths = split_list(profile.get("strengths", ""))

    vacancy_text = f"{vacancy.get('title', '')}\n{vacancy.get('description', '')}".lower()
    matched_skills = [skill for skill in skills if skill.lower() in vacancy_text]
    matched_strengths = [item for item in strengths if item.lower() in vacancy_text]

    intro_role = roles[0] if roles else vacancy.get("title", "эту роль")
    skill_line = ", ".join(matched_skills[:5] or skills[:5])
    strength_line = ", ".join(matched_strengths[:3] or strengths[:3])

    parts = [
        "Здравствуйте!",
        "",
        f"Меня заинтересовала позиция «{vacancy.get('title', 'в вашей команде')}»"
        + (f" в {vacancy.get('company')}." if vacancy.get("company") else "."),
        f"Мой профиль сфокусирован на направлении: {intro_role}.",
    ]

    if skill_line:
        parts.append(f"Из релевантных навыков могу опереться на: {skill_line}.")
    if strength_line:
        parts.append(f"Сильные стороны, которые могут быть полезны на этой позиции: {strength_line}.")

    parts.extend(
        [
            "Буду рад обсудить, как мой опыт может помочь команде в задачах этой роли.",
            "",
            f"С уважением,{(' ' + name) if name else ''}",
        ]
    )
    return "\n".join(parts)


def get_ai_status(conn: sqlite3.Connection, user_id: int) -> dict[str, Any]:
    settings = conn.execute("select * from ai_settings where user_id = ?", (user_id,)).fetchone()
    usage = conn.execute(
        """select count(*) as generations, coalesce(sum(input_tokens), 0) as input_tokens,
        coalesce(sum(output_tokens), 0) as output_tokens, coalesce(sum(total_tokens), 0) as total_tokens
        from ai_usage where user_id = ?""",
        (user_id,),
    ).fetchone()
    provider = settings["provider"] if settings and settings["provider"] in {"openai", "gemini", "ollama"} else "openai"
    openai_configured = bool(os.environ.get("OPENAI_API_KEY") or (settings and settings["api_key_encrypted"]))
    gemini_configured = bool(
        os.environ.get("GEMINI_API_KEY") or (settings and settings["gemini_api_key_encrypted"])
    )
    ollama_models = get_ollama_models()
    model = settings["model"] if settings else DEFAULT_AI_MODEL
    ollama_running = ollama_models is not None
    ollama_model_available = bool(ollama_models is not None and model in ollama_models)
    configured_by_provider = {
        "openai": openai_configured,
        "gemini": gemini_configured,
        "ollama": ollama_model_available,
    }
    configured = configured_by_provider[provider]
    env_name = "GEMINI_API_KEY" if provider == "gemini" else "OPENAI_API_KEY"
    return {
        "provider": provider,
        "model": model,
        "configured": configured,
        "key_source": "local" if provider == "ollama" else (
            "environment" if os.environ.get(env_name) else ("windows" if configured else "none")
        ),
        "providers": {
            "openai": {"configured": openai_configured},
            "gemini": {"configured": gemini_configured},
            "ollama": {
                "configured": ollama_model_available,
                "running": ollama_running,
                "models": ollama_models or [],
            },
        },
        "usage": dict(usage),
    }


def get_ai_credentials(conn: sqlite3.Connection, user_id: int) -> tuple[str, str, str]:
    settings = conn.execute("select * from ai_settings where user_id = ?", (user_id,)).fetchone()
    provider = settings["provider"] if settings and settings["provider"] in {"openai", "gemini", "ollama"} else "openai"
    default_model = (
        DEFAULT_OLLAMA_MODEL if provider == "ollama" else DEFAULT_GEMINI_MODEL if provider == "gemini" else DEFAULT_AI_MODEL
    )
    model = settings["model"] if settings else default_model
    if provider == "ollama":
        models = get_ollama_models()
        if models is None:
            raise ValueError("Ollama не запущена. Откройте Ollama и повторите генерацию.")
        if model not in models:
            raise ValueError(f"Локальная модель {model} не загружена. Запустите setup-ollama.cmd.")
        return provider, "", model
    env_name = "GEMINI_API_KEY" if provider == "gemini" else "OPENAI_API_KEY"
    key_column = "gemini_api_key_encrypted" if provider == "gemini" else "api_key_encrypted"
    provider_name = "Gemini" if provider == "gemini" else "OpenAI"
    env_key = os.environ.get(env_name, "").strip()
    if env_key:
        return provider, env_key, model
    encrypted = settings[key_column] if settings else None
    if not encrypted:
        raise ValueError(f"Сначала подключите {provider_name} API во вкладке «ИИ».")
    try:
        return provider, unprotect_secret(encrypted), model
    except OSError as exc:
        raise ValueError(
            "Windows не смогла открыть сохраненный API-ключ. Введите ключ повторно во вкладке «ИИ» и сохраните подключение."
        ) from exc


def get_ollama_models() -> list[str] | None:
    request = Request(f"{OLLAMA_API_BASE}/api/tags", headers={"User-Agent": f"CareerBot/{APP_VERSION}"})
    try:
        with urlopen(request, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return [str(item.get("name", "")) for item in payload.get("models", []) if item.get("name")]
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def get_local_search_model(conn: sqlite3.Connection, user_id: int) -> str:
    models = get_ollama_models()
    if models is None:
        raise ValueError("Ollama не запущена. Откройте Ollama и повторите создание сценариев.")
    if not models:
        raise ValueError("В Ollama нет локальных моделей. Запустите setup-ollama.cmd.")
    settings = conn.execute("select provider, model from ai_settings where user_id = ?", (user_id,)).fetchone()
    preferred = str(settings["model"] or "") if settings and settings["provider"] == "ollama" else DEFAULT_OLLAMA_MODEL
    if preferred in models:
        return preferred
    return models[0]


def normalize_ai_search_scenarios(payload: Any) -> list[dict[str, str]]:
    raw_items = payload.get("scenarios", []) if isinstance(payload, dict) else []
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        query = re.sub(r"\s+", " ", str(raw.get("query") or raw.get("name") or "")).strip(" \t\r\n-–—:;,.\"")
        name = re.sub(r"\s+", " ", str(raw.get("name") or query)).strip()
        reason = re.sub(r"\s+", " ", str(raw.get("reason") or "Подобрано по описанию желаемой работы.")).strip()
        key = query.casefold()
        if not query or len(query) > 100 or len(query.split()) > 10 or key in seen:
            continue
        seen.add(key)
        items.append({"query": query, "name": name[:100] or query, "reason": reason[:320]})
        if len(items) >= 6:
            break
    if not items:
        raise ValueError("Локальная модель не предложила корректных названий вакансий. Уточните описание и повторите.")
    return items


def generate_local_search_scenarios(
    profile: dict[str, Any], intent: str, vacancy_titles: list[str], model: str
) -> tuple[list[dict[str, str]], dict[str, int]]:
    catalog_titles = sorted({
        title
        for role in MANAGEMENT_ROLE_CATALOG
        for title in [role["name"], *role.get("searches", [])]
    })
    profile_context = {
        "target_roles": str(profile.get("target_roles") or "")[:1500],
        "skills": str(profile.get("skills") or "")[:2500],
        "strengths": str(profile.get("strengths") or "")[:1500],
        "constraints": str(profile.get("constraints") or "")[:1500],
        "work_format": str(profile.get("work_format") or "")[:800],
        "experience_years": str(profile.get("experience_years") or "")[:500],
        "work_history": str(profile.get("work_history") or "")[:3500],
    }
    schema = {
        "type": "object",
        "properties": {
            "scenarios": {
                "type": "array",
                "minItems": 2,
                "maxItems": 6,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "query": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["name", "query", "reason"],
                },
            },
        },
        "required": ["scenarios"],
    }
    instruction = (
        "Ты карьерный аналитик и составляешь поисковые сценарии для hh.ru. "
        "По свободному описанию пользователя предложи от 2 до 6 коротких запросов, которые выглядят как реальные "
        "названия должностей на рынке. Не превращай навыки, обязанности, отрасли или пожелания в название вакансии. "
        "Сначала предложи самые точные роли, затем допустимые смежные. Не придумывай экзотические должности. "
        "Если в примерах вакансий или каталоге есть подходящее устойчивое название, используй его формулировку. "
        "Пожелания пользователя важнее старых целевых ролей профиля. Для каждого запроса кратко объясни связь с "
        "описанием и профилем. Верни только JSON по заданной схеме."
    )
    user_content = json.dumps({
        "desired_work": intent,
        "profile": profile_context,
        "existing_vacancy_titles": vacancy_titles[:80],
        "known_market_titles": catalog_titles[:160],
    }, ensure_ascii=False)
    request_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": instruction},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
        "think": False,
        "format": schema,
        "options": {"temperature": 0.25},
    }
    request = Request(
        f"{OLLAMA_API_BASE}/api/chat",
        data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": f"CareerBot/{APP_VERSION}"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            details = str(json.loads(exc.read().decode("utf-8")).get("error", ""))
        except (json.JSONDecodeError, UnicodeDecodeError):
            details = ""
        raise ValueError(f"Ollama вернула ошибку {exc.code}. {details}".strip()) from exc
    except URLError as exc:
        raise ValueError("Ollama не запущена. Откройте Ollama и повторите создание сценариев.") from exc
    except TimeoutError as exc:
        raise ValueError("Локальная модель не ответила за три минуты. Сократите описание и повторите.") from exc
    try:
        generated = json.loads(result["message"]["content"])
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Локальная модель вернула некорректный список сценариев. Повторите генерацию.") from exc
    items = normalize_ai_search_scenarios(generated)
    input_tokens = int(result.get("prompt_eval_count", 0) or 0)
    output_tokens = int(result.get("eval_count", 0) or 0)
    return items, {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


def extract_response_text(response: dict[str, Any]) -> str:
    for output in response.get("output", []):
        for content in output.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return str(content["text"])
    raise ValueError("Модель не вернула текст письма.")


def normalize_evidence(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def evidence_terms(value: str) -> set[str]:
    words = re.findall(r"[A-Za-zА-Яа-яЁё0-9+#.-]{3,}", normalize_evidence(value))
    terms = set()
    for word in words:
        cleaned = word.strip(".,;:()[]{}").lower()
        if cleaned in STOPWORDS:
            continue
        terms.add(cleaned if re.search(r"[a-z0-9+#]", cleaned) else cleaned[:5])
    return terms


def sanitize_external_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-zА-Яа-я]{2,}\b", " ", text)
    text = re.sub(r"https?://\S+|www\.\S+", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<!\w)@[A-Za-zА-Яа-я0-9_.-]{3,}", " ", text)
    text = re.sub(r"(?<!\d)(?:\+?7|8)[\s()\-]*\d{3}[\s()\-]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}(?!\d)", " ", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def select_relevant_excerpts(value: Any, vacancy_text: str, max_chars: int) -> str:
    text = sanitize_external_text(value)
    if len(text) <= max_chars:
        return text
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n|(?<=\.)\s+(?=[А-ЯЁA-Z])", text) if chunk.strip()]
    vacancy_terms = evidence_terms(vacancy_text)
    action_markers = (
        "координир", "организ", "подготов", "обработ", "контрол", "анализ", "разработ",
        "созда", "отслеж", "реш", "соглас", "запуст", "реализ", "исслед", "провел", "провёл",
    )
    ranked = []
    for index, chunk in enumerate(chunks):
        chunk_terms = evidence_terms(chunk)
        overlap = len(chunk_terms & vacancy_terms)
        action_score = sum(marker in chunk.lower() for marker in action_markers)
        number_score = min(12, len(re.findall(r"\b\d+(?:[.,]\d+)?%?\b", chunk)) * 3)
        ranked.append((overlap * 6 + action_score * 3 + number_score, index, chunk))
    selected = []
    used = 0
    for _score, index, chunk in sorted(ranked, key=lambda item: (-item[0], item[1])):
        if used + len(chunk) + 2 > max_chars:
            continue
        selected.append((index, chunk))
        used += len(chunk) + 2
    return "\n\n".join(chunk for _index, chunk in sorted(selected))[:max_chars]


def select_quantified_achievements(value: Any, vacancy_text: str, max_chars: int = 2_200) -> str:
    """Return the strongest measurable results from work history for the letter prompt."""
    text = sanitize_external_text(value)
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n|(?<=\.)\s+(?=[А-ЯЁA-Z])", text) if chunk.strip()]
    vacancy_terms = evidence_terms(vacancy_text)
    action_markers = (
        "координир", "организ", "обработ", "контрол", "анализ", "разработ", "созда",
        "собрал", "подготов", "запуст", "увелич", "сниз", "провел", "провёл",
    )
    ranked = []
    for index, chunk in enumerate(chunks):
        numeric_matches = re.findall(r"\b\d+(?:[.,]\d+)?(?:%|\+)?\b", chunk)
        if not numeric_matches:
            continue
        chunk_terms = evidence_terms(chunk)
        overlap = len(chunk_terms & vacancy_terms)
        action_score = sum(marker in chunk.lower() for marker in action_markers)
        # Сначала релевантность вакансии, затем измеримый масштаб и конкретное действие.
        ranked.append((overlap * 8 + min(18, len(numeric_matches) * 5) + action_score * 4, index, chunk))
    selected = []
    used = 0
    for _score, index, chunk in sorted(ranked, key=lambda item: (-item[0], item[1])):
        if used + len(chunk) + 2 > max_chars:
            continue
        selected.append((index, chunk))
        used += len(chunk) + 2
    return "\n\n".join(chunk for _index, chunk in sorted(selected))[:max_chars]


def letter_concepts(value: Any) -> set[str]:
    """Map differently worded text to a compact, explainable set of work concepts."""
    text = normalize_evidence(str(value or ""))
    return {
        concept
        for concept, markers in LETTER_CONCEPTS.items()
        if any(marker in text for marker in markers)
    }


def split_experience_facts(value: Any) -> list[str]:
    """Keep source fragments intact, so a selected achievement can always be verified."""
    text = sanitize_external_text(value)
    chunks = [
        chunk.strip(" -•\t")
        for chunk in re.split(r"\n\s*\n|\n(?=[•\-–—])|(?<=\.)\s+(?=[А-ЯЁA-Z])", text)
        if chunk.strip(" -•\t")
    ]
    # A CV sometimes has a whole job in one paragraph. Split only excessively long
    # fragments, preserving sentences as the evidence quote.
    expanded: list[str] = []
    for chunk in chunks:
        if len(chunk) > 900:
            expanded.extend(part.strip() for part in re.split(r"(?<=\.)\s+", chunk) if len(part.strip()) >= 40)
        else:
            expanded.append(chunk)
    return expanded[:80]


def classify_experience_record(source: str) -> tuple[str, str]:
    """Return an honest label and a non-negotiable wording rule for an experience block."""
    lowered = normalize_evidence(source)
    source_label = normalize_evidence(str(source).splitlines()[0] if str(source).splitlines() else source)
    if "oasis" in source_label:
        return "коммерческий опыт", "Можно называть работой и коммерческим опытом."
    if "solutions" in lowered or "independent project" in lowered:
        return "самостоятельное исследование", "Называть самостоятельным исследованием, не работой в компании."
    if any(marker in lowered for marker in ("хакатон", "business battle", "кейс-чемпионат", "лицей", "ростелеком", "alfa bank", "калининград")):
        return "учебный хакатон/кейс", "Обязательно называть хакатоном, кейсом или учебным проектом; не называть работой в компании."
    return "проектная работа", "Называть проектной работой; не заявлять коммерческий результат команды как личный."


def build_experience_records(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize the CV into whole, non-mixable experience records.

    A record is the atomic source for a cover letter: one source, personal actions,
    results, and wording constraints travel together.
    """
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw_line in str(profile.get("work_history") or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r"^(?:\d{2}[./]\d{4}|\d{4})", line) and current:
            blocks.append(current)
            current = []
        current.append(line)
    if current:
        blocks.append(current)

    records: list[dict[str, Any]] = []
    for index, lines in enumerate(blocks, start=1):
        source_label = lines[0]
        project_lines = [line for line in lines[1:] if normalize_evidence(line).startswith(("проект", "заказчик", "направление"))]
        actions = [line.lstrip("-•–— ") for line in lines[1:] if line.startswith(("-", "•", "–", "—"))]
        results = [line for line in lines if normalize_evidence(line).startswith("результат")]
        # Preserve the complete block as a verifiable source, but use concise fields
        # for the model prompt.
        source_text = "\n".join(lines)
        experience_type, constraint = classify_experience_record(source_text)
        if not actions and not results:
            continue
        record_text = "\n".join([
            f"Источник: {source_label}",
            *(project_lines[:2]),
            f"Тип опыта: {experience_type}",
            "Что делал лично: " + "; ".join(actions[:6]),
            "Результат: " + "; ".join(results[:2] or actions[-1:]),
            f"Ограничение формулировки: {constraint}",
        ])
        records.append({
            "id": f"experience-{index}",
            "source_label": source_label,
            "experience_type": experience_type,
            "what_did": actions[:8],
            "results": results[:3],
            "constraint": constraint,
            "source_text": source_text[:5_000],
            "quote": record_text[:2_500],
            "concepts": sorted(letter_concepts(source_text)),
            "numbers": re.findall(r"\b\d+(?:[.,]\d+)?(?:%|\+)?\b", source_text)[:12],
        })
    return records


def build_fact_cards(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Expose whole experience records as the only selectable proof cards."""
    return [{**record, "has_action": bool(record["what_did"])} for record in build_experience_records(profile)]


def build_vacancy_requirements(vacancy: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract employer expectations into explainable semantic requirement cards."""
    text = "\n".join((str(vacancy.get("title") or ""), str(vacancy.get("description") or "")))
    fragments = split_experience_facts(text)
    requirements: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for fragment in fragments:
        concepts = sorted(letter_concepts(fragment))
        if not concepts:
            continue
        key = tuple(concepts)
        if key in seen:
            continue
        seen.add(key)
        lowered = normalize_evidence(fragment)
        priority = 3 if any(marker in lowered for marker in ("обязан", "требован", "необходим", "обязател")) else 2
        requirements.append({"text": fragment[:500], "concepts": concepts, "priority": priority})
    # The title represents the primary purpose even when the description is short.
    title_concepts = sorted(letter_concepts(str(vacancy.get("title") or "")))
    if title_concepts and tuple(title_concepts) not in seen:
        requirements.insert(0, {"text": str(vacancy.get("title") or "")[:500], "concepts": title_concepts, "priority": 3})
    return requirements[:7]


def build_letter_evidence_plan(profile: dict[str, Any], vacancy: dict[str, Any]) -> dict[str, Any]:
    """Select 2–3 source-backed facts before text generation; no extra LLM request."""
    requirements = build_vacancy_requirements(vacancy)
    cards = build_fact_cards(profile)
    vacancy_terms = evidence_terms("\n".join(str(item["text"]) for item in requirements))
    ranked: list[tuple[int, int, dict[str, Any], list[str]]] = []
    for index, card in enumerate(cards):
        card_terms = evidence_terms(card["quote"])
        matched: list[str] = []
        score = 0
        for requirement in requirements:
            overlap = set(card["concepts"]) & set(requirement["concepts"])
            if overlap:
                matched.append(requirement["text"])
                score += len(overlap) * requirement["priority"] * 12
        score += len(card_terms & vacancy_terms) * 3
        score += min(16, len(card["numbers"]) * 6)
        score += 5 if card["has_action"] else 0
        if score:
            ranked.append((score, index, card, matched[:3]))

    selected: list[dict[str, Any]] = []
    used_concepts: set[str] = set()
    for score, _index, card, matched in sorted(ranked, key=lambda item: (-item[0], item[1])):
        # Prefer different evidence types, but do not discard a very strong numeric fact.
        fresh_concepts = set(card["concepts"]) - used_concepts
        if selected and not fresh_concepts and not card["numbers"]:
            continue
        selected.append({
            **card,
            "score": score,
            "matches": matched,
        })
        used_concepts.update(card["concepts"])
        if len(selected) == 3:
            break
    return {"requirements": requirements, "selected_facts": selected}


def build_ai_request(profile: dict[str, Any], vacancy: dict[str, Any]) -> tuple[dict[str, str], dict[str, str], dict[str, Any], str]:
    vacancy_payload = {
        "title": str(vacancy.get("title", "")),
        "company": str(vacancy.get("company", "")),
        "description": sanitize_external_text(vacancy.get("description", ""))[:14_000],
    }
    vacancy_context = "\n".join(vacancy_payload.values())
    profile_payload = {
        field: (str(profile.get(field, "")) if field == "name" else sanitize_external_text(profile.get(field, "")))[:14_000]
        for field in PROFILE_FIELDS
    }
    evidence_plan = build_letter_evidence_plan(profile, vacancy)
    # Do not show the writer a long raw CV: it is the main cause of mixing a result
    # from one project with the name of another. Only selected whole records are facts.
    profile_payload["work_history"] = "Для письма используй только profile.approved_facts ниже."
    profile_payload["resume_text"] = "Не используй как источник новых кейсов или цифр."
    profile_payload["quantified_achievements"] = "Числа разрешены только внутри выбранных approved_facts."
    # JSON is deliberately passed as text: it remains part of the verified source
    # corpus and Qwen receives an explicit, compact plan instead of rediscovering
    # facts in thousands of characters of CV text.
    profile_payload["approved_facts"] = json.dumps(
        evidence_plan["selected_facts"], ensure_ascii=False
    )
    vacancy_payload["employer_requirements"] = json.dumps(
        evidence_plan["requirements"], ensure_ascii=False
    )
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "letter": {"type": "string"},
            "evidence": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "requirement": {"type": "string"},
                        "claim": {"type": "string"},
                        "quote": {"type": "string"},
                    },
                    "required": ["requirement", "claim", "quote"],
                },
            },
            "uncovered_requirements": {
                "type": "array", "maxItems": 6, "items": {"type": "string"}
            },
        },
        "required": ["letter", "evidence", "uncovered_requirements"],
    }
    instruction = (
        "Ты пишешь короткое персональное сопроводительное письмо только на русском языке от первого лица. "
        "Английские названия компании, должности или инструмента допустимы лишь как отдельные собственные названия; "
        "не пиши английские предложения или абзацы. "
        "Сначала молча проанализируй вакансию и профиль, но НИКОГДА не показывай ход анализа, оценку совпадения "
        "или названия полей профиля в тексте письма. Используй только подтвержденные факты кандидата.\n\n"
        "ОБЯЗАТЕЛЬНЫЙ ВНУТРЕННИЙ ЧЕКЛИСТ ПЕРЕД НАПИСАНИЕМ (результаты анализа не показывай):\n"
        "1. Определи уровень роли: internship/junior/middle/senior/lead; требуемые годы и коммерческий или отраслевой "
        "опыт; ответственность за людей, бюджет, сроки, качество или P&L; обязательное образование, сертификаты и hard skills.\n"
        "2. Оцени соответствие кандидата: полное, большей частью, частичное, заметно ниже или отсутствует. Не маскируй "
        "существенный гэп. При умеренном гэпе покажи сильный переносимый опыт без оправданий; при большом — честно обозначь "
        "меньший опыт или предложи рассмотреть junior/смежную роль.\n"
        "3. Выдели 5-7 ключевых требований вакансии и мысленно пометь каждое как критичное, важное или дополнительное. "
        "Для каждого проверь: есть ли подтверждение, какой конкретный эпизод его подтверждает и насколько сильное совпадение.\n"
        "4. Сформулируй одну центральную идею: почему кандидата стоит рассмотреть именно на эту роль. Затем выбери заново "
        "для этой вакансии 2-3 наиболее сильных кейса; не используй привычный набор проектов автоматически.\n"
        "5. В каждом кейсе различай личный и командный вклад и используй схему контекст → действие кандидата → подтвержденный "
        "масштаб/цифра → результат. Не превращай интерес в опыт, учебный кейс в коммерческий, участие в руководство, "
        "командный результат в личный, знакомство с инструментом во владение. Неподтвержденные цифры запрещены.\n"
        "ПЛАН ДОКАЗАТЕЛЬСТВ — ГЛАВНЫЙ ИСТОЧНИК ДЛЯ КЕЙСОВ: поле profile.approved_facts содержит 2–3 факта, которые "
        "бот уже сопоставил с ожиданиями работодателя из vacancy.employer_requirements. Это не подсказка для пересказа, "
        "а утверждённые исходные данные: выбери из них один-два наиболее естественных факта и используй их смысл и цифры "
        "в письме. Не добавляй других чисел и не приписывай факту результат, которого нет в quote. НЕЛЬЗЯ соединять "
        "source_label одного факта, действие или результат другого факта. Если approved_facts пуст, честно напиши короткое "
        "письмо без кейса, не используй work_history и resume_text как запасной источник.\n"
        "УПОМИНАНИЕ ИСТОЧНИКА: если называешь организацию, проект или период, копируй их только из source_label того же "
        "approved_fact, чьи действия и результат описываешь. Не упоминай название другого места работы даже как вводную.\n"
        "СТАТУС ОПЫТА: у каждого approved_facts есть experience_type. Если это «учебный хакатон/кейс», обязательно "
        "называй его в письме хакатоном, кейсом или учебным проектом; не представляй как работу в компании, коммерческий "
        "проект или занимаемую должность. Не пиши «в течение последних лет», если факты относятся к отдельным проектам.\n"
        "ЧИСЛА И РЕЗУЛЬТАТЫ — ПРИОРИТЕТ: поле profile.quantified_achievements содержит подтверждённые измеримые факты "
        "из опыта кандидата. Если среди них есть факт, релевантный ключевой задаче вакансии, обязательно используй в письме "
        "хотя бы один такой факт, а при естественном изложении — два. Предпочитай его общим словам «есть опыт», «умею работать "
        "с многозадачностью» и «накопил опыт». Встраивай цифры как доказательство в рассказ о кейсе, а не отдельным списком. "
        "Не вставляй показатель только ради числа: он должен объяснять, почему опыт подходит задачам работодателя.\n"
        "6. Используй терминологию вакансии только когда она соответствует реальному опыту. Для неродной отрасли объясни "
        "переносимость опыта. Для AI различай использование инструментов, создание агентов, управление AI/ML-проектом и ML-разработку. "
        "Для PM не заявляй полный цикл без подтверждений; для аналитики ищи источник и объем данных, метод, инструмент, вывод и решение.\n"
        "7. Удали каждый абзац, который не отвечает ожиданию работодателя. Баланс: примерно 70-80% конкретных задач и результатов, "
        "20-30% мотивации и характера. Письмо объясняет релевантность опыта, а не повторяет резюме.\n"
        "8. Перед ответом проверь: ясны ли роль и адресная мотивация; есть ли конкретный кейс, масштаб или результат; "
        "подтвержден ли каждый сильный тезис; нет ли выдумок, замаскированного гэпа и пересказа CV; естественен ли язык; "
        "понятно ли, зачем приглашать кандидата. Если провалены три и более пункта — перепиши письмо.\n\n"
        "«Уважаемые коллеги», «Команда TEKTA GROUP» и других обращений к компании. Не пиши отдельные абзацы о том, "
        "чего кандидат не хочет: «я не хочу заниматься рутиной», «не хочу быть на подхвате», «не люблю бюрократию», "
        "«не рассматриваю…». Такие ограничения не помогают работодателю принять решение. Если важно показать мотивацию, "
        "сформулируй её позитивно и конкретно через задачи, ответственность и тип проектов, которые привлекают кандидата.\n\n"
        "ДЕЛОВОЙ ТОН: после строки «Здравствуйте!» сразу переходи к роли, задаче или продукту. Не добавляй второе "
        "обращение: «Уважаемые коллеги», «Уважаемый HR-специалист», «Команда TEKTA GROUP» и подобные формулы запрещены. "
        "Никогда не используй гендерные шаблоны с вариантами в скобках: «уверен(а)», «занимал(а)» и т. п. Пиши в мужском "
        "роде, так как кандидат — Александр. Не пиши отдельные абзацы о том, чего кандидат не хочет: «я не хочу заниматься "
        "рутиной», «не хочу быть на подхвате», «не люблю бюрократию», «не рассматриваю…». Такие ограничения не помогают "
        "работодателю принять решение. Если важно показать мотивацию, сформулируй её позитивно и конкретно через задачи, "
        "ответственность и тип проектов, которые привлекают кандидата.\n\n"
        "«Уважаемые коллеги», «Команда TEKTA GROUP» и других обращений к компании. Не пиши отдельные абзацы о том, "
        "чего кандидат не хочет: «я не хочу заниматься рутиной», «не хочу быть на подхвате», «не люблю бюрократию», "
        "«не рассматриваю…». Такие ограничения не помогают работодателю принять решение. Если важно показать мотивацию, "
        "сформулируй её позитивно и конкретно через задачи, ответственность и тип проектов, которые привлекают кандидата.\n\n"
        "СТИЛЕВЫЕ ОРИЕНТИРЫ (их факты и названия НЕЛЬЗЯ переносить в новое письмо):\n"
        "1. «Здравствуйте! Хочу предложить свою кандидатуру на роль Project Manager в Софи. Мне близка идея "
        "продукта: автоматизация поиска работы решает понятную задачу, поэтому мне было бы интересно участвовать "
        "в развитии сервиса. В проектной работе я координировал задачи, структурировал решения и готовил требования. "
        "Мне интересна небольшая продуктовая команда, где нужно быстро разбираться в задачах и двигать продукт от "
        "идеи до релиза. Буду рад обсудить, чем могу быть полезен вашей команде».\n"
        "2. «Здравствуйте! Хочу предложить свою кандидатуру на стажировку в команду доставки. Мне интересны проекты "
        "на стыке логистики, аналитики и продукта. В небольшой компании я координировал отправки, общался с клиентами "
        "и отслеживал статусы заказов. Также в учебном проекте работал над аналитикой выхода бизнеса в новый регион. "
        "Мне близки задачи, где нужно соединять данные, рынок и практическое решение».\n\n"
        "Повторяй не слова ориентиров, а их качество: адресная мотивация, связное развитие мысли, конкретный опыт и "
        "спокойный человеческий тон. Если из вакансии понятны продукт, миссия или тип задач, коротко объясни, почему "
        "они интересны кандидату. Если таких данных нет, говори об интересе к задачам роли и ничего не выдумывай. "
        "Не цитируй резюме и не объясняй работодателю механику сопоставления. Соединяй факты переходами по смыслу, "
        "а не шаблонными выводами после каждого предложения.\n\n"
        "ПРИОРИТЕТ РАБОТОДАТЕЛЯ: из выделенных требований выбери 2-4 главных ожидания работодателя — задачи, "
        "требуемый опыт, навыки и особенности продукта или команды. Строй письмо как содержательный ответ именно "
        "на эти ожидания в порядке их важности. Из опыта кандидата выбирай только наиболее подходящие доказательства; "
        "не пытайся пересказать всю биографию и не подменяй требования работодателя общими стремлениями кандидата.\n\n"
        "КОНКРЕТИКА: письмо обязано содержать хотя бы один реальный эпизод из опыта кандидата с действием "
        "в прошедшем времени: что именно он координировал, организовал, подготовил, обработал, проверил, "
        "проанализировал или создал. Если в подтвержденном эпизоде есть число или измеримый результат, сохрани его. "
        "Не заменяй опыт рассуждениями о том, что кандидат любит, хочет, готов или умеет.\n\n"
        "КОМПОЗИЦИЯ: обязательно начни отдельной строкой «Здравствуйте!», затем напиши 6-9 законченных предложений "
        "в 3-5 естественных абзацах, разделенных пустой строкой. Не склеивай все письмо в один абзац. Первый "
        "содержательный абзац — точная роль, "
        "компания и содержательная мотивация. Затем связно раскрой 1-2 наиболее релевантных эпизода: контекст, "
        "действия кандидата и связь с будущими задачами. Отдельным коротким абзацем можно показать, какой формат "
        "работы или направление особенно интересны кандидату. Не превращай письмо в блоки «факт — доказательство — "
        "польза» и не объясняй каждое совпадение отдельно. Варьируй начало: "
        "«Меня заинтересовала позиция...», «Хочу предложить свою кандидатуру на роль...», «Буду рад присоединиться "
        "к команде ... в роли...». Следующие 2-3 предложения — "
        "первый релевантный проект, конкретные действия и осторожно сформулированная польза. Еще 1-2 предложения — "
        "второй релевантный опыт или инструменты и их польза. Предпоследнее — приглашение обсудить опыт. Последняя "
        "строка — «С уважением, Имя Фамилия». Не ужимай содержательную часть до одного предложения.\n\n"
        "ЗАПРЕЩЕННЫЕ ФРАЗЫ И КОНСТРУКЦИИ: «я откликаюсь на вакансию», «я откликаюсь на позицию», "
        "«откликаюсь на вакансию», «откликнулся на вакансию», «я кандидат на позицию», «резюме на позицию», «в моем профиле указано», "
        "«также указано», «это соответствует требованию», «что подтверждает мои навыки», «демонстрирует способность», "
        "кавычки вокруг фрагментов резюме, перечисление требований вакансии и фразы о том, что что-либо указано в данных. "
        "Не используй канцелярские связки «Это помогло мне понять», «что позволило мне лучше понять», "
        "«многие из предложенных мною концепций». Не начинай абзацы одинаково, не повторяй название позиции и не повторяй одно смысловое слово дважды в "
        "одном предложении. Не пиши «Меня зовут», «Уважаемые коллеги», «очень заинтересован», «мне подходит роль», «спасибо за внимание», "
        "«если получу шанс» и «в вашей компании». Никогда не используй плейсхолдеры в квадратных скобках, "
        "HTML-сущности и вымышленные данные. Избегай пластиковых GPT-оборотов: «динамичная среда», «на стыке X и Y», "
        "«реальное влияние на бизнес», «комплексный подход», «эффективно взаимодействовать», «успешно реализовал», "
        "«внести вклад в развитие», «разделяю ценности компании». Формулировки «мне близки задачи» и «хочу развиваться» "
        "используй только если без них нельзя выразить конкретную мотивацию. Имя уже передано в profile.name.\n\n"
        "Можно творчески формулировать мотивацию, переходы, будущую пользу и тон письма. При этом не выдумывай "
        "стаж, должности, работодателей, выполненные задачи, результаты, цифры и уровень владения инструментами. "
        "Не называй учебный кейс полноценным коммерческим опытом и не заявляй управление командой, если в профиле "
        "описано только участие. Не приписывай прошлому опыту неподтвержденные последствия через «что позволило мне», "
        "«благодаря этому я достиг» или «это обеспечило». Объясняй только будущую пользу осторожными формулировками: "
        "«этот опыт поможет», «может быть полезно», «позволит быстрее включиться». Упоминай не более трех инструментов. "
        "Ориентир по длине — около 2 000 символов с пробелами, обычно в диапазоне 1 500-2 300 символов. "
        "Это не требование искусственно растягивать текст: если для точного ответа на вакансию достаточно меньшего объема, "
        "пиши короче. Абсолютный технический лимит — 10 000 символов с пробелами; превышать его нельзя. "
        "Не добавляй воду ради объема и не повторяй уже высказанные мысли. Не обязательно подтверждать evidence каждое оценочное или мотивационное предложение; "
        "evidence нужен только для конкретных утверждений об опыте кандидата. "
        "В подписи используй только значение поля name, не извлекай другое имя из резюме.\n\n"
        "Для технического поля evidence выбери 2-3 самых сильных факта и приложи к каждому короткую цитату или "
        "максимально близкий фрагмент профиля. Не пересказывай в evidence весь опыт кандидата. "
        "Evidence не является частью письма. Если подтверждения нет, занеси требование в uncovered_requirements.\n\n"
        "Верни только JSON-объект без Markdown и пояснений: letter — строка письма; evidence — массив объектов "
        "с полями requirement, claim и quote; uncovered_requirements — массив строк."
    )
    tier = str(vacancy.get("generation_tier") or "short")
    if tier == "deep":
        instruction += (
            "\n\nРЕЖИМ ГЛУБОКОГО ПИСЬМА: эта вакансия вошла в лучшие. Напиши 1 200–1 800 символов, "
            "свяжи два разных approved_facts с двумя ожиданиями работодателя. Хотя бы один факт должен содержать "
            "релевантную цифру, если она есть в approved_facts."
        )
    else:
        instruction += (
            "\n\nРЕЖИМ МАССОВОГО ПИСЬМА: напиши 700–1 100 символов. Используй одну главную связку "
            "«задача работодателя → подтверждённый факт кандидата», не пересказывай резюме и не добавляй второй кейс "
            "ради объёма."
        )
    return profile_payload, vacancy_payload, schema, instruction


BANNED_LETTER_PHRASES = (
    "я откликаюсь на вакансию",
    "я откликаюсь на позицию",
    "откликаюсь на вакансию",
    "откликнулся на вакансию",
    "я кандидат на позицию",
    "резюме на позицию",
    "в моем профиле указано",
    "в моём профиле указано",
    "также указано",
    "это соответствует требованию",
    "что подтверждает мои навыки",
    "демонстрирует способность",
    "это помогло мне понять",
    "что позволило мне лучше понять",
    "многие из предложенных мною концепций",
    "меня зовут",
    "уважаемые коллеги",
    "уважаемый hr-специалист",
    "hr-специалист(а)",
    "после тщательного изучения",
    "после тщательного анализа",
    "я уверен(а)",
    "я уверен, что",
    "занимал(а)",
    "благодарю за внимание",
    "соответствуют требованиям вакансии",
    "в течение последних лет",
    "я не хочу",
    "не хочу быть на подхвате",
    "не люблю бюрократию",
    "очень заинтересован",
    "мне подходит роль",
    "спасибо за внимание",
    "если получу шанс",
    "в вашей компании",
)

HARD_LETTER_ISSUES = {
    "письмо должно начинаться отдельной строкой «Здравствуйте!»",
    "обнаружен плейсхолдер в квадратных скобках",
    "обнаружена HTML-сущность",
    "письмо превышает лимит 10 000 символов",
    "нет подписи",
    "в подписи отсутствует имя из профиля",
    "письмо написано преимущественно на английском языке",
    "я уверен(а)", "занимал(а)", "hr-специалист(а)",
}


CONCRETE_EXPERIENCE_PATTERNS = (
    r"\bкоординировал[аи]?\b",
    r"\bорганизовал[аи]?\b",
    r"\bподготовил[аи]?\b",
    r"\bобработал[аи]?\b",
    r"\bпроверил[аи]?\b",
    r"\bпроанализировал[аи]?\b",
    r"\bразработал[аи]?\b",
    r"\bсоздал[аи]?\b",
    r"\bконтролировал[аи]?\b",
    r"\bсопровождал[аи]?\b",
    r"\bвзаимодействовал[аи]?\b",
    r"\bпров[её]л[аи]?\b",
    r"\bсоставил[аи]?\b",
    r"\bнастроил[аи]?\b",
    r"\bотслеживал[аи]?\b",
    r"\bрешил[аи]?\b",
    r"\bготовил[аи]?\b",
    r"\bсобрал[аи]?\b",
    r"\bоформил[аи]?\b",
    r"\bсогласовал[аи]?\b",
    r"\bзапустил[аи]?\b",
    r"\bреализовал[аи]?\b",
    r"\bисследовал[аи]?\b",
    r"\bулучшил[аи]?\b",
    r"\bснизил[аи]?\b",
    r"\bувеличил[аи]?\b",
    r"\bучаствовал[аи]?\b",
    r"\bпомог(?:ла|ли)?\b",
    r"\bв[её]л[аи]?\b",
)


def normalize_generated_letter(letter: str, expected_name: str = "") -> str:
    normalized = html.unescape(str(letter or "")).strip()
    clean_name = str(expected_name or "").strip()
    # Убираем безопасные шаблонные вводные, которые иногда добавляет локальная модель.
    normalized = re.sub(
        r"(?im)^\s*(?:уважаемые коллеги|уважаем(?:ый|ая)(?:\([^\n)]*\))?\s+hr[^\n]*|команда\s+)[^\n]*\s*$",
        "", normalized,
    )
    normalized = re.sub(r"(?im)^\s*меня зовут[^.!?\n]*[.!?]\s*", "", normalized)
    # Локальная модель иногда оставляет служебный шаблон вроде [название компании].
    # Он не является фактом кандидата: безопаснее убрать его, чем потерять всё письмо.
    normalized = re.sub(r"\[[^\]\n]{1,100}\]", "", normalized)
    normalized = re.sub(r"(?i)\bздравствуйте!\s*", "", normalized)
    normalized = "Здравствуйте!\n\n" + normalized.strip()
    normalized = re.sub(r"(?i)\b(?:спасибо|благодарю) за внимание(?: к моему резюме)?[.!?]?\s*", "", normalized)
    normalized = re.sub(r"(?i)\bздравствуйте!\s*", "", normalized)
    normalized = re.sub(r"\b([А-Яа-яЁё]+)\([а-яё]+\)", r"\1", normalized)
    normalized = re.sub(r"[ \t]{2,}", " ", normalized)
    normalized = re.sub(r"(?:\s*с уважением\b[^\n]*)+\s*$", "", normalized, flags=re.IGNORECASE)
    normalized = "Здравствуйте!\n\n" + normalized.strip()
    normalized = re.sub(r"(?i)\bздравствуйте!\s*", "", normalized)
    normalized = "Здравствуйте!\n\n" + normalized.strip()
    if clean_name:
        normalized = re.sub(r"\[\s*ваше\s+имя\s*\]", clean_name, normalized, flags=re.IGNORECASE)
    if clean_name:
        signature = f"С уважением, {clean_name}"
        normalized = re.sub(r"(?:\n\s*с уважением\b[^\n]*)+\s*$", "", normalized, flags=re.IGNORECASE)
        normalized = f"{normalized.rstrip()}\n\n{signature}"
    return normalized.strip()


def letter_style_issues(letter: str, expected_name: str = "") -> list[str]:
    lowered = normalize_evidence(letter)
    issues = [phrase for phrase in BANNED_LETTER_PHRASES if phrase in lowered]
    first_line = next((line.strip() for line in letter.splitlines() if line.strip()), "")
    if first_line != "Здравствуйте!":
        issues.append("письмо должно начинаться отдельной строкой «Здравствуйте!»")
    if re.search(r"\[[^\]\n]{1,100}\]", letter):
        issues.append("обнаружен плейсхолдер в квадратных скобках")
    if re.search(r"&(?:#x?[0-9a-f]+|[a-z]+);", letter, re.IGNORECASE):
        issues.append("обнаружена HTML-сущность")
    word_count = len(re.findall(r"[A-Za-zА-Яа-яЁё0-9+#.-]+", letter))
    if word_count < 70:
        issues.append("слишком короткое письмо")
    if len(letter) > 10_000:
        issues.append("письмо превышает лимит 10 000 символов")
    if "с уважением" not in lowered:
        issues.append("нет подписи")
    clean_name = normalize_evidence(expected_name)
    if clean_name and not re.search(rf"с уважением\s*,?\s*{re.escape(clean_name)}\s*$", lowered):
        issues.append("в подписи отсутствует имя из профиля")
    # Названия компаний, ролей и инструментов могут быть на латинице, но само
    # сопроводительное письмо должно быть русским. Полностью английский ответ
    # нельзя тихо сохранить только потому, что в нём есть русское приветствие.
    cyrillic_letters = len(re.findall(r"[А-Яа-яЁё]", letter))
    latin_letters = len(re.findall(r"[A-Za-z]", letter))
    if latin_letters > 80 and latin_letters > cyrillic_letters * 0.45:
        issues.append("письмо написано преимущественно на английском языке")
    # Наличие конкретного действия задаётся промптом и проверяется в evidence,
    # но не должно блокировать сохранение письма из-за особенностей формулировки Qwen.
    return issues


def vacancy_has_full_description(vacancy: dict[str, Any]) -> bool:
    description = normalize_evidence(str(vacancy.get("description", "")))
    content_terms = evidence_terms(description)
    interface_words = {
        "сейчас", "смотрят", "человек", "опыт", "откликнуться", "добавляю", "отзыва", "вакансия",
    }
    meaningful_terms = content_terms - {word[:5] for word in interface_words}
    has_sections = any(marker in description for marker in ("обязан", "требован", "задач", "необходимо"))
    return len(description) >= 300 and len(meaningful_terms) >= 12 and has_sections


def validate_ai_letter(
    generated: dict[str, Any], profile_payload: dict[str, str], vacancy_payload: dict[str, str] | None = None
) -> tuple[str, list[dict[str, str]]]:
    letter = str(generated.get("letter", "")).strip()
    evidence = generated.get("evidence") or []
    profile_corpus = normalize_evidence("\n".join(profile_payload.values()))
    profile_terms = evidence_terms(profile_corpus)
    checked_evidence = []
    for item in evidence:
        quote = str(item.get("quote", "")).strip()
        normalized_quote = normalize_evidence(quote)
        quote_terms = evidence_terms(quote)
        overlap = len(quote_terms & profile_terms) / max(1, len(quote_terms))
        if len(quote) >= 8 and normalized_quote in profile_corpus:
            verification = "exact"
            note = "Точная цитата из профиля"
        elif len(quote_terms) >= 2 and overlap >= 0.6:
            verification = "close"
            note = "Близкий пересказ: проверьте формулировку"
        else:
            verification = "warning"
            note = "Источник не найден дословно: проверьте утверждение"
        checked_evidence.append({
            "requirement": str(item.get("requirement", "")).strip(),
            "claim": str(item.get("claim", "")).strip(),
            "quote": quote,
            "verification": verification,
            "note": note,
        })
    if len(letter) < 150:
        raise ValueError("ИИ вернул слишком короткое письмо. Запустите генерацию повторно.")
    if "письмо написано преимущественно на английском языке" in letter_style_issues(
        letter, profile_payload.get("name", "")
    ):
        raise ValueError("ИИ вернул сопроводительное письмо преимущественно на английском языке. Перегенерируйте его.")

    allowed_corpus = normalize_evidence(
        "\n".join([*profile_payload.values(), *(vacancy_payload or {}).values()])
    )
    allowed_numbers = set(re.findall(r"\b\d+(?:[.,]\d+)?%?\b", allowed_corpus))
    new_numbers = sorted(set(re.findall(r"\b\d+(?:[.,]\d+)?%?\b", letter)) - allowed_numbers)
    allowed_latin = {term for term in evidence_terms(allowed_corpus) if re.search(r"[a-z]", term)}
    letter_latin = {term for term in evidence_terms(letter) if re.search(r"[a-z]", term)}
    common_latin = {"product", "manager", "project", "team", "career", "bot"}
    new_latin = sorted(letter_latin - allowed_latin - common_latin)
    if new_numbers or new_latin:
        details = []
        if new_numbers:
            details.append("новые числа: " + ", ".join(new_numbers))
        if new_latin:
            details.append("новые названия/инструменты: " + ", ".join(new_latin))
        checked_evidence.append({
            "requirement": "Автоматическая проверка новых деталей",
            "claim": "; ".join(details),
            "quote": "Эти элементы не найдены в профиле или вакансии.",
            "verification": "warning",
            "note": "Перед использованием письма проверьте или удалите эти детали",
        })
    return letter, checked_evidence


def generate_ai_letter(
    profile: dict[str, Any], vacancy: dict[str, Any], api_key: str, model: str
) -> tuple[str, list[dict[str, str]], dict[str, int]]:
    profile_payload, vacancy_payload, schema, instruction = build_ai_request(profile, vacancy)
    request_payload = {
        "model": model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": instruction}]},
            {
                "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": json.dumps(
                        {"profile": profile_payload, "vacancy": vacancy_payload}, ensure_ascii=False
                    ),
                }],
            },
        ],
        "text": {"format": {"type": "json_schema", "name": "career_cover_letter", "strict": True, "schema": schema}},
    }
    request = Request(
        OPENAI_API_BASE,
        data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": f"CareerBot/{APP_VERSION}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        error_code = ""
        try:
            error_payload = json.loads(exc.read().decode("utf-8")).get("error", {})
            details = str(error_payload.get("message", ""))
            error_code = str(error_payload.get("code", ""))
        except (json.JSONDecodeError, UnicodeDecodeError):
            details = ""
        if exc.code == 429 and (
            "no credits" in details.lower()
            or "quota" in details.lower()
            or error_code in {"insufficient_quota", "billing_hard_limit_reached"}
        ):
            raise ValueError(
                "На балансе OpenAI API нет средств. Пополните баланс в разделе Billing платформы OpenAI "
                "и повторите генерацию через несколько минут."
            ) from exc
        raise ValueError(f"OpenAI API вернул ошибку {exc.code}. {details}".strip()) from exc
    except URLError as exc:
        reason = exc.reason
        winerror = getattr(reason, "winerror", None)
        if winerror == 10013:
            raise ValueError(
                "Windows запретила серверу доступ в интернет. Остановите Career Bot и запустите его "
                "обычным ярлыком start-career-bot-app.cmd, затем повторите генерацию."
            ) from exc
        raise ValueError(f"Не удалось подключиться к OpenAI API: {reason}") from exc
    except TimeoutError as exc:
        raise ValueError("OpenAI API не ответил вовремя. Повторите генерацию через минуту.") from exc

    generated = json.loads(extract_response_text(result))
    letter, valid_evidence = validate_ai_letter(generated, profile_payload, vacancy_payload)
    usage_raw = result.get("usage") or {}
    usage = {
        "input_tokens": int(usage_raw.get("input_tokens", 0) or 0),
        "output_tokens": int(usage_raw.get("output_tokens", 0) or 0),
        "total_tokens": int(usage_raw.get("total_tokens", 0) or 0),
    }
    return letter, valid_evidence, usage


def generate_gemini_letter(
    profile: dict[str, Any], vacancy: dict[str, Any], api_key: str, model: str
) -> tuple[str, list[dict[str, str]], dict[str, int]]:
    profile_payload, vacancy_payload, schema, instruction = build_ai_request(profile, vacancy)
    request_payload = {
        "systemInstruction": {"parts": [{"text": instruction}]},
        "contents": [{
            "role": "user",
            "parts": [{"text": json.dumps({"profile": profile_payload, "vacancy": vacancy_payload}, ensure_ascii=False)}],
        }],
        "generationConfig": {
            "temperature": 0.25,
            "responseMimeType": "application/json",
            "responseJsonSchema": schema,
        },
    }
    request = Request(
        f"{GEMINI_API_BASE}/{model}:generateContent",
        data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key, "User-Agent": f"CareerBot/{APP_VERSION}"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            error_payload = json.loads(exc.read().decode("utf-8")).get("error", {})
            details = str(error_payload.get("message", ""))
            status = str(error_payload.get("status", ""))
        except (json.JSONDecodeError, UnicodeDecodeError):
            details, status = "", ""
        if exc.code == 429 or status == "RESOURCE_EXHAUSTED":
            raise ValueError(
                "Бесплатный лимит Gemini для этой модели исчерпан. Попробуйте позже или выберите другую модель."
            ) from exc
        if exc.code in {401, 403}:
            raise ValueError("Gemini отклонил API-ключ или доступ к модели. Проверьте ключ и выбранную модель.") from exc
        raise ValueError(f"Gemini API вернул ошибку {exc.code}. {details}".strip()) from exc
    except URLError as exc:
        raise ValueError(f"Не удалось подключиться к Gemini API: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ValueError("Gemini API не ответил вовремя. Повторите генерацию через минуту.") from exc

    try:
        response_text = result["candidates"][0]["content"]["parts"][0]["text"]
        generated = json.loads(response_text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Gemini не вернул корректное письмо. Попробуйте повторить генерацию.") from exc
    letter, valid_evidence = validate_ai_letter(generated, profile_payload, vacancy_payload)
    usage_raw = result.get("usageMetadata") or {}
    usage = {
        "input_tokens": int(usage_raw.get("promptTokenCount", 0) or 0),
        "output_tokens": int(usage_raw.get("candidatesTokenCount", 0) or 0),
        "total_tokens": int(usage_raw.get("totalTokenCount", 0) or 0),
    }
    return letter, valid_evidence, usage


def generate_ollama_letter(
    profile: dict[str, Any], vacancy: dict[str, Any], model: str
) -> tuple[str, list[dict[str, str]], dict[str, int]]:
    profile_payload, vacancy_payload, schema, instruction = build_ai_request(profile, vacancy)
    user_content = json.dumps({"profile": profile_payload, "vacancy": vacancy_payload}, ensure_ascii=False)
    results = []
    previous_issues = []
    # Массовый режим не тратит три полных прохода модели на одну вакансию.
    # Повторная генерация остаётся доступна пользователю по кнопке.
    for attempt in range(1):
        retry_note = ""
        if attempt:
            retry_note = (
                "\n\nПерепиши результат заново. Предыдущая версия нарушила стиль эталона. Не используй ни одну "
                "служебную фразу из списка запретов. Начни с естественной адресной мотивации к роли, продукту или "
                "задачам вакансии и пиши как человек. Не превращай опыт в отдельные блоки доказательств. "
                "Исправь конкретные нарушения: " + ", ".join(previous_issues) + "."
            )
        request_payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": instruction + retry_note},
                {"role": "user", "content": user_content},
            ],
            "stream": False,
            "think": False,
            "format": "json" if model.startswith("qwen3.5") else schema,
            "options": {
                "temperature": 0.35,
                "num_ctx": OLLAMA_LETTER_CONTEXT,
                # Для письма около 2 000 знаков достаточно этого лимита; он не даёт
                # локальной модели уходить в чрезмерно долгую генерацию.
                "num_predict": 2400,
            },
        }
        request = Request(
            f"{OLLAMA_API_BASE}/api/chat",
            data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": f"CareerBot/{APP_VERSION}"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=180) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                details = str(json.loads(exc.read().decode("utf-8")).get("error", ""))
            except (json.JSONDecodeError, UnicodeDecodeError):
                details = ""
            raise ValueError(f"Ollama вернула ошибку {exc.code}. {details}".strip()) from exc
        except URLError as exc:
            raise ValueError("Ollama не запущена. Откройте Ollama и повторите генерацию.") from exc
        except TimeoutError as exc:
            raise ValueError("Локальная модель не ответила за три минуты. Попробуйте повторить генерацию.") from exc

        try:
            generated = json.loads(result["message"]["content"])
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Локальная модель не вернула корректное письмо. Попробуйте повторить генерацию.") from exc
        generated["letter"] = normalize_generated_letter(
            str(generated.get("letter", "")), profile_payload.get("name", "")
        )
        results.append(result)
        all_issues = letter_style_issues(
            str(generated.get("letter", "")), profile_payload.get("name", "")
        )
        previous_issues = [issue for issue in all_issues if issue in HARD_LETTER_ISSUES]
        if not previous_issues:
            break
    if previous_issues:
        raise ValueError(
            "Локальная модель вернула письмо с критической ошибкой: " + ", ".join(previous_issues) +
            ". Попробуйте перегенерировать письмо."
        )
    letter, valid_evidence = validate_ai_letter(generated, profile_payload, vacancy_payload)
    input_tokens = sum(int(item.get("prompt_eval_count", 0) or 0) for item in results)
    output_tokens = sum(int(item.get("eval_count", 0) or 0) for item in results)
    return letter, valid_evidence, {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


def parse_csv(text: str) -> list[dict[str, str]]:
    rows = list(csv.DictReader(text.splitlines()))
    return [{str(k).strip(): (v or "").strip() for k, v in row.items()} for row in rows]


def normalize_vacancy(raw: dict[str, Any], source: str) -> dict[str, str]:
    title = str(raw.get("title") or raw.get("name") or raw.get("position") or "Без названия").strip()
    description = str(raw.get("description") or raw.get("text") or raw.get("body") or title).strip()
    return {
        "title": title,
        "company": str(raw.get("company") or raw.get("employer") or "").strip(),
        "location": str(raw.get("location") or raw.get("area") or "").strip(),
        "salary": str(raw.get("salary") or "").strip(),
        "url": str(raw.get("url") or raw.get("link") or "").strip(),
        "source": str(raw.get("source") or source or "import").strip(),
        "description": description,
    }


def salary_to_text(salary: Any) -> str:
    if not isinstance(salary, dict):
        return ""
    parts = []
    if salary.get("from") is not None:
        parts.append(f"от {salary['from']}")
    if salary.get("to") is not None:
        parts.append(f"до {salary['to']}")
    if salary.get("currency"):
        parts.append(str(salary["currency"]))
    if salary.get("gross") is not None:
        parts.append("до вычета" if salary["gross"] else "на руки")
    return " ".join(parts)


def normalize_hh_item(item: dict[str, Any]) -> dict[str, str]:
    employer = item.get("employer") if isinstance(item.get("employer"), dict) else {}
    area = item.get("area") if isinstance(item.get("area"), dict) else {}
    snippet = item.get("snippet") if isinstance(item.get("snippet"), dict) else {}
    requirement = snippet.get("requirement") or ""
    responsibility = snippet.get("responsibility") or ""
    description = "\n".join(part for part in [requirement, responsibility] if part).strip()
    if not description:
        description = item.get("name") or "Вакансия hh.ru"
    vacancy = normalize_vacancy(
        {
            "title": item.get("name") or "Вакансия hh.ru",
            "company": employer.get("name") or "",
            "location": area.get("name") or "",
            "salary": salary_to_text(item.get("salary")),
            "url": item.get("alternate_url") or item.get("url") or "",
            "source": "hh-api",
            "description": description,
        },
        "hh-api",
    )
    vacancy["hh_id"] = str(item.get("id") or "")
    return vacancy


def strip_html(value: str) -> str:
    text = re.sub(r"<(?:br|/p|/li|/div|/h\d)\b[^>]*>", "\n", value, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[ \t]+", " ", html.unescape(text)).strip()


def fetch_hh_vacancy(vacancy_id: str, contact: str = "") -> dict[str, str]:
    user_agent = f"PersonalCareerBotMVP/{APP_VERSION}"
    if contact:
        user_agent += f" ({contact})"
    request = Request(
        f"{HH_API_BASE}/vacancies/{vacancy_id}",
        headers={
            "Accept": "application/json",
            "HH-User-Agent": user_agent,
            "User-Agent": user_agent,
        },
    )
    with urlopen(request, timeout=15) as response:
        item = json.loads(response.read().decode("utf-8"))
    employer = item.get("employer") if isinstance(item.get("employer"), dict) else {}
    area = item.get("area") if isinstance(item.get("area"), dict) else {}
    skills = [str(skill.get("name")) for skill in item.get("key_skills", []) if isinstance(skill, dict) and skill.get("name")]
    attributes = []
    for key in ("experience", "employment", "schedule", "work_format"):
        value = item.get(key)
        if isinstance(value, dict) and value.get("name"):
            attributes.append(str(value["name"]))
        elif isinstance(value, list):
            attributes.extend(str(part.get("name")) for part in value if isinstance(part, dict) and part.get("name"))
    description = strip_html(str(item.get("description") or ""))
    if skills:
        description += "\n\nКлючевые навыки: " + ", ".join(skills)
    if attributes:
        description += "\nУсловия и формат: " + ", ".join(attributes)
    return normalize_vacancy({
        "title": item.get("name"),
        "company": employer.get("name"),
        "location": area.get("name"),
        "salary": salary_to_text(item.get("salary")),
        "url": item.get("alternate_url") or f"https://hh.ru/vacancy/{vacancy_id}",
        "source": "hh-api-auto",
        "description": description,
    }, "hh-api-auto")


def browser_assist_item(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    scenario = dict(row)
    scenario_id = int(scenario["id"])
    params: dict[str, str] = {
        "text": str(scenario.get("query") or "").strip(),
        "area": str(scenario.get("area_id") or "113").strip(),
        "period": str(scenario.get("period") or 7),
        "order_by": "publication_time",
        "items_on_page": "50",
        "career_bot_assist": str(scenario_id),
        "career_bot_limit": str(max(1, min(200, int(scenario.get("result_limit") or 50)))),
    }
    salary = int(scenario.get("salary") or 0)
    if salary > 0:
        params["salary"] = str(salary)
    if scenario.get("only_with_salary"):
        params["only_with_salary"] = "true"
    work_format = str(scenario.get("work_format") or "").strip().upper()
    if work_format in SEARCH_WORK_FORMATS and work_format:
        params["work_format"] = work_format
    return {
        "id": scenario_id,
        "name": scenario.get("name") or scenario.get("query") or "Поиск hh.ru",
        "query": scenario.get("query") or "",
        "area_name": scenario.get("area_name") or "",
        "url": f"https://hh.ru/search/vacancy?{urlencode(params)}#careerBotAssist={scenario_id}",
    }


def search_hh(payload: dict[str, Any]) -> dict[str, Any]:
    text = str(payload.get("text") or "").strip()
    if not text:
        raise ValueError("Введите поисковый запрос.")
    contact = str(payload.get("contact") or "").strip()
    if not contact:
        raise ValueError("Укажите контакт для hh API. Подойдет email, который hh увидит в User-Agent.")
    if re.search(r"(example\.com|test@test|local-user)", contact, re.IGNORECASE):
        raise ValueError("hh.ru отклоняет тестовые контакты. Укажите реальный email для User-Agent.")

    def optional_int(name: str, label: str, minimum: int | None = None, maximum: int | None = None) -> int | None:
        value = str(payload.get(name) or "").strip()
        if not value:
            return None
        if not re.fullmatch(r"\d+", value):
            raise ValueError(f"Поле «{label}» должно быть числом без текста и пробелов.")
        number = int(value)
        if minimum is not None and number < minimum:
            raise ValueError(f"Поле «{label}» должно быть не меньше {minimum}.")
        if maximum is not None and number > maximum:
            raise ValueError(f"Поле «{label}» должно быть не больше {maximum}.")
        return number

    page = optional_int("page", "Страница", 0) or 0
    per_page = optional_int("per_page", "Кол-во", 1, 50) or 20

    params: dict[str, Any] = {
        "text": text,
        "page": page,
        "per_page": per_page,
    }

    for field, label, minimum, maximum in [
        ("area", "Регион hh", 1, None),
        ("salary", "Зарплата от", 1, None),
        ("period", "Период", 1, 30),
        ("professional_role", "Профроль hh", 1, None),
    ]:
        value = optional_int(field, label, minimum, maximum)
        if value is not None:
            params[field] = value

    for field in ["experience", "schedule", "work_format"]:
        value = str(payload.get(field) or "").strip()
        if value:
            if field == "work_format" and value.upper() not in SEARCH_WORK_FORMATS:
                raise ValueError("Неизвестный формат работы.")
            params[field] = value

    if payload.get("only_with_salary"):
        params["only_with_salary"] = "true"

    url = f"{HH_API_BASE}/vacancies?{urlencode(params)}"
    headers = {
        "Accept": "application/json",
        "HH-User-Agent": f"PersonalCareerBotMVP/{APP_VERSION} ({contact})",
        "User-Agent": f"PersonalCareerBotMVP/{APP_VERSION} ({contact})",
    }
    request = Request(
        url,
        headers=headers,
    )
    try:
        with urlopen(request, timeout=15) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        details = ""
        try:
            parsed_error = json.loads(body)
            errors = parsed_error.get("errors") or []
            if errors:
                details = "; ".join(
                    " ".join(str(part) for part in [item.get("type"), item.get("value")] if part)
                    for item in errors
                    if isinstance(item, dict)
                )
            details = details or parsed_error.get("description") or parsed_error.get("error") or ""
        except json.JSONDecodeError:
            details = body[:300]
        if exc.code == 400:
            hint = f" Детали hh.ru: {details}." if details else ""
            raise ValueError(f"hh.ru отклонил параметры поиска.{hint}")
        if exc.code == 403:
            raise ValueError("hh.ru запросил CAPTCHA. Откройте готовый поиск на сайте hh.ru и пройдите проверку вручную.")
        raise ValueError(f"hh.ru вернул HTTP {exc.code}. {details}".strip())
    except URLError as exc:
        reason = exc.reason
        if getattr(reason, "winerror", None) == 10013 or getattr(reason, "errno", None) == 10013:
            raise ValueError(
                "Windows заблокировал сетевое подключение к api.hh.ru (ошибка 10013). "
                "Проверьте VPN, антивирус или сетевой фильтр и откройте https://api.hh.ru в браузере, "
                "затем запустите сценарии повторно. Career Bot не будет обходить это ограничение."
            )
        raise ValueError(f"Не удалось подключиться к API hh.ru: {reason}")
    except Exception as exc:
        message = str(exc)
        raise ValueError(f"Не удалось получить вакансии hh.ru: {message}")

    items = [normalize_hh_item(item) for item in raw.get("items", []) if isinstance(item, dict)]
    return {
        "source": "hh-api",
        "found": raw.get("found", len(items)),
        "page": raw.get("page", params["page"]),
        "pages": raw.get("pages", 1),
        "per_page": raw.get("per_page", params["per_page"]),
        "items": items,
    }


def upsert_vacancy(conn: sqlite3.Connection, user_id: int, vacancy: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    profile = get_profile(conn, user_id)
    existing = None
    if vacancy.get("url"):
        existing = conn.execute(
            "select * from vacancies where url = ? and user_id = ? order by id desc limit 1",
            (vacancy["url"], user_id),
        ).fetchone()
        hh_id = re.search(r"/vacancy/(\d+)", str(vacancy["url"]))
        if not existing and hh_id:
            existing = conn.execute(
                "select * from vacancies where user_id = ? and url like ? order by id desc limit 1",
                (user_id, f"%/vacancy/{hh_id.group(1)}%"),
            ).fetchone()
    if existing:
        old_description = str(existing["description"] or "")
        if len(str(vacancy.get("description", ""))) > len(old_description) + 100:
            score = score_vacancy(profile, vacancy)
            conn.execute(
                """update vacancies set title = ?, company = ?, location = ?, salary = ?, source = ?,
                description = ?, score = ?, score_explanation = ?, updated_at = ? where id = ?""",
                (
                    vacancy["title"], vacancy["company"], vacancy["location"], vacancy["salary"], vacancy["source"],
                    vacancy["description"], score.score, json.dumps(score.explanation, ensure_ascii=False),
                    now_iso(), int(existing["id"]),
                ),
            )
        row = conn.execute("select * from vacancies where id = ?", (int(existing["id"]),)).fetchone()
        return row_to_dict(row), False
    score = score_vacancy(profile, vacancy)
    ts = now_iso()
    cursor = conn.execute(
        """insert into vacancies (
            title, company, location, salary, url, source, description,
            status, score, score_explanation, created_at, updated_at, user_id
        ) values (?, ?, ?, ?, ?, ?, ?, 'found', ?, ?, ?, ?, ?)""",
        (
            vacancy["title"], vacancy["company"], vacancy["location"], vacancy["salary"], vacancy["url"],
            vacancy["source"], vacancy["description"], score.score,
            json.dumps(score.explanation, ensure_ascii=False), ts, ts, user_id,
        ),
    )
    row = conn.execute("select * from vacancies where id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_dict(row), True


def process_search_run(run_id: int) -> None:
    with db() as conn:
        run = conn.execute("select * from search_runs where id = ?", (run_id,)).fetchone()
        if not run or run["status"] != "queued":
            return
        scenario = conn.execute("select * from search_scenarios where id = ?", (run["scenario_id"],)).fetchone()
        if not scenario:
            conn.execute("update search_runs set status = 'error', error = ?, finished_at = ? where id = ?", ("Сценарий удален", now_iso(), run_id))
            return
        conn.execute("update search_runs set status = 'running', started_at = ? where id = ?", (now_iso(), run_id))
        scenario = dict(scenario)
        user_id = int(run["user_id"])

    processed = imported = duplicates = found = 0
    try:
        limit = max(1, min(200, int(scenario.get("result_limit") or 50)))
        page = 0
        while processed < limit:
            with db() as conn:
                state = conn.execute("select status from search_runs where id = ?", (run_id,)).fetchone()
                if not state or state["status"] == "stopping":
                    break
            payload = {
                "text": scenario["query"], "area": scenario["area_id"], "salary": scenario["salary"],
                "period": scenario["period"], "only_with_salary": bool(scenario["only_with_salary"]),
                "work_format": scenario.get("work_format") or "", "contact": scenario["contact"],
                "page": page, "per_page": min(50, limit - processed),
            }
            result = search_hh(payload)
            found = int(result.get("found") or 0)
            items = result.get("items") or []
            if not items:
                break
            for item in items:
                with db() as conn:
                    state = conn.execute("select status from search_runs where id = ?", (run_id,)).fetchone()
                    if not state or state["status"] == "stopping":
                        break
                vacancy = item
                if item.get("hh_id"):
                    try:
                        vacancy = fetch_hh_vacancy(str(item["hh_id"]), str(scenario["contact"]))
                    except Exception:
                        pass
                with db() as conn:
                    _, created = upsert_vacancy(conn, user_id, vacancy)
                    processed += 1
                    imported += int(created)
                    duplicates += int(not created)
                    conn.execute(
                        "update search_runs set found = ?, processed = ?, imported = ?, duplicates = ? where id = ?",
                        (found, processed, imported, duplicates, run_id),
                    )
                if processed >= limit:
                    break
            if page + 1 >= int(result.get("pages") or 1):
                break
            page += 1
        with db() as conn:
            state = conn.execute("select status from search_runs where id = ?", (run_id,)).fetchone()
            final_status = "stopped" if state and state["status"] == "stopping" else "done"
            conn.execute(
                "update search_runs set status = ?, found = ?, processed = ?, imported = ?, duplicates = ?, finished_at = ? where id = ?",
                (final_status, found, processed, imported, duplicates, now_iso(), run_id),
            )
    except Exception as exc:
        with db() as conn:
            error = str(exc)[:1000]
            conn.execute(
                "update search_runs set status = 'error', error = ?, found = ?, processed = ?, imported = ?, duplicates = ?, finished_at = ? where id = ?",
                (error, found, processed, imported, duplicates, now_iso(), run_id),
            )
            if "ошибка 10013" in error:
                conn.execute(
                    """update search_runs set status = 'stopped', error = ?, finished_at = ?
                    where user_id = ? and status = 'queued'""",
                    ("Остановлено: Windows заблокировал доступ к api.hh.ru в этом запуске.", now_iso(), user_id),
                )


def search_queue_worker() -> None:
    while True:
        try:
            with db() as conn:
                row = conn.execute("select id from search_runs where status = 'queued' order by id limit 1").fetchone()
            if row:
                process_search_run(int(row["id"]))
            else:
                time.sleep(0.8)
        except Exception:
            time.sleep(1.5)


def parse_import(payload: dict[str, Any]) -> list[dict[str, str]]:
    text = (payload.get("text") or "").strip()
    source = (payload.get("source") or "import").strip()
    fmt = (payload.get("format") or "auto").lower()
    if not text:
        return []

    if fmt in {"auto", "json"}:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                parsed = parsed.get("items") or parsed.get("vacancies") or [parsed]
            if isinstance(parsed, list):
                return [normalize_vacancy(item, source) for item in parsed if isinstance(item, dict)]
        except json.JSONDecodeError:
            if fmt == "json":
                raise ValueError("JSON не распознан.")

    if fmt in {"auto", "csv"} and "," in text.splitlines()[0]:
        try:
            rows = parse_csv(text)
            if rows and any("title" in row or "name" in row for row in rows):
                return [normalize_vacancy(row, source) for row in rows]
        except csv.Error:
            if fmt == "csv":
                raise ValueError("CSV не распознан.")

    first_line = text.splitlines()[0].strip()[:120] or "Импортированная вакансия"
    return [
        normalize_vacancy(
            {
                "title": first_line,
                "description": text,
                "source": source,
            },
            source,
        )
    ]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def send_json(self, data: Any, status: int = 200, cookies: list[str] | None = None) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for cookie in cookies or []:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def session_user(self, conn: sqlite3.Connection) -> sqlite3.Row | None:
        owner = conn.execute("select * from users where role = 'owner' order by id limit 1").fetchone()
        if owner:
            return owner
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        morsel = cookie.get("career_bot_session")
        if not morsel:
            return None
        token_hash = hashlib.sha256(morsel.value.encode("utf-8")).hexdigest()
        user = conn.execute(
            """
            select users.* from sessions
            join users on users.id = sessions.user_id
            where sessions.token_hash = ? and sessions.expires_at > ?
            """,
            (token_hash, now_iso()),
        ).fetchone()
        return user

    def create_session(self, conn: sqlite3.Connection, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
        conn.execute(
            "insert into sessions (token_hash, user_id, expires_at, created_at) values (?, ?, ?, ?)",
            (hashlib.sha256(token.encode("utf-8")).hexdigest(), user_id, expires.isoformat(), now_iso()),
        )
        return f"career_bot_session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={SESSION_DAYS * 86400}"

    def require_user(self, conn: sqlite3.Connection) -> sqlite3.Row | None:
        user = self.session_user(conn)
        if not user:
            self.send_json({"error": "Требуется вход", "code": "auth_required"}, 401)
        return user

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            return super().do_GET()

        try:
            with db() as conn:
                if parsed.path == "/api/health":
                    return self.send_json({"ok": True, "version": APP_VERSION})

                if parsed.path == "/api/auth/state":
                    user_count = conn.execute("select count(*) from users").fetchone()[0]
                    user = self.session_user(conn)
                    return self.send_json({
                        "setup_required": user_count == 0,
                        "authenticated": bool(user),
                        "user": public_user(user) if user else None,
                    })

                apply_match = re.fullmatch(r"/api/apply/session/([A-Za-z0-9_-]{20,})", parsed.path)
                if apply_match:
                    session = conn.execute(
                        "select letter, vacancy_id, user_id, batch_token, status, stage, route from apply_sessions where token = ? and expires_at > ?",
                        (apply_match.group(1), now_iso()),
                    ).fetchone()
                    if not session:
                        return self.send_json({"error": "Сеанс отклика истек или не найден."}, 404)
                    if session["batch_token"]:
                        active = conn.execute("select 1 from apply_batches where token = ? and status = 'running' and expires_at > ?", (session["batch_token"], now_iso())).fetchone()
                        if not active or session["status"] != "running":
                            return self.send_json({"error": "Этот отклик остановлен или уже обработан."}, 409)
                    vacancy = conn.execute("select title, company, url from vacancies where id = ?", (session["vacancy_id"],)).fetchone()
                    profile = get_profile(conn, int(session["user_id"]))
                    return self.send_json({
                        "letter": session["letter"],
                        "vacancy": dict(vacancy) if vacancy else {},
                        "hh_resume_title": profile.get("hh_resume_title", ""),
                        "auto_submit": False,
                        "diagnostic": session["status"] == "diagnostic",
                        "apply_stage": session["stage"],
                        "route": session["route"],
                    })

                batch_match = re.fullmatch(r"/api/apply/batches/([A-Za-z0-9_-]{20,})/next", parsed.path)
                if batch_match:
                    return self.send_json({"error": "Автоотправка отключена до завершения диагностики."}, 409)
                    batch_token = batch_match.group(1)
                    batch = conn.execute(
                        "select * from apply_batches where token = ? and expires_at > ?", (batch_token, now_iso())
                    ).fetchone()
                    if not batch:
                        return self.send_json({"error": "Пакет откликов истек или не найден."}, 404)
                    if batch["status"] != "running":
                        return self.send_json({"error": "Пакет остановлен. Продолжите его из Career Bot."}, 409)
                    session = conn.execute(
                        """select s.*, v.url, v.title, v.company from apply_sessions s
                        join vacancies v on v.id = s.vacancy_id
                        where s.batch_token = ? and s.status = 'running'
                        order by s.created_at limit 1""",
                        (batch_token,),
                    ).fetchone()
                    if session:
                        return self.send_json({"error": "Предыдущий отклик ещё обрабатывается. При прерывании остановите пакет в Career Bot."}, 409)
                    if not session:
                        session = conn.execute(
                            """select s.*, v.url, v.title, v.company from apply_sessions s
                            join vacancies v on v.id = s.vacancy_id
                            where s.batch_token = ? and s.status = 'pending'
                            order by s.created_at limit 1""",
                            (batch_token,),
                        ).fetchone()
                        if session:
                            conn.execute(
                                "update apply_sessions set status = 'running', updated_at = ? where token = ?",
                                (now_iso(), session["token"]),
                            )
                    if not session:
                        conn.execute(
                            "update apply_batches set status = 'done', finished_at = ? where token = ? and status != 'done'",
                            (now_iso(), batch_token),
                        )
                        return self.send_json({"done": True, "total": int(batch["total"])})
                    clean_url = str(session["url"] or "").split("#", 1)[0]
                    separator = "&" if "#" in clean_url else "#"
                    return self.send_json({
                        "done": False,
                        "item": {
                            "session_token": session["token"],
                            "title": session["title"],
                            "company": session["company"],
                            "url": f"{clean_url}{separator}careerBotApply={session['token']}&careerBotBatch={batch_token}",
                        },
                    })

                user = self.require_user(conn)
                if not user:
                    return
                user_id = int(user["id"])

                if parsed.path == "/api/profile":
                    return self.send_json(get_profile(conn, user_id))

                if parsed.path == "/api/apply/diagnostic/latest":
                    row = conn.execute("SELECT e.payload,e.created_at,v.title FROM events e JOIN vacancies v ON v.id=e.vacancy_id WHERE v.user_id=? AND e.event_type='apply_diagnostic' ORDER BY e.id DESC LIMIT 1", (user_id,)).fetchone()
                    return self.send_json(dict(row) if row else {})

                if parsed.path == "/api/profile/resume":
                    profile = conn.execute("select resume_file_name, resume_file_path from user_profiles where user_id = ?", (user_id,)).fetchone()
                    path = Path(profile["resume_file_path"]) if profile and profile["resume_file_path"] else None
                    if not path or not path.is_file() or path.parent.resolve() != RESUME_DIR.resolve():
                        return self.send_json({"error": "PDF-резюме не загружено."}, 404)
                    data = path.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/pdf")
                    self.send_header("Content-Disposition", f'attachment; filename="resume.pdf"')
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return

                if parsed.path == "/api/ai/settings":
                    if user["role"] != "owner":
                        return self.send_json({"error": "Настройки ИИ доступны только владельцу."}, 403)
                    return self.send_json(get_ai_status(conn, user_id))

                if parsed.path == "/api/hh/areas":
                    return self.send_json(get_hh_areas())

                if parsed.path == "/api/hh/area-suggest":
                    query = parse_qs(parsed.query).get("q", [""])[0]
                    return self.send_json(suggest_hh_areas(query))

                if parsed.path == "/api/catalog/profile-options":
                    return self.send_json(get_profile_catalog())

                if parsed.path == "/api/search/suggestions":
                    return self.send_json(profile_search_suggestions(get_profile(conn, user_id)))

                if parsed.path == "/api/search/scenarios":
                    rows = conn.execute(
                        "select * from search_scenarios where user_id = ? order by enabled desc, id",
                        (user_id,),
                    ).fetchall()
                    return self.send_json([dict(row) for row in rows])

                if parsed.path == "/api/search/browser-plan":
                    rows = conn.execute(
                        "select * from search_scenarios where user_id = ? and enabled = 1 order by id",
                        (user_id,),
                    ).fetchall()
                    items = [browser_assist_item(row) for row in rows]
                    return self.send_json({"items": items, "total": len(items), "mode": "browser-assist"})

                if parsed.path == "/api/search/runs":
                    rows = conn.execute(
                        """select r.*, s.name as scenario_name, s.query from search_runs r
                        join search_scenarios s on s.id = r.scenario_id
                        where r.user_id = ? order by r.id desc limit 30""",
                        (user_id,),
                    ).fetchall()
                    return self.send_json([dict(row) for row in rows])

                if parsed.path == "/api/vacancies":
                    profile = get_profile(conn, user_id)
                    params = parse_qs(parsed.query)
                    where = []
                    args: list[Any] = []
                    if params.get("status", [""])[0]:
                        where.append("status = ?")
                        args.append(params["status"][0])
                    if params.get("q", [""])[0]:
                        where.append("(title like ? or company like ? or description like ?)")
                        q = f"%{params['q'][0]}%"
                        args.extend([q, q, q])
                    min_score = params.get("min_score", [""])[0]
                    if min_score:
                        where.append("score >= ?")
                        args.append(int(min_score))
                    source = params.get("source", [""])[0]
                    if source:
                        where.append("source = ?")
                        args.append(source)
                    where.insert(0, "user_id = ?")
                    args.insert(0, user_id)
                    sql = "select * from vacancies"
                    if where:
                        sql += " where " + " and ".join(where)
                    sort = params.get("sort", ["score"])[0]
                    sort_sql = {
                        "score": "score desc, updated_at desc",
                        "letter_new": "case when trim(letter_generated_at) = '' then 1 else 0 end, letter_generated_at desc, score desc",
                        "letter_old": "case when trim(letter_generated_at) = '' then 1 else 0 end, letter_generated_at asc, score desc",
                    }.get(sort, "score desc, updated_at desc")
                    sql += " order by " + sort_sql
                    rows = conn.execute(sql, args).fetchall()
                    items = [enrich_vacancy(profile, row) for row in rows]
                    eligibility = params.get("eligibility", [""])[0]
                    if eligibility:
                        items = [item for item in items if item["eligibility"]["status"] == eligibility]
                    return self.send_json(items)

                if parsed.path == "/api/letters/progress":
                    batch = conn.execute(
                        "select * from letter_batches where user_id = ? order by id desc limit 1", (user_id,)
                    ).fetchone()
                    if not batch:
                        return self.send_json({"active": False, "total": 0, "done": 0, "queued": 0, "running": 0, "error": 0})
                    counts = {row["status"]: int(row["count"]) for row in conn.execute(
                        "select status, count(*) as count from letter_jobs where batch_id = ? group by status", (batch["id"],)
                    ).fetchall()}
                    total = int(batch["total"])
                    done = counts.get("done", 0)
                    queued = counts.get("queued", 0)
                    running = counts.get("running", 0)
                    error = counts.get("error", 0)
                    return self.send_json({
                        "active": bool(queued or running), "batch_id": int(batch["id"]), "total": total, "done": done,
                        "queued": queued, "running": running, "error": error, "created_at": batch["created_at"],
                    })

                if parsed.path == "/api/apply/batches/latest":
                    for stale in conn.execute("select token from apply_batches where user_id = ? and status = 'running' and expires_at <= ?", (user_id, now_iso())).fetchall():
                        pause_apply_batch(conn, stale["token"])
                    batch = conn.execute(
                        "select * from apply_batches where user_id = ? order by created_at desc limit 1", (user_id,)
                    ).fetchone()
                    if not batch:
                        return self.send_json({"total": 0, "active": False})
                    counts = {row["status"]: int(row["count"]) for row in conn.execute(
                        "select status, count(*) as count from apply_sessions where batch_token = ? group by status",
                        (batch["token"],),
                    ).fetchall()}
                    return self.send_json({
                        "batch_token": batch["token"], "total": int(batch["total"]), "status": batch["status"],
                        "active": batch["status"] == "running", "created_at": batch["created_at"],
                        "sent": counts.get("sent", 0), "pending": counts.get("pending", 0),
                        "running": counts.get("running", 0), "skipped": counts.get("skipped", 0),
                        "needs_manual": counts.get("needs_manual", 0), "failed": counts.get("failed", 0),
                    })

                if parsed.path == "/api/funnel":
                    rows = conn.execute(
                        "select status, count(*) as count from vacancies where user_id = ? group by status",
                        (user_id,),
                    ).fetchall()
                    counts = {status: 0 for status in STATUSES}
                    counts.update({row["status"]: row["count"] for row in rows})
                    return self.send_json(
                        [{"status": status, "label": STATUS_LABELS[status], "count": counts[status]} for status in STATUSES]
                    )

            return self.send_json({"error": "Not found"}, 404)
        except Exception as exc:
            return self.send_json({"error": str(exc)}, 500)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            return self.send_json({"error": "Not found"}, 404)

        try:
            payload = self.read_json()
            with db() as conn:
                if parsed.path == "/api/auth/setup":
                    if conn.execute("select count(*) from users").fetchone()[0]:
                        return self.send_json({"error": "Первичная настройка уже завершена."}, 409)
                    owner_username = str(payload.get("owner_username", "")).strip()
                    owner_name = str(payload.get("owner_name", "")).strip() or owner_username
                    owner_password = str(payload.get("owner_password", ""))
                    tester_username = str(payload.get("tester_username", "")).strip()
                    tester_name = str(payload.get("tester_name", "")).strip() or tester_username
                    tester_password = str(payload.get("tester_password", ""))
                    if not owner_username or not tester_username:
                        raise ValueError("Введите логины владельца и тестировщика.")
                    if owner_username.lower() == tester_username.lower():
                        raise ValueError("Логины должны отличаться.")
                    if len(owner_password) < 8 or len(tester_password) < 8:
                        raise ValueError("Каждый пароль должен содержать не менее 8 символов.")
                    ts = now_iso()
                    owner_cursor = conn.execute(
                        """insert into users
                        (username, display_name, password_hash, role, can_use_ai, ai_unlimited, created_at)
                        values (?, ?, ?, 'owner', 1, 1, ?)""",
                        (owner_username, owner_name, hash_password(owner_password), ts),
                    )
                    owner_id = int(owner_cursor.lastrowid)
                    tester_cursor = conn.execute(
                        """insert into users
                        (username, display_name, password_hash, role, can_use_ai, ai_unlimited, created_at)
                        values (?, ?, ?, 'tester', 0, 0, ?)""",
                        (tester_username, tester_name, hash_password(tester_password), ts),
                    )
                    tester_id = int(tester_cursor.lastrowid)
                    legacy = conn.execute("select * from profile where id = 1").fetchone()
                    legacy_columns = set(legacy.keys()) if legacy else set()
                    legacy_values = [legacy[field] if field in legacy_columns else "" for field in PROFILE_FIELDS]
                    conn.execute(
                        f"insert into user_profiles (user_id, {', '.join(PROFILE_FIELDS)}, updated_at) "
                        f"values (?, {', '.join('?' for _ in PROFILE_FIELDS)}, ?)",
                        [owner_id, *legacy_values, ts],
                    )
                    ensure_user_profile(conn, tester_id)
                    conn.execute("update vacancies set user_id = ? where user_id is null", (owner_id,))
                    cookie = self.create_session(conn, owner_id)
                    owner = conn.execute("select * from users where id = ?", (owner_id,)).fetchone()
                    return self.send_json({"ok": True, "user": public_user(owner)}, cookies=[cookie])

                if parsed.path == "/api/auth/login":
                    username = str(payload.get("username", "")).strip()
                    password = str(payload.get("password", ""))
                    user = conn.execute("select * from users where username = ? collate nocase", (username,)).fetchone()
                    if not user or not verify_password(password, user["password_hash"]):
                        return self.send_json({"error": "Неверный логин или пароль."}, 401)
                    conn.execute("delete from sessions where expires_at <= ?", (now_iso(),))
                    cookie = self.create_session(conn, int(user["id"]))
                    return self.send_json({"ok": True, "user": public_user(user)}, cookies=[cookie])

                if parsed.path == "/api/auth/logout":
                    cookie = SimpleCookie(self.headers.get("Cookie", ""))
                    morsel = cookie.get("career_bot_session")
                    if morsel:
                        conn.execute(
                            "delete from sessions where token_hash = ?",
                            (hashlib.sha256(morsel.value.encode("utf-8")).hexdigest(),),
                        )
                    expired = "career_bot_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0"
                    return self.send_json({"ok": True}, cookies=[expired])

                if parsed.path == "/api/hh/areas/cache":
                    areas = payload.get("areas")
                    if not isinstance(areas, list):
                        raise ValueError("Некорректный справочник регионов.")
                    return self.send_json({"ok": True, "count": cache_hh_areas(areas)})

                if parsed.path == "/api/setup/hh-extension":
                    installer = ROOT / "install-hh-button.cmd"
                    subprocess.Popen(
                        ["cmd.exe", "/c", str(installer)],
                        cwd=str(ROOT),
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                    )
                    return self.send_json({"ok": True})

                batch_result_match = re.fullmatch(r"/api/apply/session/([A-Za-z0-9_-]{20,})/result", parsed.path)
                diagnostic_match = re.fullmatch(r"/api/apply/session/([A-Za-z0-9_-]{20,})/diagnostic", parsed.path)
                if diagnostic_match:
                    session = conn.execute("SELECT vacancy_id FROM apply_sessions WHERE token=? AND status='diagnostic' AND expires_at>?", (diagnostic_match.group(1), now_iso())).fetchone()
                    if not session:
                        return self.send_json({"error": "Диагностическая сессия истекла."}, 404)
                    if not isinstance(payload, dict):
                        raise ValueError("Некорректный отчет диагностики.")
                    report = json.dumps(payload, ensure_ascii=False)
                    if len(report) > 18000:
                        raise ValueError("Отчет слишком большой.")
                    route, stage, blockers = classify_diagnostic_report(payload)
                    ts = now_iso()
                    conn.execute(
                        "update apply_sessions set route=?, stage=?, diagnostic_json=?, updated_at=?, error=? where token=?",
                        (route, stage, report, ts, "; ".join(blockers), diagnostic_match.group(1)),
                    )
                    event = {"report": payload, "route": route, "stage": stage, "blockers": blockers}
                    conn.execute("INSERT INTO events(vacancy_id,event_type,payload,created_at) VALUES (?, 'apply_diagnostic', ?, ?)",
                                 (session["vacancy_id"], json.dumps(event, ensure_ascii=False), ts))
                    return self.send_json({"ok": True, "route": route, "stage": stage, "blockers": blockers})
                if batch_result_match:
                    session = conn.execute(
                        "select * from apply_sessions where token = ? and batch_token != '' and expires_at > ?",
                        (batch_result_match.group(1), now_iso()),
                    ).fetchone()
                    if not session:
                        return self.send_json({"error": "Сеанс пакетного отклика истек или не найден."}, 404)
                    if session["status"] != "running":
                        return self.send_json({"error": "Результат уже зафиксирован или отклик остановлен."}, 409)
                    outcome = str(payload.get("outcome", "")).strip()
                    if outcome not in {"sent", "skipped", "needs_manual", "failed"}:
                        raise ValueError("Некорректный результат отклика.")
                    reason = str(payload.get("reason", "")).strip()[:500]
                    ts = now_iso()
                    conn.execute(
                        "update apply_sessions set status = ?, error = ?, updated_at = ? where token = ?",
                        (outcome, reason, ts, session["token"]),
                    )
                    if outcome == "sent":
                        conn.execute(
                            "update vacancies set status = 'applied', updated_at = ? where id = ? and user_id = ?",
                            (ts, session["vacancy_id"], session["user_id"]),
                        )
                    conn.execute(
                        """insert into events(vacancy_id, event_type, payload, created_at)
                        values (?, ?, ?, ?)""",
                        (
                            session["vacancy_id"],
                            f"batch_apply_{outcome}",
                            json.dumps({"reason": reason, "batch_token": session["batch_token"]}, ensure_ascii=False),
                            ts,
                        ),
                    )
                    outstanding = conn.execute(
                        "select count(*) from apply_sessions where batch_token = ? and status in ('pending', 'running')",
                        (session["batch_token"],),
                    ).fetchone()[0]
                    if not outstanding:
                        conn.execute(
                            "update apply_batches set status = 'done', finished_at = ? where token = ?",
                            (ts, session["batch_token"]),
                        )
                    return self.send_json({"ok": True, "outcome": outcome})

                user = self.session_user(conn)
                if not user and parsed.path in {"/api/vacancies", "/api/profile/hh-import"} and payload.get("source") == "hh-browser-safe":
                    user = conn.execute("select * from users where role = 'owner' order by id limit 1").fetchone()
                if not user:
                    return self.send_json({"error": "Требуется вход", "code": "auth_required"}, 401)
                user_id = int(user["id"])

                if parsed.path == "/api/profile":
                    fields = PROFILE_FIELDS
                    values = [str(payload.get(field, "")) for field in fields]
                    conn.execute(
                        f"""
                        update user_profiles set {', '.join(field + ' = ?' for field in fields)}, updated_at = ?
                        where user_id = ?
                        """,
                        [*values, now_iso(), user_id],
                    )
                    rescore_all(conn, user_id)
                    return self.send_json(get_profile(conn, user_id))

                if parsed.path == "/api/profile/hh-import":
                    imported = payload.get("profile") if isinstance(payload.get("profile"), dict) else {}
                    limits = {"resume_text": 60000, "work_history": 30000}
                    allowed = {
                        field: (
                            sanitize_hh_profile_text(str(imported.get(field, "")))
                            if field in {"resume_text", "work_history"}
                            else str(imported.get(field, "")).strip()
                        )[:limits.get(field, 5000)]
                        for field in PROFILE_FIELDS
                    }
                    current = get_profile(conn, user_id)
                    for field in ("target_roles", "locations", "skills"):
                        if allowed.get(field):
                            allowed[field] = merge_list_text(str(current.get(field, "")), allowed[field])
                    if allowed.get("work_history"):
                        allowed["work_history"] = merge_imported_section(
                            str(current.get("work_history", "")), allowed["work_history"], "Опыт с hh.ru"
                        )[:30000]
                    if allowed.get("resume_text"):
                        allowed["resume_text"] = merge_imported_section(
                            str(current.get("resume_text", "")), allowed["resume_text"], "Импорт с hh.ru"
                        )[:60000]
                    nonempty = {field: value for field, value in allowed.items() if value}
                    if not nonempty:
                        raise ValueError("На странице hh.ru не удалось распознать данные профиля.")
                    raw_sections = payload.get("sections") if isinstance(payload.get("sections"), list) else []
                    sections = [str(item).strip()[:120] for item in raw_sections if str(item).strip()][:20]
                    summary = f"Перенесено разделов: {len(sections)}"
                    if sections:
                        summary += f" — {', '.join(sections)}"
                    assignments = ", ".join(f"{field} = ?" for field in nonempty)
                    conn.execute(
                        f"update user_profiles set {assignments}, hh_imported_at = ?, hh_import_summary = ?, updated_at = ? where user_id = ?",
                        [*nonempty.values(), now_iso(), summary, now_iso(), user_id],
                    )
                    rescore_all(conn, user_id)
                    return self.send_json({
                        "ok": True,
                        "imported_fields": list(nonempty),
                        "sections_count": len(sections),
                        "summary": summary,
                        "profile": get_profile(conn, user_id),
                    })

                if parsed.path == "/api/profile/resume":
                    file_name = Path(str(payload.get("name", "resume.pdf"))).name
                    encoded = str(payload.get("data", ""))
                    if not file_name.lower().endswith(".pdf"):
                        raise ValueError("Можно загрузить только PDF-файл.")
                    try:
                        content = base64.b64decode(encoded, validate=True)
                    except Exception as exc:
                        raise ValueError("Не удалось прочитать PDF-файл.") from exc
                    if not content.startswith(b"%PDF-"):
                        raise ValueError("Файл не является PDF.")
                    if len(content) > 10 * 1024 * 1024:
                        raise ValueError("PDF должен быть не больше 10 МБ.")
                    RESUME_DIR.mkdir(parents=True, exist_ok=True)
                    path = RESUME_DIR / f"user-{user_id}-resume.pdf"
                    path.write_bytes(content)
                    conn.execute(
                        "update user_profiles set resume_file_name = ?, resume_file_path = ?, updated_at = ? where user_id = ?",
                        (file_name, str(path.resolve()), now_iso(), user_id),
                    )
                    return self.send_json({"ok": True, "name": file_name, "size": len(content)})

                apply_match = re.fullmatch(r"/api/vacancies/(\d+)/(?:apply-session|diagnostic-session)", parsed.path)
                if apply_match:
                    diagnostic = parsed.path.endswith("/diagnostic-session")
                    vacancy_id = int(apply_match.group(1))
                    vacancy = conn.execute(
                        "select * from vacancies where id = ? and user_id = ?", (vacancy_id, user_id)
                    ).fetchone()
                    if not vacancy:
                        return self.send_json({"error": "Vacancy not found"}, 404)
                    letter = str(vacancy["cover_letter"] or "").strip()
                    if not letter:
                        raise ValueError("Сначала сгенерируйте и проверьте сопроводительное письмо.")
                    if not vacancy["letter_approved"]:
                        raise ValueError("Сначала одобрите сопроводительное письмо.")
                    if not vacancy["url"] or not re.search(r"https://(?:[\w-]+\.)?hh\.ru/vacancy/\d+", vacancy["url"]):
                        raise ValueError("Для Safe Apply нужна ссылка на вакансию hh.ru.")
                    token = secrets.token_urlsafe(24)
                    expires = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
                    conn.execute("delete from apply_sessions where expires_at <= ? and batch_token = ''", (now_iso(),))
                    conn.execute(
                        """insert into apply_sessions
                        (token, user_id, vacancy_id, letter, expires_at, created_at, stage, letter_hash, updated_at)
                        values (?, ?, ?, ?, ?, ?, 'queued', ?, ?)""",
                        (token, user_id, vacancy_id, letter, expires, now_iso(),
                         hashlib.sha256(letter.encode("utf-8")).hexdigest(), now_iso()),
                    )
                    ts = now_iso()
                    if diagnostic:
                        conn.execute("UPDATE apply_sessions SET status='diagnostic', stage='diagnostic', updated_at=? WHERE token=?", (now_iso(), token))
                        return self.send_json({"ok": True, "url": vacancy["url"].split("#", 1)[0] + "#careerBotDiagnostic=" + token})
                    conn.execute(
                        "insert into events(vacancy_id, event_type, payload, created_at) values (?, ?, ?, ?)",
                        (
                            vacancy_id,
                            "safe_apply_started",
                            json.dumps({"status": "prepared"}, ensure_ascii=False),
                            ts,
                        ),
                    )
                    clean_url = vacancy["url"].split("#", 1)[0]
                    profile = get_profile(conn, user_id)
                    return self.send_json({"ok": True, "url": f"{clean_url}#careerBotApply={token}", "hh_resume_title": profile.get("hh_resume_title", "")})

                if parsed.path in {"/api/apply/batches/pause", "/api/apply/batches/resume"}:
                    if parsed.path.endswith("/resume"):
                        return self.send_json({"error": "Автоотправка отключена до завершения диагностики."}, 409)
                    batch = conn.execute("select * from apply_batches where user_id = ? order by created_at desc limit 1", (user_id,)).fetchone()
                    if not batch:
                        raise ValueError("Пакет не найден.")
                    if parsed.path.endswith("/pause"):
                        if batch["status"] == "running":
                            pause_apply_batch(conn, batch["token"])
                        return self.send_json({"ok": True})
                    return self.send_json(resume_apply_batch(conn, batch))

                if parsed.path == "/api/vacancies/batch-apply-session":
                    return self.send_json({"error": "Автоотправка отключена. Откройте вакансию и нажмите «Диагностика без отправки»."}, 409)
                    active = conn.execute(
                        "select count(*) from apply_batches where user_id = ? and status = 'running' and expires_at > ?",
                        (user_id, now_iso()),
                    ).fetchone()[0]
                    if active:
                        raise ValueError("Уже есть активный пакет откликов. Завершите его или дождитесь истечения срока.")
                    limit = max(1, min(40, int(payload.get("limit") or 40)))
                    rows = conn.execute(
                        """select * from vacancies
                        where user_id = ? and letter_approved = 1 and trim(cover_letter) != ''
                        and status not in ('applied', 'interview', 'offer', 'rejected', 'archived')
                        and not exists (select 1 from apply_sessions s where s.vacancy_id = vacancies.id
                        and s.batch_token != '' and s.status in ('pending', 'running', 'needs_manual', 'sent'))
                        order by score desc, letter_generated_at desc""",
                        (user_id,),
                    ).fetchall()
                    candidates = [
                        row for row in rows
                        if re.search(r"https://(?:[\w-]+\.)?hh\.ru/vacancy/\d+", str(row["url"] or ""))
                    ][:limit]
                    if not candidates:
                        raise ValueError("Нет одобренных писем для активных вакансий hh.ru.")
                    batch_token = secrets.token_urlsafe(24)
                    ts = now_iso()
                    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
                    conn.execute(
                        """insert into apply_batches (token, user_id, total, status, created_at, expires_at)
                        values (?, ?, ?, 'running', ?, ?)""",
                        (batch_token, user_id, len(candidates), ts, expires),
                    )
                    for row in candidates:
                        conn.execute(
                            """insert into apply_sessions
                            (token, user_id, vacancy_id, letter, expires_at, created_at, batch_token, status, updated_at)
                            values (?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
                            (secrets.token_urlsafe(24), user_id, row["id"], row["cover_letter"], expires, ts, batch_token, ts),
                        )
                    first_url = str(candidates[0]["url"] or "").split("#", 1)[0]
                    return self.send_json({
                        "ok": True, "total": len(candidates), "batch_token": batch_token,
                        "url": f"{first_url}#careerBotBatch={batch_token}",
                    }, 201)

                if parsed.path == "/api/ai/settings":
                    if user["role"] != "owner":
                        return self.send_json({"error": "Настройки ИИ доступны только владельцу."}, 403)
                    provider = str(payload.get("provider", "openai")).strip().lower()
                    if provider not in {"openai", "gemini", "ollama"}:
                        raise ValueError("Неизвестный провайдер ИИ.")
                    default_model = (
                        DEFAULT_OLLAMA_MODEL if provider == "ollama" else
                        DEFAULT_GEMINI_MODEL if provider == "gemini" else DEFAULT_AI_MODEL
                    )
                    model = str(payload.get("model", default_model)).strip()
                    if not re.fullmatch(r"[A-Za-z0-9._:/-]{2,120}", model):
                        raise ValueError("Некорректное название модели.")
                    existing = conn.execute("select * from ai_settings where user_id = ?", (user_id,)).fetchone()
                    openai_encrypted = existing["api_key_encrypted"] if existing else None
                    gemini_encrypted = existing["gemini_api_key_encrypted"] if existing else None
                    api_key = str(payload.get("api_key", "")).strip()
                    if api_key and provider != "ollama":
                        if len(api_key) < 20:
                            raise ValueError("API-ключ выглядит слишком коротким.")
                        if provider == "gemini":
                            gemini_encrypted = protect_secret(api_key)
                        else:
                            openai_encrypted = protect_secret(api_key)
                    if payload.get("clear_key") and provider != "ollama":
                        if provider == "gemini":
                            gemini_encrypted = None
                        else:
                            openai_encrypted = None
                    conn.execute(
                        """insert into ai_settings
                        (user_id, provider, model, api_key_encrypted, gemini_api_key_encrypted, updated_at)
                        values (?, ?, ?, ?, ?, ?)
                        on conflict(user_id) do update set provider = excluded.provider, model = excluded.model,
                        api_key_encrypted = excluded.api_key_encrypted,
                        gemini_api_key_encrypted = excluded.gemini_api_key_encrypted,
                        updated_at = excluded.updated_at""",
                        (user_id, provider, model, openai_encrypted, gemini_encrypted, now_iso()),
                    )
                    return self.send_json(get_ai_status(conn, user_id))

                if parsed.path == "/api/vacancies":
                    profile = get_profile(conn, user_id)
                    vacancy = normalize_vacancy(payload, payload.get("source", "manual"))
                    existing = None
                    if vacancy["url"]:
                        existing = conn.execute(
                            "select * from vacancies where url = ? and user_id = ? order by id desc limit 1",
                            (vacancy["url"], user_id),
                        ).fetchone()
                    if not existing and vacancy["source"] == "hh-browser-safe":
                        candidates = conn.execute(
                            """select * from vacancies where user_id = ? and title = ? collate nocase
                            and company = ? collate nocase order by updated_at desc""",
                            (user_id, vacancy["title"], vacancy["company"]),
                        ).fetchall()
                        incomplete = [row for row in candidates if not vacancy_has_full_description(row_to_dict(row))]
                        if len(incomplete) == 1:
                            existing = incomplete[0]
                    if existing:
                        existing_description = str(existing["description"] or "")
                        if len(vacancy["description"]) > len(existing_description) + 100:
                            score = score_vacancy(profile, vacancy)
                            conn.execute(
                                """update vacancies set title = ?, company = ?, location = ?, salary = ?, url = ?,
                                description = ?, score = ?, score_explanation = ?, updated_at = ? where id = ?""",
                                (
                                    vacancy["title"], vacancy["company"], vacancy["location"], vacancy["salary"], vacancy["url"],
                                    vacancy["description"], score.score,
                                    json.dumps(score.explanation, ensure_ascii=False), now_iso(), int(existing["id"]),
                                ),
                            )
                            existing = conn.execute("select * from vacancies where id = ?", (int(existing["id"]),)).fetchone()
                            result = row_to_dict(existing)
                            result["duplicate"] = True
                            result["updated"] = True
                            return self.send_json(result)
                        result = row_to_dict(existing)
                        result["duplicate"] = True
                        return self.send_json(result)
                    result = score_vacancy(profile, vacancy)
                    ts = now_iso()
                    cursor = conn.execute(
                        """
                        insert into vacancies (
                            title, company, location, salary, url, source, description,
                            status, score, score_explanation, created_at, updated_at, user_id
                        ) values (?, ?, ?, ?, ?, ?, ?, 'found', ?, ?, ?, ?, ?)
                        """,
                        (
                            vacancy["title"],
                            vacancy["company"],
                            vacancy["location"],
                            vacancy["salary"],
                            vacancy["url"],
                            vacancy["source"],
                            vacancy["description"],
                            result.score,
                            json.dumps(result.explanation, ensure_ascii=False),
                            ts,
                            ts,
                            user_id,
                        ),
                    )
                    row = conn.execute("select * from vacancies where id = ?", (cursor.lastrowid,)).fetchone()
                    return self.send_json(row_to_dict(row), 201)

                if parsed.path == "/api/import":
                    profile = get_profile(conn, user_id)
                    vacancies = parse_import(payload)
                    created = []
                    for vacancy in vacancies:
                        result = score_vacancy(profile, vacancy)
                        ts = now_iso()
                        cursor = conn.execute(
                            """
                            insert into vacancies (
                                title, company, location, salary, url, source, description,
                                status, score, score_explanation, created_at, updated_at, user_id
                            ) values (?, ?, ?, ?, ?, ?, ?, 'found', ?, ?, ?, ?, ?)
                            """,
                            (
                                vacancy["title"],
                                vacancy["company"],
                                vacancy["location"],
                                vacancy["salary"],
                                vacancy["url"],
                                vacancy["source"],
                                vacancy["description"],
                                result.score,
                                json.dumps(result.explanation, ensure_ascii=False),
                                ts,
                                ts,
                                user_id,
                            ),
                        )
                        created.append(cursor.lastrowid)
                    return self.send_json({"created": len(created), "ids": created}, 201)

                if parsed.path == "/api/search/hh":
                    result = search_hh(payload)
                    profile = get_profile(conn, user_id)
                    scored_items = []
                    for vacancy in result["items"]:
                        score = score_vacancy(profile, vacancy)
                        vacancy["score"] = score.score
                        vacancy["score_explanation"] = score.explanation
                        scored_items.append(vacancy)
                    result["items"] = sorted(scored_items, key=lambda item: item["score"], reverse=True)
                    return self.send_json(result)

                if parsed.path == "/api/search/scenarios/from-intent":
                    intent = re.sub(r"\s+", " ", str(payload.get("intent") or "")).strip()
                    if len(intent) < 20:
                        raise ValueError("Опишите желаемую работу подробнее: хотя бы 20 символов.")
                    if len(intent) > 4000:
                        raise ValueError("Описание слишком длинное. Оставьте ключевые пожелания в пределах 4000 символов.")
                    area_id = str(payload.get("area_id") or "1").strip()
                    area_name = str(payload.get("area_name") or "Москва").strip()
                    salary = max(0, int(payload.get("salary") or 0))
                    period = max(1, min(30, int(payload.get("period") or 7)))
                    result_limit = max(10, min(200, int(payload.get("result_limit") or 50)))
                    only_with_salary = int(bool(payload.get("only_with_salary")))
                    work_format = str(payload.get("work_format") or "").strip().upper()
                    if work_format not in SEARCH_WORK_FORMATS:
                        raise ValueError("Неизвестный формат работы.")
                    profile = get_profile(conn, user_id)
                    title_rows = conn.execute(
                        """select title, count(*) as uses from vacancies where user_id = ? and trim(title) != ''
                        group by title collate nocase order by uses desc, max(updated_at) desc limit 80""",
                        (user_id,),
                    ).fetchall()
                    vacancy_titles = [str(row["title"]) for row in title_rows]
                    model = get_local_search_model(conn, user_id)
                    suggestions, usage = generate_local_search_scenarios(profile, intent, vacancy_titles, model)
                    ts = now_iso()
                    created = 0
                    updated = 0
                    saved = []
                    for suggestion in suggestions:
                        query = suggestion["query"]
                        existing = conn.execute(
                            "select id from search_scenarios where user_id = ? and query = ? collate nocase and area_id = ?",
                            (user_id, query, area_id),
                        ).fetchone()
                        if existing:
                            scenario_id = int(existing["id"])
                            conn.execute(
                                """update search_scenarios set name = ?, area_name = ?, salary = ?, period = ?,
                                only_with_salary = ?, work_format = ?, result_limit = ?, enabled = 1, source = 'ai-intent',
                                intent_text = ?, reason = ?, updated_at = ? where id = ?""",
                                (suggestion["name"], area_name, salary, period, only_with_salary, work_format, result_limit,
                                 intent, suggestion["reason"], ts, scenario_id),
                            )
                            updated += 1
                        else:
                            cursor = conn.execute(
                                """insert into search_scenarios
                                (user_id, name, query, area_id, area_name, salary, period, only_with_salary,
                                work_format, contact, result_limit, enabled, source, intent_text, reason, created_at, updated_at)
                                values (?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, 1, 'ai-intent', ?, ?, ?, ?)""",
                                (user_id, suggestion["name"], query, area_id, area_name, salary, period,
                                 only_with_salary, work_format, result_limit, intent, suggestion["reason"], ts, ts),
                            )
                            scenario_id = int(cursor.lastrowid)
                            created += 1
                        saved.append({"id": scenario_id, **suggestion})
                    conn.execute(
                        """insert into ai_usage
                        (user_id, vacancy_id, provider, model, input_tokens, output_tokens, total_tokens, created_at)
                        values (?, null, 'ollama', ?, ?, ?, ?, ?)""",
                        (user_id, model, usage["input_tokens"], usage["output_tokens"], usage["total_tokens"], ts),
                    )
                    return self.send_json({
                        "ok": True, "created": created, "updated": updated, "items": saved, "model": model,
                    }, 201)

                if parsed.path == "/api/search/scenarios/from-profile":
                    contact = str(payload.get("contact") or "").strip()
                    if contact and re.search(r"(example\.com|test@test|local-user)", contact, re.IGNORECASE):
                        raise ValueError("Для прямого API укажите реальный email либо оставьте поле пустым для Browser Assist.")
                    area_id = str(payload.get("area_id") or "1").strip()
                    area_name = str(payload.get("area_name") or "Москва").strip()
                    salary = max(0, int(payload.get("salary") or 0))
                    period = max(1, min(30, int(payload.get("period") or 7)))
                    result_limit = max(10, min(200, int(payload.get("result_limit") or 50)))
                    only_with_salary = int(bool(payload.get("only_with_salary")))
                    work_format = str(payload.get("work_format") or "").strip().upper()
                    if work_format not in SEARCH_WORK_FORMATS:
                        raise ValueError("Неизвестный формат работы.")
                    suggestions = profile_search_suggestions(get_profile(conn, user_id))
                    if not suggestions:
                        raise ValueError("Сначала добавьте целевые роли в профиль.")
                    ts = now_iso()
                    created = 0
                    for suggestion in suggestions:
                        query = suggestion["query"]
                        existing = conn.execute(
                            "select id from search_scenarios where user_id = ? and query = ? collate nocase and area_id = ?",
                            (user_id, query, area_id),
                        ).fetchone()
                        if existing:
                            conn.execute(
                                """update search_scenarios set name = ?, area_name = ?, salary = ?, period = ?,
                                only_with_salary = ?, work_format = ?, contact = ?, result_limit = ?, enabled = 1, source = 'profile',
                                intent_text = '', reason = ?, updated_at = ? where id = ?""",
                                (query, area_name, salary, period, only_with_salary, work_format, contact, result_limit,
                                 suggestion["reason"], ts, int(existing["id"])),
                            )
                        else:
                            conn.execute(
                                """insert into search_scenarios
                                (user_id, name, query, area_id, area_name, salary, period, only_with_salary,
                                work_format, contact, result_limit, enabled, source, reason, created_at, updated_at)
                                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'profile', ?, ?, ?)""",
                                (user_id, query, query, area_id, area_name, salary, period, only_with_salary,
                                 work_format, contact, result_limit, suggestion["reason"], ts, ts),
                            )
                            created += 1
                    return self.send_json({"ok": True, "created": created, "total": len(suggestions)})

                scenario_match = re.fullmatch(r"/api/search/scenarios/(\d+)", parsed.path)
                if scenario_match:
                    scenario_id = int(scenario_match.group(1))
                    updates = []
                    values: list[Any] = []
                    if "enabled" in payload:
                        updates.append("enabled = ?")
                        values.append(int(bool(payload.get("enabled"))))
                    if "work_format" in payload:
                        work_format = str(payload.get("work_format") or "").strip().upper()
                        if work_format not in SEARCH_WORK_FORMATS:
                            raise ValueError("Неизвестный формат работы.")
                        updates.append("work_format = ?")
                        values.append(work_format)
                    if not updates:
                        raise ValueError("Нет изменений для сценария.")
                    updates.append("updated_at = ?")
                    values.extend([now_iso(), scenario_id, user_id])
                    updated = conn.execute(
                        f"update search_scenarios set {', '.join(updates)} where id = ? and user_id = ?",
                        values,
                    ).rowcount
                    if not updated:
                        return self.send_json({"error": "Сценарий не найден"}, 404)
                    return self.send_json({"ok": True})

                scenario_delete_match = re.fullmatch(r"/api/search/scenarios/(\d+)/delete", parsed.path)
                if scenario_delete_match:
                    scenario_id = int(scenario_delete_match.group(1))
                    active = conn.execute(
                        """select count(*) from search_runs where user_id = ? and scenario_id = ?
                        and status in ('queued', 'running', 'stopping')""",
                        (user_id, scenario_id),
                    ).fetchone()[0]
                    if active:
                        return self.send_json({"error": "Сначала остановите активный API-запуск этого сценария."}, 409)
                    deleted = conn.execute(
                        "delete from search_scenarios where id = ? and user_id = ?",
                        (scenario_id, user_id),
                    ).rowcount
                    if not deleted:
                        return self.send_json({"error": "Сценарий не найден"}, 404)
                    return self.send_json({"ok": True, "deleted": deleted})

                if parsed.path == "/api/search/scenarios/delete-all":
                    if str(payload.get("confirm") or "") != "DELETE_ALL_SEARCH_SCENARIOS":
                        raise ValueError("Удаление всех сценариев не подтверждено.")
                    active = conn.execute(
                        """select count(*) from search_runs where user_id = ?
                        and status in ('queued', 'running', 'stopping')""",
                        (user_id,),
                    ).fetchone()[0]
                    if active:
                        return self.send_json({"error": "Сначала остановите активные API-запуски."}, 409)
                    deleted = conn.execute("delete from search_scenarios where user_id = ?", (user_id,)).rowcount
                    return self.send_json({"ok": True, "deleted": deleted})

                if parsed.path == "/api/search/run-all":
                    active = conn.execute(
                        "select count(*) from search_runs where user_id = ? and status in ('queued', 'running', 'stopping')",
                        (user_id,),
                    ).fetchone()[0]
                    if active:
                        raise ValueError("Поиск уже запущен. Дождитесь завершения или остановите его.")
                    scenarios = conn.execute(
                        "select id from search_scenarios where user_id = ? and enabled = 1 order by id",
                        (user_id,),
                    ).fetchall()
                    if not scenarios:
                        raise ValueError("Нет включенных поисковых сценариев.")
                    ts = now_iso()
                    run_ids = []
                    for scenario in scenarios:
                        cursor = conn.execute(
                            "insert into search_runs (user_id, scenario_id, status, created_at) values (?, ?, 'queued', ?)",
                            (user_id, int(scenario["id"]), ts),
                        )
                        run_ids.append(int(cursor.lastrowid))
                    return self.send_json({"ok": True, "queued": len(run_ids), "run_ids": run_ids}, 202)

                if parsed.path == "/api/search/stop":
                    count = conn.execute(
                        "update search_runs set status = 'stopping' where user_id = ? and status in ('queued', 'running')",
                        (user_id,),
                    ).rowcount
                    return self.send_json({"ok": True, "stopping": count})

                if parsed.path == "/api/vacancies/batch-letter":
                    if not user["can_use_ai"]:
                        return self.send_json({"error": "AI-генерация недоступна."}, 403)
                    get_ai_credentials(conn, user_id)
                    min_score = max(65, min(100, int(payload.get("min_score") or 65)))
                    scope = str(payload.get("scope") or "score")
                    limit = max(1, min(100, int(payload.get("limit") or 100)))
                    where = ["user_id = ?", "score >= ?", "status not in ('rejected', 'archived', 'applied', 'interview', 'offer')", "trim(cover_letter) = ''"]
                    args: list[Any] = [user_id, min_score]
                    if scope == "liked":
                        where.append("status = 'matched'")
                    rows = conn.execute(
                        "select * from vacancies where " + " and ".join(where) + " order by score desc limit ?",
                        [*args, limit],
                    ).fetchall()
                    ts = now_iso()
                    batch_cursor = conn.execute(
                        "insert into letter_batches (user_id, total, created_at) values (?, ?, ?)",
                        (user_id, len(rows), ts),
                    )
                    batch_id = int(batch_cursor.lastrowid)
                    queued = []
                    skipped_incomplete = 0
                    for row in rows:
                        vacancy = row_to_dict(row)
                        queue_letter_job(conn, user_id, int(row["id"]), batch_id=batch_id)
                        queued.append(int(row["id"]))
                    return self.send_json({"ok": True, "batch_id": batch_id, "queued": len(queued), "ids": queued, "skipped_incomplete": skipped_incomplete}, 202)

                if parsed.path == "/api/vacancies/batch-approve-letter":
                    if payload.get("all") is True:
                        approved = conn.execute(
                            "update vacancies set letter_approved = 1, updated_at = ? where user_id = ? and trim(cover_letter) != ''",
                            (now_iso(), user_id),
                        ).rowcount
                        return self.send_json({"ok": True, "approved": approved})
                    raw_ids = payload.get("ids") if isinstance(payload.get("ids"), list) else []
                    ids = sorted({int(item) for item in raw_ids if str(item).isdigit()})[:100]
                    if not ids:
                        raise ValueError("Выберите готовые письма для подтверждения.")
                    placeholders = ",".join("?" for _ in ids)
                    approved = conn.execute(
                        f"""update vacancies set letter_approved = 1, updated_at = ?
                        where user_id = ? and id in ({placeholders}) and trim(cover_letter) != ''""",
                        [now_iso(), user_id, *ids],
                    ).rowcount
                    return self.send_json({"ok": True, "approved": approved})

                if parsed.path == "/api/vacancies/delete-all":
                    confirm = str(payload.get("confirm", ""))
                    if confirm != "DELETE_ALL_VACANCIES":
                        raise ValueError("Подтверждение удаления не получено.")
                    count = conn.execute("select count(*) from vacancies where user_id = ?", (user_id,)).fetchone()[0]
                    conn.execute(
                        "delete from events where vacancy_id in (select id from vacancies where user_id = ?)",
                        (user_id,),
                    )
                    conn.execute("delete from letter_jobs where user_id = ?", (user_id,))
                    conn.execute("delete from apply_sessions where user_id = ?", (user_id,))
                    conn.execute("delete from apply_batches where user_id = ?", (user_id,))
                    conn.execute("delete from vacancies where user_id = ?", (user_id,))
                    return self.send_json({"ok": True, "deleted": int(count)})

                delete_match = re.fullmatch(r"/api/vacancies/(\d+)/delete", parsed.path)
                if delete_match:
                    vacancy_id = int(delete_match.group(1))
                    if str(payload.get("confirm", "")) != "DELETE_VACANCY":
                        raise ValueError("Подтверждение удаления не получено.")
                    exists = conn.execute(
                        "select id from vacancies where id = ? and user_id = ?", (vacancy_id, user_id)
                    ).fetchone()
                    if not exists:
                        return self.send_json({"error": "Vacancy not found"}, 404)
                    conn.execute("delete from events where vacancy_id = ?", (vacancy_id,))
                    conn.execute("delete from letter_jobs where vacancy_id = ? and user_id = ?", (vacancy_id, user_id))
                    conn.execute("delete from apply_sessions where vacancy_id = ? and user_id = ?", (vacancy_id, user_id))
                    conn.execute("delete from vacancies where id = ? and user_id = ?", (vacancy_id, user_id))
                    return self.send_json({"ok": True, "deleted": vacancy_id})

                match = re.fullmatch(r"/api/vacancies/(\d+)/(status|letter|letter-text|notes|approve-letter)", parsed.path)
                if match:
                    vacancy_id = int(match.group(1))
                    action = match.group(2)
                    row = conn.execute(
                        "select * from vacancies where id = ? and user_id = ?", (vacancy_id, user_id)
                    ).fetchone()
                    if not row:
                        return self.send_json({"error": "Vacancy not found"}, 404)
                    vacancy = row_to_dict(row)

                    if action == "status":
                        status = payload.get("status")
                        if status not in STATUSES:
                            return self.send_json({"error": "Unknown status"}, 400)
                        conn.execute(
                            "update vacancies set status = ?, updated_at = ? where id = ?",
                            (status, now_iso(), vacancy_id),
                        )
                        conn.execute(
                            "insert into events(vacancy_id, event_type, payload, created_at) values (?, ?, ?, ?)",
                            (vacancy_id, "status_changed", json.dumps({"status": status}, ensure_ascii=False), now_iso()),
                        )

                    if action == "letter":
                        if not user["can_use_ai"]:
                            return self.send_json(
                                {"error": "AI-генерация доступна только владельцу Career Bot.", "code": "ai_forbidden"},
                                403,
                            )
                        get_ai_credentials(conn, user_id)
                        job = queue_letter_job(conn, user_id, vacancy_id)
                        return self.send_json({"ok": True, "job": job}, 202)

                    if action == "notes":
                        conn.execute(
                            "update vacancies set notes = ?, updated_at = ? where id = ?",
                            (str(payload.get("notes", "")), now_iso(), vacancy_id),
                        )

                    if action == "letter-text":
                        letter = str(payload.get("letter", "")).strip()
                        if len(letter) < 40:
                            raise ValueError("Письмо слишком короткое.")
                        conn.execute(
                            "update vacancies set cover_letter = ?, letter_approved = 0, updated_at = ? where id = ?",
                            (letter, now_iso(), vacancy_id),
                        )

                    if action == "approve-letter":
                        if not str(vacancy.get("cover_letter", "")).strip():
                            raise ValueError("Сначала сгенерируйте письмо.")
                        conn.execute(
                            "update vacancies set letter_approved = 1, updated_at = ? where id = ?",
                            (now_iso(), vacancy_id),
                        )

                    updated = conn.execute(
                        "select * from vacancies where id = ? and user_id = ?", (vacancy_id, user_id)
                    ).fetchone()
                    return self.send_json(enrich_vacancy(get_profile(conn, user_id), updated))

            return self.send_json({"error": "Not found"}, 404)
        except ValueError as exc:
            return self.send_json({"error": str(exc)}, 400)
        except Exception as exc:
            return self.send_json({"error": str(exc)}, 500)


def main() -> None:
    init_db()
    with db() as conn:
        for batch in conn.execute("select token from apply_batches where status = 'running'").fetchall():
            pause_apply_batch(conn, batch["token"])
        for user_row in conn.execute("select id from users").fetchall():
            rescore_all(conn, int(user_row["id"]))
        conn.execute("update letter_jobs set status = 'queued', updated_at = ? where status = 'running'", (now_iso(),))
        conn.execute("update vacancies set letter_job_status = 'queued' where letter_job_status = 'running'")
        conn.execute("update search_runs set status = 'queued', started_at = '' where status = 'running'")
        conn.execute("update search_runs set status = 'stopped', finished_at = ? where status = 'stopping'", (now_iso(),))
    threading.Thread(target=letter_queue_worker, name="letter-queue", daemon=True).start()
    threading.Thread(target=search_queue_worker, name="search-queue", daemon=True).start()
    host = os.environ.get("CAREER_BOT_HOST", "127.0.0.1")
    port = int(os.environ.get("CAREER_BOT_PORT", "8765"))
    server = ThreadingHTTPServer((host, port), Handler)
    print("Personal Career Bot MVP")
    print(f"Local database: {DB_PATH}")
    print(f"Open http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
