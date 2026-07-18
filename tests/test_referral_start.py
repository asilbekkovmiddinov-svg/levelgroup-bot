import unittest

from services.referral import referral_code_from_start


class ReferralStartPayloadTests(unittest.TestCase):
    def test_referral_start_payload_validation(self):
        cases = [
            ("/start ref_abc_DEF-123", "abc_DEF-123"),
            ("/start", None),
            ("/start ordinary_payload", None),
            ("/start ref_", None),
            ("/start ref_bad.code", None),
            (None, None),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(referral_code_from_start(text), expected)
