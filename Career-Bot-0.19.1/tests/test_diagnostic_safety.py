from pathlib import Path
import re
import unittest


class DiagnosticSafetyTest(unittest.TestCase):
    def test_no_site_click_or_submit_in_diagnostic_script(self):
        source = (Path(__file__).resolve().parents[1] / "hh-career-bot-extension" / "diagnostic.js").read_text(encoding="utf-8")
        self.assertNotRegex(source, r"\.(?:click|submit|requestSubmit)\s*\(")
        self.assertNotRegex(source, r"KeyboardEvent|location\.(?:assign|replace)")
        self.assertIn('fields.length !== 1', source)
        self.assertIn('exactLetterMatch', source)

    def test_diagnostic_uses_separate_url_marker(self):
        source = (Path(__file__).resolve().parents[1] / "hh-career-bot-extension" / "diagnostic.js").read_text(encoding="utf-8")
        self.assertIn('get("careerBotDiagnostic")', source)
        self.assertNotIn('get("careerBotApply")', source)


if __name__ == "__main__":
    unittest.main()
