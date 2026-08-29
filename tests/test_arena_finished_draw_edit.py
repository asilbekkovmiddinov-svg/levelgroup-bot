import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAW_HANDLER = (ROOT / "handlers" / "admin_arena_draw_edit.py").read_text(encoding="utf-8")
BOT = (ROOT / "bot.py").read_text(encoding="utf-8")


class ArenaFinishedDrawEditTests(unittest.TestCase):
    def test_draw_correction_calls_backend(self):
        self.assertIn("correct_finished_match_result", DRAW_HANDLER)
        self.assertIn('F.data.regexp', DRAW_HANDLER)
        self.assertIn('arv4:e:confirm:', DRAW_HANDLER)

    def test_draw_router_is_before_legacy_arena_router(self):
        draw_pos = BOT.index("dp.include_router(admin_arena_draw_edit_router)")
        legacy_pos = BOT.index("dp.include_router(admin_arena_v4_router)")
        self.assertLess(draw_pos, legacy_pos)

    def test_draw_correction_requires_admin(self):
        self.assertIn("callback.from_user.id not in ARENA_ADMIN_IDS", DRAW_HANDLER)


if __name__ == "__main__":
    unittest.main()
