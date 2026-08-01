import importlib


def test_admin_user_ids_are_parsed_as_explicit_allowlist(monkeypatch):
    monkeypatch.setenv("ADMIN_USER_IDS", "1678146043, 42")
    import config
    importlib.reload(config)
    assert config.ADMIN_USER_IDS == {1678146043, 42}


def test_arena_admin_ids_are_parsed_as_independent_allowlist(monkeypatch):
    monkeypatch.setenv("ARENA_ADMIN_IDS", "101, 202")
    import config
    importlib.reload(config)
    assert config.ARENA_ADMIN_IDS == {101, 202}
