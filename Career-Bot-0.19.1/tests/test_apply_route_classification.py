import unittest

from career_bot.server import classify_diagnostic_report


class ApplyRouteClassificationTest(unittest.TestCase):
    def test_detects_direct_cover_letter_form(self):
        route, stage, blockers = classify_diagnostic_report({
            "fields": [{"qa": "vacancy-response-popup-form-letter-input"}],
            "buttons": [], "blockers": [],
        })
        self.assertEqual((route, stage, blockers), ("direct_letter_form", "letter_form_open", []))

    def test_questions_override_other_routes(self):
        route, stage, blockers = classify_diagnostic_report({
            "fields": [{"qa": "vacancy-response-popup-form-letter-input"}],
            "buttons": [], "blockers": ["Дополнительный вопрос, тест или анкета работодателя."],
        })
        self.assertEqual(route, "manual")
        self.assertEqual(stage, "needs_manual")
        self.assertTrue(blockers)

    def test_detects_post_application_link(self):
        route, stage, blockers = classify_diagnostic_report({
            "fields": [], "buttons": [{"qa": "responded-success-attach-cover-letter", "label": "Приложить сопроводительное письмо"}], "blockers": [],
        })
        self.assertEqual((route, stage, blockers), ("post_application_letter", "application_created", []))

    def test_generic_chat_header_is_not_vacancy_chat(self):
        route, stage, _blockers = classify_diagnostic_report({
            "fields": [], "buttons": [{"qa": "chatikActivator-button", "label": "Чаты"}], "blockers": [],
        })
        self.assertEqual((route, stage), ("unknown", "unknown_result"))


if __name__ == "__main__":
    unittest.main()
