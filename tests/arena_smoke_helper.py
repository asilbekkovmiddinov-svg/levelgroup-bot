from copy import deepcopy


class ArenaSmokeBackend:
    """Stateful contract fake for Bot/API release smoke tests."""

    def __init__(self):
        self.matches = {}
        self.calls = []
        self.next_id = 1

    @staticmethod
    def _identity(init_data):
        identities = {"creator-init": 1001, "opponent-init": 2002}
        return identities.get(init_data)

    def _match(self, match_id):
        return self.matches[match_id]

    async def request(
        self,
        method,
        path,
        *,
        init_data=None,
        internal=False,
        json=None,
        params=None,
    ):
        self.calls.append(
            {
                "method": method,
                "path": path,
                "init_data": init_data,
                "internal": internal,
                "json": deepcopy(json),
                "params": deepcopy(params),
            }
        )
        identity = self._identity(init_data)

        if method == "POST" and path == "/matches/":
            match_id = self.next_id
            self.next_id += 1
            match = {
                "id": match_id,
                "creator_telegram_id": identity,
                "opponent_telegram_id": None,
                "efc_amount": str(json["stake_efc"]),
                "winner_reward": str(json["stake_efc"] * 2),
                "status": "WAITING_PLAYER",
                "creator_ready": False,
                "opponent_ready": False,
                "room_code": None,
                "creator_screenshot": None,
                "creator_video": None,
                "opponent_screenshot": None,
                "opponent_video": None,
                "winner_telegram_id": None,
            }
            self.matches[match_id] = match
            return deepcopy(match)

        if path.endswith("/accept"):
            match = self._match(int(path.split("/")[2]))
            match["opponent_telegram_id"] = identity
            match["status"] = "WAITING_READY"
            return deepcopy(match)

        if path.endswith("/start-ready-check"):
            assert internal is True
            return deepcopy(self._match(int(path.split("/")[2])))

        if path.endswith("/ready"):
            match = self._match(int(path.split("/")[2]))
            if identity == match["creator_telegram_id"]:
                match["creator_ready"] = True
            elif identity == match["opponent_telegram_id"]:
                match["opponent_ready"] = True
            return deepcopy(match)

        if path.endswith("/finish-ready-check"):
            assert internal is True
            match = self._match(int(path.split("/")[2]))
            match["status"] = "ROOM_READY"
            return deepcopy(match)

        if path.endswith("/room-code"):
            match = self._match(int(path.split("/")[2]))
            match["room_code"] = json["room_code"]
            match["status"] = "PLAYING"
            return deepcopy(match)

        if path == "/matches/internal/evidence":
            assert internal is True
            match = self._match(json["match_id"])
            prefix = (
                "creator"
                if json["telegram_id"] == match["creator_telegram_id"]
                else "opponent"
            )
            for media in ("screenshot", "video"):
                field = f"{media}_file_id"
                if field in json:
                    key = f"{prefix}_{media}"
                    if match[key]:
                        raise AssertionError("duplicate evidence request")
                    match[key] = json[field]
            evidence_keys = (
                "creator_screenshot",
                "creator_video",
                "opponent_screenshot",
                "opponent_video",
            )
            if all(match[key] for key in evidence_keys):
                match["status"] = "WAITING_ADMIN"
            return deepcopy(match)

        if path.endswith("/resolve"):
            assert internal is True
            match = self._match(int(path.split("/")[2]))
            decision = json.get("decision")
            if decision == "CANCEL":
                match["status"] = "CANCELLED"
            else:
                match["status"] = "COMPLETED"
            if decision in {"PLAYER_1_WIN", "PLAYER_2_WIN"}:
                match["winner_telegram_id"] = json["winner_telegram_id"]
            match["decision"] = decision
            return deepcopy(match)

        raise AssertionError(f"Unexpected smoke request: {method} {path}")


class RecordingBot:
    def __init__(self, fail=False):
        self.fail = fail
        self.messages = []

    async def send_message(self, **kwargs):
        self.messages.append(kwargs)
        if self.fail:
            raise RuntimeError("private transport detail")
