# levelgroup-bot

## Arena V5 private relay

Arena V5 keeps both players in their private bot chats. A MiniApp deep link
(`arena_<opaque-token>`) is validated by the backend, and ordinary text/media is
copied only to the active opponent. Result photos are copied to the configured
admin channel and are not downloaded or re-uploaded by the application.

Required configuration:

- `API_URL`
- `INTERNAL_API_KEY` (must match the backend)
- `ARENA_ADMIN_CHANNEL_ID` (falls back to `MATCH_RESULTS_CHANNEL_ID`)

The bot must be an administrator in the results channel. Deploy the backend
schema/API before deploying this bot version.
