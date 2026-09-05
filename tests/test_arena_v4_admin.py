import asyncio
import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from handlers import admin_arena_v4
from services import arena_v4_api


def run(awaitable):
    return asyncio.run(awaitable)


def test_review_and_appeal_queues_are_separate():
    recorder = AsyncMock(return_value={"reviews": []})
    with patch.object(arena_v4_api, "client") as client:
        client.request = recorder
        run(arena_v4_api.list_reviews("INITIAL"))
        run(arena_v4_api.list_reviews("APPEAL"))
    assert recorder.await_args_list[0].kwargs["params"]["review_type"] == "INITIAL"
    assert recorder.await_args_list[1].kwargs["params"]["review_type"] == "APPEAL"
    assert all(
        call.kwargs["params"]["status"] == "PENDING"
        for call in recorder.await_args_list
    )


def test_claim_uses_internal_api_and_admin_identity():
    with patch.object(arena_v4_api, "client") as client:
        client.request = AsyncMock(return_value={"id": 7, "status": "CLAIMED"})
        result = run(arena_v4_api.claim_review(7, 1001))
    assert result["status"] == "CLAIMED"
    call = client.request.await_args
    assert call.args == ("POST", "/internal/arena/reviews/7/claim")
    assert call.kwargs["internal"] is True
    assert call.kwargs["json"] == {"admin_id": 1001}


def test_channel_claim_uses_match_specific_internal_endpoint():
    with patch.object(arena_v4_api, "client") as client:
        client.request = AsyncMock(return_value={"id": 8, "status": "CLAIMED"})
        result = run(arena_v4_api.claim_match_review(42, 1001))
    assert result["status"] == "CLAIMED"
    call = client.request.await_args
    assert call.args == ("POST", "/internal/arena/matches/42/claim")
    assert call.kwargs["internal"] is True
    assert call.kwargs["json"] == {"admin_id": 1001}


def test_submit_score_never_sends_winner():
    with patch.object(arena_v4_api, "client") as client:
        client.request = AsyncMock(
            return_value={"id": 7, "decision": "PLAYER_A_WIN"}
        )
        result = run(arena_v4_api.submit_score(7, 1001, 2, 1))
    payload = client.request.await_args.kwargs["json"]
    assert payload["owner_score"] == 2
    assert payload["opponent_score"] == 1
    assert "winner_id" not in payload
    assert "decision" not in payload
    assert result["decision"] == "PLAYER_A_WIN"


def test_cancel_uses_separate_backend_action():
    with patch.object(arena_v4_api, "client") as client:
        client.request = AsyncMock(return_value={"decision": "CANCEL"})
        run(arena_v4_api.cancel_match(9, 1001))
    call = client.request.await_args
    assert call.args == ("POST", "/internal/arena/reviews/9/cancel")
    assert call.kwargs["idempotency_key"] == "bot:cancel:9:1001"


def test_keep_and_update_score_appeal_actions():
    with patch.object(arena_v4_api, "client") as client:
        client.request = AsyncMock(return_value={"status": "DECIDED"})
        run(arena_v4_api.submit_appeal_decision(5, 1001, "KEEP_RESULT"))
        run(
            arena_v4_api.submit_appeal_decision(
                6, 1001, "UPDATE_SCORE", owner_score=1, opponent_score=4
            )
        )
    keep = client.request.await_args_list[0].kwargs["json"]
    update = client.request.await_args_list[1].kwargs["json"]
    assert keep["action"] == "KEEP_RESULT"
    assert "owner_score" not in keep
    assert update["action"] == "UPDATE_SCORE"
    assert (update["owner_score"], update["opponent_score"]) == (1, 4)


def test_channel_callback_uses_private_admin_fsm_key():
    state = FSMContext(
        storage=MemoryStorage(),
        key=StorageKey(bot_id=77, chat_id=-100123, user_id=1001),
    )
    private = admin_arena_v4._private_admin_state(
        state, bot_id=77, admin_id=1001
    )
    assert private.key.bot_id == 77
    assert private.key.chat_id == 1001
    assert private.key.user_id == 1001


def test_channel_score_stays_on_the_channel_post():
    source = inspect.getsource(admin_arena_v4.start_channel_score)
    assert "edit_reply_markup" in source
    assert "channel_score_keyboard" in source
    assert "_start_private_input" not in source


def test_channel_score_keyboard_is_match_specific_and_keeps_draft_score():
    keyboard = admin_arena_v4.channel_score_keyboard(42, 3, 2)
    buttons = [button for row in keyboard.inline_keyboard for button in row]
    assert any(button.text == "⚽ A 3:2 B" for button in buttons)
    callbacks = [button.callback_data for button in buttons]
    assert "arv4:m:confirm:42:3:2" in callbacks
    assert "arv4:m:cancel:42:3:2" in callbacks
    assert all(len(value) <= 64 for value in callbacks)


def test_start_channel_score_claims_match_before_showing_controls(monkeypatch):
    monkeypatch.setattr(admin_arena_v4, "ARENA_ADMIN_IDS", {1001})
    claim = AsyncMock(return_value={"status": "CLAIMED"})
    monkeypatch.setattr(admin_arena_v4, "claim_match_review", claim)
    callback = SimpleNamespace(
        data="arv4:m:start:42",
        from_user=SimpleNamespace(id=1001),
        message=SimpleNamespace(edit_reply_markup=AsyncMock()),
        answer=AsyncMock(),
    )

    run(admin_arena_v4.start_channel_score(callback))

    claim.assert_awaited_once_with(42, 1001)
    callback.message.edit_reply_markup.assert_awaited_once()


def test_channel_confirmation_submits_score_for_callback_match(monkeypatch):
    monkeypatch.setattr(admin_arena_v4, "ARENA_ADMIN_IDS", {1001})
    submit = AsyncMock(return_value={"decision": "PLAYER_A_WIN"})
    monkeypatch.setattr(admin_arena_v4, "submit_match_score", submit)
    callback = SimpleNamespace(
        data="arv4:m:confirm:42:3:2",
        from_user=SimpleNamespace(id=1001),
        message=SimpleNamespace(edit_reply_markup=AsyncMock()),
        answer=AsyncMock(),
    )

    run(admin_arena_v4.confirm_channel_score(callback))

    submit.assert_awaited_once_with(42, 1001, 3, 2)
    callback.message.edit_reply_markup.assert_awaited_once_with(
        reply_markup=admin_arena_v4.finished_result_edit_keyboard(42)
    )


def test_legacy_channel_score_button_opens_new_inline_controls(monkeypatch):
    monkeypatch.setattr(admin_arena_v4, "ARENA_ADMIN_IDS", {1001})
    claim = AsyncMock(return_value={"status": "CLAIMED"})
    monkeypatch.setattr(admin_arena_v4, "claim_match_review", claim)
    callback = SimpleNamespace(
        data="arv4:match:score:42",
        from_user=SimpleNamespace(id=1001),
        message=SimpleNamespace(edit_reply_markup=AsyncMock()),
        answer=AsyncMock(),
    )

    run(admin_arena_v4.start_channel_score(callback))

    claim.assert_awaited_once_with(42, 1001)
    callback.message.edit_reply_markup.assert_awaited_once()


def test_multi_admin_allowlist(monkeypatch):
    monkeypatch.setattr(admin_arena_v4, "ARENA_ADMIN_IDS", {1001, 2002})
    assert admin_arena_v4.is_arena_admin(1001)
    assert admin_arena_v4.is_arena_admin(2002)
    assert not admin_arena_v4.is_arena_admin(3003)


def test_duplicate_callback_is_blocked_while_first_is_running():
    started = asyncio.Event()
    release = asyncio.Event()

    async def action():
        started.set()
        await release.wait()

    async def scenario():
        first = asyncio.create_task(
            admin_arena_v4._exclusive_action(55, action)
        )
        await started.wait()
        duplicate = await admin_arena_v4._exclusive_action(55, action)
        release.set()
        applied = await first
        return applied, duplicate

    assert run(scenario()) == (True, False)


def test_review_formatter_contains_required_admin_fields():
    detail = {
        "review": {"id": 4, "review_type": "INITIAL"},
        "match": {
            "id": 10,
            "public_id": "ARENA-10",
            "owner_id": 1001,
            "owner_efootball_username": "EF-A",
            "opponent_efootball_username": "EF-B",
            "stake_efc": "500.00",
            "total_pool_efc": "1000.00",
            "commission_efc": "100.00",
            "winner_reward_efc": "900.00",
            "created_at": "2026-08-01T10:00:00+00:00",
        },
        "player_a": {
            "telegram_id": 1001,
            "display_name": "Player A",
            "username": "player_a",
        },
        "player_b": {
            "telegram_id": 2002,
            "display_name": "Player B",
            "username": "player_b",
        },
        "screenshots": [{"uploaded_at": "2026-08-01T10:30:00+00:00"}],
    }
    text = admin_arena_v4.format_review(detail)
    for value in (
        "ARENA-10",
        "Player A",
        "@player_a",
        "EF-A",
        "Player B",
        "@player_b",
        "EF-B",
        "500.00",
        "1000.00",
        "100.00",
        "900.00",
    ):
        assert value in text
