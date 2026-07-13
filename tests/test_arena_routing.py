import ast
import sys
import types
import unittest
from pathlib import Path


try:
    import dotenv  # noqa: F401
except ModuleNotFoundError:
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda: None
    sys.modules["dotenv"] = dotenv

from services.arena_links import ArenaMiniAppConfigError, build_arena_miniapp_url


ROOT = Path(__file__).resolve().parents[1]


class ArenaRoutingTests(unittest.TestCase):
    def test_miniapp_redirect_is_https_and_preserves_existing_query(self):
        url = build_arena_miniapp_url(
            base_url="https://miniapp.example/app?lang=uz",
            action="ready",
            match_id=42,
        )
        self.assertEqual(
            url,
            "https://miniapp.example/app?lang=uz&section=arena&action=ready&match_id=42",
        )

    def test_missing_or_insecure_miniapp_url_is_rejected(self):
        for url in ("", "http://miniapp.example", "javascript:alert(1)"):
            with self.assertRaises(ArenaMiniAppConfigError):
                build_arena_miniapp_url(base_url=url)

    def test_legacy_user_handler_does_not_import_or_call_arena_api(self):
        source = (ROOT / "handlers" / "match.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        match_api_imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "services.match_api":
                match_api_imports.update(alias.name for alias in node.names)
        called_names = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }

        self.assertEqual(
            match_api_imports, {"ArenaApiError", "upload_internal_evidence"}
        )
        for forbidden in {
            "create_match",
            "accept_match",
            "set_player_ready",
            "create_room_code",
            "upload_result_screenshot",
        }:
            self.assertNotIn(forbidden, called_names)
        self.assertIn("WebAppInfo", source)

    def test_admin_handler_uses_moderation_service_only(self):
        source = (ROOT / "handlers" / "admin_match.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        match_api_imports = set()
        moderation_imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "services.match_api":
                match_api_imports.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module == "services.arena_moderation":
                moderation_imports.update(alias.name for alias in node.names)

        self.assertEqual(match_api_imports, set())
        self.assertIn("apply_arena_decision", moderation_imports)

        moderation_source = (ROOT / "services" / "arena_moderation.py").read_text(
            encoding="utf-8"
        )
        moderation_tree = ast.parse(moderation_source)
        moderation_api_imports = set()
        for node in ast.walk(moderation_tree):
            if isinstance(node, ast.ImportFrom) and node.module == "services.match_api":
                moderation_api_imports.update(alias.name for alias in node.names)
        self.assertEqual(moderation_api_imports, {"ArenaApiError", "resolve_match"})
        self.assertIn("ArenaDecision.CANCEL", source)
        for label in (
            "🏆 Player 1 Win",
            "🏆 Player 2 Win",
            "⚙️ Technical Win",
            "💰 Refund",
            "❌ Cancel",
        ):
            self.assertIn(label, source)
        self.assertIn('"✅ <b>Decision applied</b>', source)
        self.assertIn("reply_markup=None", source)

    def test_worker_uses_only_internal_arena_api_methods(self):
        source = (ROOT / "bot.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        match_api_imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "services.match_api":
                match_api_imports.update(alias.name for alias in node.names)

        self.assertEqual(
            match_api_imports,
            {
                "finish_ready_check",
                "get_due_scheduled_matches",
                "get_expired_ready_matches",
                "start_ready_check",
            },
        )
        self.assertNotIn("Arena ready start item error:", source)
        self.assertNotIn("Arena ready finish item error:", source)


if __name__ == "__main__":
    unittest.main()
