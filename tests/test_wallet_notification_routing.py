from pathlib import Path
import unittest


class WalletNotificationRoutingTests(unittest.TestCase):
    def test_wallet_routing_uses_production_channel_names(self):
        root = Path(__file__).parents[1]
        deposit = (root / "handlers" / "deposit.py").read_text()
        withdraw = (root / "handlers" / "withdraw.py").read_text()
        admin = (root / "handlers" / "admin_orders.py").read_text()
        assert "chat_id=NEW_ORDERS_CHANNEL_ID" in deposit
        assert "chat_id=NEW_ORDERS_CHANNEL_ID" in withdraw
        assert admin.count("chat_id=ADMIN_CHAT_ID") >= 2
        assert admin.count("chat_id=ADMIN_LOGS_CHANNEL_ID") >= 4
        assert admin.count("chat_id=COMPLETED_ORDERS_CHANNEL_ID") >= 4


if __name__ == "__main__":
    unittest.main()
