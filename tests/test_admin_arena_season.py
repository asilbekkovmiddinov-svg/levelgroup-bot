from pathlib import Path


def test_bot_has_arena_season_admin_flow():
    handler = Path("handlers/admin_arena_season.py").read_text(encoding="utf-8")
    api = Path("services/arena_v5_api.py").read_text(encoding="utf-8")
    bot = Path("bot.py").read_text(encoding="utf-8")

    assert 'Command("arena_admin")' in handler
    assert "arseason:create" in handler
    assert "arseason:finish-ok:" in handler
    assert "duration_days" in handler
    assert "arseason:duration:" in handler
    assert "yangi referal +3" in handler
    assert '"/internal/arena/v5/seasons"' in api
    assert 'f"/internal/arena/v5/seasons/{season_id}/finish"' in api
    assert 'f"/internal/arena/v5/seasons/{season_id}/duration"' in api
    assert "admin_arena_season_router" in bot
