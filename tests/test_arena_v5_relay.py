import unittest

from handlers.arena_relay import _match_text, arena_token_from_start
from handlers.start import subscription_keyboard


class ArenaV5RelayTests(unittest.TestCase):
    def test_arena_start_token_is_strictly_parsed(self):
        token = "a" * 24
        self.assertEqual(arena_token_from_start(f"/start arena_{token}"), token)
        self.assertIsNone(arena_token_from_start("/start ref_code"))
        self.assertIsNone(arena_token_from_start("/start arena_short"))

    def test_match_context_escapes_efootball_names(self):
        text = _match_text({
            "id": 152,
            "player_a": {"efootball_username": "KING <PES>"},
            "player_b": {"efootball_username": "ASILBEK"},
        })
        self.assertIn("№152 MATCH", text)
        self.assertIn("KING &lt;PES&gt;", text)
        self.assertNotIn("KING <PES>", text)

    def test_subscription_gate_preserves_safe_arena_token(self):
        token = "a" * 32
        keyboard = subscription_keyboard([], token)
        callback_data = keyboard.inline_keyboard[-1][0].callback_data
        self.assertEqual(
            callback_data,
            f"check_required_channels:arena_{token}",
        )
        self.assertLessEqual(len(callback_data), 64)


if __name__ == "__main__":
    unittest.main()
