from pathlib import Path


def test_admin_coin_chat_exposes_quick_actions_and_fsm():
    source=(Path(__file__).parents[1]/"handlers"/"admin_coin_chat.py").read_text()
    for value in ("REQUEST_CODE","ACCEPT_CODE","WRONG_CODE","RESEND_CODE","CLAIM","COMPLETE","REJECT","CREDENTIALS"):
        assert value in source
    assert 'Command("coin_chats")' in source
    assert "CoinChatState.message" in source
    assert "protect_content=True" in source
    assert 'result["data"]' not in source
    assert 'result["view_url"]' in source
    assert "Bir martalik credential oynasi" in source
