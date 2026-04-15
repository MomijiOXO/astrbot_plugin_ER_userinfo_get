from __future__ import annotations
from typing import Any, Optional
from urllib.parse import quote
import requests
class PlayerNotFoundError(Exception):
    pass
import time

class ERApiClient:
    BASE_URL = "https://er.dakgg.io/api/v1"

    def __init__(
        self,
        timeout: int = 20,
        user_agent: str = "Mozilla/5.0",
    ):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "application/json,text/plain,*/*",
        })

    def _get(self, path: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        resp = self.session.get(url, params=params, timeout=self.timeout)

        if resp.status_code == 404:
            raise PlayerNotFoundError("player not found")

        try:
            resp.raise_for_status()
        except requests.HTTPError:
            try:
                data = resp.json()
                message = str(data.get("message", "")).lower()
                code = str(data.get("code", "")).lower()

                if "not found" in message or "player" in message and "not found" in message:
                    raise PlayerNotFoundError("player not found")
                if code in {"player_not_found", "not_found"}:
                    raise PlayerNotFoundError("player not found")
            except ValueError:
                pass
            raise

        data = resp.json()

        if isinstance(data, dict):
            message = str(data.get("message", "")).lower()
            code = str(data.get("code", "")).lower()

            if "not found" in message or code in {"player_not_found", "not_found"}:
                raise PlayerNotFoundError("player not found")

        return data

    def get_profile(self, player_name: str, season: str = "SEASON_19") -> dict[str, Any]:
        return self._get(
            f"/players/{player_name}/profile",
            params={"season": season},
        )
    
    def sync_player_by_name(self, player_name: str) -> dict[str, Any]:
        encoded_name = quote(player_name, safe="")
        url = f"https://er.dakgg.io/api/v0/rpc/player-sync/by-name/{encoded_name}"

        headers = {
            "User-Agent": self.session.headers.get("User-Agent", "Mozilla/5.0"),
            "Accept": "application/json,text/plain,*/*",
            "Referer": f"https://dak.gg/er/players/{encoded_name}",
            "Origin": "https://dak.gg",
        }

        resp = self.session.get(url, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            return {"ok": True, "text": resp.text}

    def sync_and_wait_for_profile(
        self,
        player_name: str,
        season: str = "SEASON_19",
        max_attempts: int = 6,
        interval_seconds: float = 2.0,
    ) -> dict[str, Any]:
        before_profile = self.get_profile(player_name, season=season)
        before_synced_at = int(before_profile.get("player", {}).get("syncedAt", 0) or 0)

        self.sync_player_by_name(player_name)

        last_profile = before_profile
        for _ in range(max_attempts):
            time.sleep(interval_seconds)
            current_profile = self.get_profile(player_name, season=season)
            current_synced_at = int(current_profile.get("player", {}).get("syncedAt", 0) or 0)

            last_profile = current_profile
            if current_synced_at > before_synced_at:
                return current_profile

        return last_profile

    def get_matches(
        self,
        player_name: str,
        season: str = "SEASON_19",
        matching_mode: str = "RANK",
        team_mode: str = "ALL",
        page: int = 1,
    ) -> dict[str, Any]:
        return self._get(
            f"/players/{player_name}/matches",
            params={
                "season": season,
                "matchingMode": matching_mode,
                "teamMode": team_mode,
                "page": page,
            },
        )

    def get_union_teams(self, player_name: str, season: str = "SEASON_19") -> dict[str, Any]:
        return self._get(
            f"/players/{player_name}/union-teams",
            params={"season": season},
        )

    def get_all_matches(
        self,
        player_name: str,
        season: str = "SEASON_19",
        matching_mode: str = "ALL",
        team_mode: str = "ALL",
        max_pages: int = 20,
    ) -> list[dict[str, Any]]:
        all_matches: list[dict[str, Any]] = []

        for page in range(1, max_pages + 1):
            data = self.get_matches(
                player_name=player_name,
                season=season,
                matching_mode=matching_mode,
                team_mode=team_mode,
                page=page,
            )
            matches = data.get("matches", [])
            if not matches:
                break
            all_matches.extend(matches)

        return all_matches