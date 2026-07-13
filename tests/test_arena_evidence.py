import ast
import sys
import tempfile
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if "dotenv" not in sys.modules:
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda: None
    sys.modules["dotenv"] = dotenv

from services.arena_evidence_state import (
    ArenaEvidenceStore,
    DuplicateEvidenceError,
)


class ArenaEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tempdir.name) / "evidence.db")
        self.store = ArenaEvidenceStore(self.path)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_screenshot_then_video_completes_progress(self):
        self.store.start(1001, 42)
        screenshot = self.store.mark_accepted(
            1001, media_type="screenshot", file_id="photo-id"
        )
        self.assertEqual(screenshot.screenshot_file_id, "photo-id")
        self.assertFalse(screenshot.complete)

        complete = self.store.mark_accepted(
            1001, media_type="video", file_id="video-id"
        )
        self.assertEqual(complete.video_file_id, "video-id")
        self.assertTrue(complete.complete)

    def test_video_then_screenshot_completes_progress(self):
        self.store.start(1001, 42)
        video = self.store.mark_accepted(
            1001, media_type="video", file_id="video-id"
        )
        self.assertFalse(video.complete)
        complete = self.store.mark_accepted(
            1001, media_type="screenshot", file_id="photo-id"
        )
        self.assertTrue(complete.complete)

    def test_duplicate_slot_is_blocked(self):
        self.store.start(1001, 42)
        self.store.mark_accepted(1001, media_type="screenshot", file_id="photo-id")
        with self.assertRaises(DuplicateEvidenceError):
            self.store.mark_accepted(
                1001, media_type="screenshot", file_id="other-photo"
            )

    def test_restart_recovers_persisted_session(self):
        self.store.start(1001, 42)
        self.store.mark_accepted(1001, media_type="video", file_id="video-id")

        recovered = ArenaEvidenceStore(self.path).get(1001)
        self.assertEqual(recovered.match_id, 42)
        self.assertEqual(recovered.video_file_id, "video-id")
        self.assertIsNone(recovered.screenshot_file_id)

    def test_handler_contract_uses_only_internal_evidence_wrapper(self):
        source = (ROOT / "handlers" / "match.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "services.match_api":
                imports.update(alias.name for alias in node.names)
        self.assertIn("upload_internal_evidence", imports)
        self.assertNotIn("upload_result_screenshot", imports)
        self.assertIn("telegram_id=message.from_user.id", source)
        self.assertIn("match_id=session.match_id", source)
        for status in ("409", "401", "403", "404", "422", "500"):
            self.assertIn(status, source)


if __name__ == "__main__":
    unittest.main()
