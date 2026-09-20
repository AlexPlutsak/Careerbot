import sqlite3
import unittest

from career_bot.server import pause_apply_batch, resume_apply_batch


class ApplyRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE apply_batches (token TEXT PRIMARY KEY, status TEXT, expires_at TEXT);
            CREATE TABLE vacancies (id INTEGER PRIMARY KEY, url TEXT);
            CREATE TABLE apply_sessions (token TEXT PRIMARY KEY, vacancy_id INTEGER,
                batch_token TEXT, status TEXT, error TEXT, updated_at TEXT, expires_at TEXT);
            INSERT INTO apply_batches VALUES ('old-batch', 'running', '2099');
            INSERT INTO vacancies VALUES (1, 'https://hh.ru/vacancy/1');
            INSERT INTO vacancies VALUES (2, 'https://hh.ru/vacancy/2');
            INSERT INTO vacancies VALUES (3, 'https://hh.ru/vacancy/3');
            INSERT INTO apply_sessions VALUES ('uncertain',1,'old-batch','running','','','2099');
            INSERT INTO apply_sessions VALUES ('untouched',2,'old-batch','pending','','','2099');
            INSERT INTO apply_sessions VALUES ('sent',3,'old-batch','sent','','','2099');
        """)

    def tearDown(self):
        self.conn.close()

    def test_pause_and_resume_only_untouched(self):
        pause_apply_batch(self.conn, "old-batch")
        batch = self.conn.execute("SELECT * FROM apply_batches").fetchone()
        self.assertEqual(batch["status"], "paused")
        self.assertEqual(self.conn.execute("SELECT status FROM apply_sessions WHERE token='uncertain'").fetchone()[0], "needs_manual")
        result = resume_apply_batch(self.conn, batch)
        self.assertEqual(result["remaining"], 1)
        self.assertIn("/vacancy/2#careerBotBatch=", result["url"])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM apply_sessions WHERE token='untouched'").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM apply_batches WHERE token='old-batch'").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM apply_sessions WHERE status='running'").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT status FROM apply_sessions WHERE token='sent'").fetchone()[0], "sent")

    def test_cannot_resume_running_batch(self):
        with self.assertRaises(ValueError):
            resume_apply_batch(self.conn, self.conn.execute("SELECT * FROM apply_batches").fetchone())

    def test_pause_idempotent(self):
        pause_apply_batch(self.conn, "old-batch")
        pause_apply_batch(self.conn, "old-batch")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM apply_sessions WHERE status='pending'").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
