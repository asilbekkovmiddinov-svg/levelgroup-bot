import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HANDLER = (ROOT / "handlers" / "admin_arena_v4.py").read_text(encoding="utf-8")
API = (ROOT / "services" / "arena_v4_api.py").read_text(encoding="utf-8")


class ArenaFinishedResultEditTests(unittest.TestCase):
    def test_finished_post_keeps_edit_button(self):
        self.assertIn("✏️ Natijani tahrirlash", HANDLER)
        self.assertIn("arv4:e:start:", HANDLER)
        self.assertIn("finished_result_edit_keyboard(match_id)", HANDLER)

    def test_edit_flow_has_adjust_reset_and_confirm_callbacks(self):
        self.assertIn('F.data.startswith("arv4:e:adj:")', HANDLER)
        self.assertIn('F.data.startswith("arv4:e:reset:")', HANDLER)
        self.assertIn('F.data.startswith("arv4:e:confirm:")', HANDLER)
        self.assertIn("Durang mumkin emas", HANDLER)

    def test_finished_correction_uses_internal_backend_endpoint(self):
        self.assertIn("correct_finished_match_result", API)
        self.assertIn('/correct-result', API)
        self.assertIn("TELEGRAM_CHANNEL_FINISHED_RESULT_CORRECTION", API)

    def test_correction_requires_arena_admin(self):
        section = HANDLER.split("async def confirm_finished_result_edit", 1)[1]
        self.assertIn("is_arena_admin(callback.from_user.id)", section)


if __name__ == "__main__":
    unittest.main()
