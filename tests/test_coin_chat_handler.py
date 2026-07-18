from pathlib import Path


def test_admin_coin_chat_exposes_quick_actions_and_fsm():
    source=(Path(__file__).parents[1]/"handlers"/"admin_coin_chat.py").read_text()
    for value in ("OTP_SENT","ACCEPT_CODE","WRONG_CODE","RESEND_CODE","CLAIM","COMPLETE","REJECT"):
        assert value in source
    assert 'Command("coin_chats")' in source
    assert "CoinChatState.message" in source
    assert "protect_content=True" in source
    assert 'result["data"]' not in source
    assert "CREDENTIALS" not in source
    assert "open_coin_credentials" not in source
    assert "render_private(callback" in source
    assert "callback.bot.send_message(callback.from_user.id" in source
    assert "protect_content=True" in source
    assert "await render(callback.message,kind,int(raw_id))" not in source
    assert "operator_id in ADMIN_USER_IDS" in source
    assert "get_chat_member" not in source
    assert "Kodni yuboring" not in source
    assert 'F.data.startswith("coinchatopen:")' in source
    assert 'callback_data=f"coinchatopen:{x[\'order_type\']}:{x[\'order_id\']}"' in source
    assert "COMPLETED_ORDERS_CHANNEL_ID" in source
    assert "send_terminal_order" in source
    assert 'kind == "SHOP"' not in source
    assert "coinshop:" not in source


def test_coin_shop_uses_channel_claim_and_terminal_flow_without_order_chat():
    source=(Path(__file__).parents[1]/"handlers"/"admin_coin_shop.py").read_text()
    assert 'F.data.startswith("coinshop:")' in source
    assert "claim_shop_order" in source
    assert "complete_shop_order" in source
    assert "reject_shop_order" in source
    assert "✅ Buyurtma bajarildi" in source
    assert "❌ Buyurtma rad etildi" in source
    assert "await callback.message.delete()" in source
    assert "ADMIN_CHAT_ID" in source
    assert "COMPLETED_ORDERS_CHANNEL_ID" in source
    assert "Order raqami" in source
    completed=source.split("COMPLETED_ORDERS_CHANNEL_ID", 2)[-1]
    assert "Order raqami" not in completed
    assert "Buyurtma chati" not in source
    assert "credential" not in source.lower()
