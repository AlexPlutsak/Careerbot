"""Build a private transfer archive without changing the live database."""
from pathlib import Path
import hashlib
import json
import sqlite3
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "Career-Bot-transfer-0.21.5-2026-09-05-ready.zip"
FOLDERS = ("career_bot", "hh-career-bot-extension", "scripts", "tests", "docs")
FILES = ("README.md", "QUICK_START_NEW_PC.md", "CODEX_HANDOFF.md",
         "start-career-bot-app.cmd", "run-career-bot.cmd", "stop-career-bot.cmd",
         "setup-ollama.cmd", "install-hh-button.cmd")


def main():
    if OUTPUT.exists():
        raise SystemExit(f"Archive already exists: {OUTPUT}")
    with tempfile.TemporaryDirectory(prefix="career-bot-transfer-") as temp:
        snapshot = Path(temp) / "career_bot.sqlite"
        with sqlite3.connect((ROOT / "data/career_bot.sqlite").as_uri() + "?mode=ro", uri=True) as source:
            with sqlite3.connect(snapshot) as dest:
                source.backup(dest)
            dest.close()
        source.close()
        with sqlite3.connect(snapshot) as dest:
            dest.execute("delete from sessions")
            dest.execute("delete from apply_sessions")
            dest.execute("update apply_batches set status='paused' where status='running'")
            dest.execute("update letter_jobs set status='error', error='Перенос на другой ПК: запустите генерацию вручную' where status in ('queued','running')")
            dest.execute("update vacancies set letter_job_status='error', letter_job_error='Перенос на другой ПК: запустите генерацию вручную' where letter_job_status in ('queued','running')")
            dest.execute("update search_runs set status='stopped' where status in ('queued','running','stopping')")
            dest.execute("update ai_settings set provider='ollama', model='qwen3:8b', api_key_encrypted=NULL, gemini_api_key_encrypted=NULL")
            counts = {t: dest.execute(f"select count(*) from {t}").fetchone()[0]
                      for t in ("users", "user_profiles", "vacancies", "events")}
            counts["letters"] = dest.execute("select count(*) from vacancies where trim(cover_letter) != ''").fetchone()[0]
            assert dest.execute("pragma integrity_check").fetchone()[0] == "ok"
        dest.close()
        members = [(ROOT / name, name) for name in FILES]
        for folder in FOLDERS:
            for path in (ROOT / folder).rglob("*"):
                if path.is_file() and "__pycache__" not in path.parts and path.suffix not in (".pyc", ".log"):
                    members.append((path, path.relative_to(ROOT).as_posix()))
        members.append((snapshot, "data/career_bot.sqlite"))
        with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
            for path, name in members:
                archive.write(path, "Career-Bot/" + name)
        with zipfile.ZipFile(OUTPUT) as archive:
            assert archive.testzip() is None
            assert len(archive.namelist()) == len(set(archive.namelist()))
        print(json.dumps({"archive": str(OUTPUT), "bytes": OUTPUT.stat().st_size,
                          "files": len(members), "counts": counts,
                          "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
