import pytest

from services.referral import referral_code_from_start


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("/start ref_abc_DEF-123", "abc_DEF-123"),
        ("/start", None),
        ("/start ordinary_payload", None),
        ("/start ref_", None),
        ("/start ref_bad.code", None),
        (None, None),
    ],
)
def test_referral_start_payload_validation(text, expected):
    assert referral_code_from_start(text) == expected

