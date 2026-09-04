from pathlib import Path


def test_bot_has_database_backed_subscription_admin_flow():
    handler = Path("handlers/admin_subscription.py").read_text(encoding="utf-8")
    api = Path("services/api.py").read_text(encoding="utf-8")
    bot = Path("bot.py").read_text(encoding="utf-8")
    start = Path("handlers/start.py").read_text(encoding="utf-8")

    assert 'Command("obuna_admin")' in handler
    assert "subadmin:add" in handler
    assert "subadmin:edit:" in handler
    assert "subadmin:delete:" in handler
    assert "validate_channel_access" in handler
    assert "/internal/subscription/channels" in api
    assert "admin_subscription_router" in bot
    assert "await get_subscription_channels()" in start
    assert "REQUIRED_CHANNELS" not in Path("config.py").read_text(encoding="utf-8")
