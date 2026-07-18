import re


REFERRAL_START_PATTERN = re.compile(r"^ref_([A-Za-z0-9_-]{1,24})$")


def referral_code_from_start(text: str | None) -> str | None:
    parts = (text or "").strip().split(maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "/start":
        return None
    match = REFERRAL_START_PATTERN.fullmatch(parts[1].strip())
    return match.group(1) if match else None
