from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_bot_registers_only_arena_v4_admin_router():
    source = (ROOT / "bot.py").read_text(encoding="utf-8")
    assert "handlers.admin_arena_v4" in source
    assert "handlers.admin_match" not in source
    assert "handlers.match" not in source


def test_old_moderation_and_video_fsm_are_removed():
    assert not (ROOT / "handlers" / "admin_match.py").exists()
    assert not (ROOT / "handlers" / "match.py").exists()
    assert not (ROOT / "services" / "arena_moderation.py").exists()
    assert not (ROOT / "services" / "arena_evidence_state.py").exists()
    match_api = (ROOT / "services" / "match_api.py").read_text(encoding="utf-8")
    for forbidden in (
        "resolve_match",
        "Technical Win",
        "winner_telegram_id",
        "upload_internal_evidence",
        "video_file_id",
    ):
        assert forbidden not in match_api


def test_v4_handler_has_no_winner_or_notification_business_logic():
    source = (ROOT / "handlers" / "admin_arena_v4.py").read_text(
        encoding="utf-8"
    )
    assert "submit_score" in source
    assert "cancel_match" in source
    assert "submit_appeal_decision" in source
    assert "Player 1 Win" not in source
    assert "Player 2 Win" not in source
    assert "Technical Win" not in source
    assert "send_arena_notification" not in source
