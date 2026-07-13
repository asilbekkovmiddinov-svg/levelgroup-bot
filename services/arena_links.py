from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from config import ARENA_MINIAPP_URL


class ArenaMiniAppConfigError(ValueError):
    pass


def build_arena_miniapp_url(
    *,
    action: str = "open",
    match_id: int | None = None,
    base_url: str | None = None,
) -> str:
    configured_url = (
        ARENA_MINIAPP_URL if base_url is None else base_url
    ) or ""
    configured_url = configured_url.strip()
    parsed = urlsplit(configured_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ArenaMiniAppConfigError("ARENA_MINIAPP_URL xavfsiz HTTPS manzilga sozlanmagan.")

    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["section"] = "arena"
    query["action"] = action
    if match_id is not None:
        query["match_id"] = str(match_id)

    return urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment)
    )
