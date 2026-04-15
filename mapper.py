from __future__ import annotations

from datetime import datetime
from typing import Any

from .asset_manager import AssetManager


AREA_NAME_MAP_ZH = {
    10: "港口",
    20: "仓库",
    30: "池塘",
    40: "小溪",
    50: "沙滩",
    60: "上城区",
    70: "小巷",
    80: "加油站",
    90: "酒店",
    100: "警察局",
    110: "消防局",
    120: "医院",
    130: "寺庙",
    140: "射箭场",
    150: "墓地",
    160: "森林",
    170: "工厂",
    180: "教堂",
    190: "学校",
}


class DataMapper:
    def __init__(self, assets: AssetManager, seasons_data: list[dict[str, Any]] | None = None):
        self.assets = assets
        self.seasons = seasons_data or []

    def build_render_data(
        self,
        profile_data: dict[str, Any],
        matches_data: dict[str, Any],
        match_count: int = 10,
    ) -> dict[str, Any]:
        return {
            "player": self._build_player(profile_data),
            "summary": self._build_summary(profile_data),
            "common_heroes": self._build_common_heroes(profile_data),
            "matches": self._build_matches(matches_data, match_count),
        }

    # ============================================================
    # 排名 / 赛季
    # ============================================================

    def _season_type_to_id(self, season_type: str) -> int:
        for season in self.seasons:
            if season.get("type") == season_type:
                return int(season.get("id", -1))
        return -1

    def _get_rank_overview(self, profile_data: dict[str, Any]) -> dict[str, Any]:
        overviews = profile_data.get("playerSeasonOverviews", [])

        candidates: list[dict[str, Any]] = []
        for item in overviews:
            if "rank" not in item:
                continue
            candidates.append(item)

        for item in candidates:
            if int(item.get("matchingModeId", -1)) == 3 and int(item.get("teamModeId", -1)) == 3:
                return item

        for item in candidates:
            if int(item.get("matchingModeId", -1)) == 3:
                return item

        return candidates[0] if candidates else {}

    def _get_rank_value(self, profile_data: dict[str, Any], scope: str) -> int:
        overview = self._get_rank_overview(profile_data)
        return int(overview.get("rank", {}).get(scope, {}).get("rank", 0) or 0)

    def _get_rank_size(self, profile_data: dict[str, Any], scope: str) -> int:
        overview = self._get_rank_overview(profile_data)
        return int(overview.get("rank", {}).get(scope, {}).get("rankSize", 0) or 0)

    def _get_rank_percent(self, profile_data: dict[str, Any], scope: str) -> float:
        rank = self._get_rank_value(profile_data, scope)
        rank_size = self._get_rank_size(profile_data, scope)
        if rank <= 0 or rank_size <= 0:
            return 0.0
        return rank / rank_size * 100

    def _get_current_season(self, profile_data: dict[str, Any]) -> dict[str, Any]:
        player_seasons = profile_data.get("playerSeasons", [])

        for item in player_seasons:
            if "tierId" in item or "mmr" in item:
                return item

        return {}

    # ============================================================
    # 玩家头部
    # ============================================================

    def _build_player(self, profile_data: dict[str, Any]) -> dict[str, Any]:
        player = profile_data.get("player", {})
        season_info = self._get_current_season(profile_data)
        rank_overview = self._get_rank_overview(profile_data)

        tier_id = int(season_info.get("tierId", 0) or rank_overview.get("tierId", 0) or 0)
        mmr = int(season_info.get("mmr", 0) or rank_overview.get("mmr", 0) or 0)
        tier_mmr = int(season_info.get("tierMmr", 0) or rank_overview.get("tierMmr", 0) or 0)

        return {
            "name": player.get("name", ""),
            "level": int(player.get("accountLevel", 0) or 0),
            "mmr": mmr,

            "tier_id": tier_id,
            "tier_name": self.assets.get_tier_name(tier_id),
            "tier_icon": self.assets.get_tier_icon_path(tier_id),
            "tier_full": self.assets.get_tier_full_path(tier_id),
            "tier_mmr": tier_mmr,

            "mmr_chart": self._build_mmr_chart(profile_data),

            "rank_global": self._get_rank_value(profile_data, "global"),
            "rank_global_size": self._get_rank_size(profile_data, "global"),
            "rank_global_percent": self._get_rank_percent(profile_data, "global"),

            "rank_local": self._get_rank_value(profile_data, "local"),
            "rank_local_size": self._get_rank_size(profile_data, "local"),
            "rank_local_percent": self._get_rank_percent(profile_data, "local"),
        }

    # ============================================================
    # overview 查找
    # ============================================================

    def _find_overview(
        self,
        profile_data: dict[str, Any],
        matching_mode_id: int | None = None,
        team_mode_id: int | None = None,
        require_rank: bool = False,
    ) -> dict[str, Any] | None:
        overviews = profile_data.get("playerSeasonOverviews", [])

        for item in overviews:
            if matching_mode_id is not None and int(item.get("matchingModeId", -1)) != int(matching_mode_id):
                continue
            if team_mode_id is not None and int(item.get("teamModeId", -1)) != int(team_mode_id):
                continue
            if require_rank and "rank" not in item:
                continue
            return item

        return overviews[0] if overviews else None

    def _find_all_overview(self, profile_data: dict[str, Any]) -> dict[str, Any] | None:
        overviews = profile_data.get("playerSeasonOverviews", [])

        for item in overviews:
            if int(item.get("matchingModeId", -1)) == 0:
                return item

        return self._find_overview(profile_data, None)

    def _find_rank_overview(self, profile_data: dict[str, Any]) -> dict[str, Any] | None:
        overview = self._get_rank_overview(profile_data)
        return overview or None

    # ============================================================
    # 特性辅助
    # ============================================================

    def _get_trait_sub1_icon(self, match: dict[str, Any]) -> str:
        subs = match.get("traitFirstSub", [])
        if not subs:
            return ""

        trait = self.assets.build_trait_render_data(int(subs[0]))
        return trait.get("icon", "")

    def _get_trait_group_key(self, match: dict[str, Any]) -> str:
        core = match.get("traitFirstCore")
        if not core:
            return ""

        trait = self.assets.get_trait_skill(int(core))
        return trait.get("group", "")

    def _get_trait_group_name(self, match: dict[str, Any]) -> str:
        group_key = self._get_trait_group_key(match)
        if not group_key:
            return ""

        group = self.assets.get_trait_group(group_key)
        return group.get("name", "")

    def _get_trait_names(self, match: dict[str, Any]) -> list[str]:
        result: list[str] = []

        core = match.get("traitFirstCore")
        if core:
            trait = self.assets.get_trait_skill(int(core))
            name = trait.get("name", "")
            if name:
                result.append(name)

        for trait_id in match.get("traitFirstSub", []):
            trait = self.assets.get_trait_skill(int(trait_id))
            name = trait.get("name", "")
            if name:
                result.append(name)

        for trait_id in match.get("traitSecondSub", []):
            trait = self.assets.get_trait_skill(int(trait_id))
            name = trait.get("name", "")
            if name:
                result.append(name)

        return result

    def _get_trait_group_icon(self, match: dict[str, Any]) -> str:
        group_key = self._get_trait_group_key(match)
        if not group_key:
            return ""
        return self.assets.get_trait_group_icon_path(group_key)

    def _get_trait_core_icon(self, match: dict[str, Any]) -> str:
        core = match.get("traitFirstCore")
        if not core:
            return ""
        trait = self.assets.build_trait_render_data(int(core))
        return trait.get("icon", "")

    def _get_trait_second_group_key(self, match: dict[str, Any]) -> str:
        second_subs = match.get("traitSecondSub", [])
        if not second_subs:
            return ""

        trait = self.assets.get_trait_skill(int(second_subs[0]))
        return trait.get("group", "")

    def _get_trait_second_group_icon(self, match: dict[str, Any]) -> str:
        group_key = self._get_trait_second_group_key(match)
        if not group_key:
            return ""
        return self.assets.get_trait_group_icon_path(group_key)

    # ============================================================
    # MMR 折线图
    # ============================================================

    def _build_mmr_chart(self, profile_data: dict[str, Any]) -> list[dict[str, Any]]:
        overview = self._get_rank_overview(profile_data)

        if not overview:
            overviews = profile_data.get("playerSeasonOverviews", [])
            if overviews:
                overview = overviews[0]

        if not overview:
            return []

        mmr_stats = overview.get("mmrStats", [])
        temp = []

        for row in mmr_stats:
            if not isinstance(row, list) or len(row) < 2:
                continue

            raw_date = str(row[0])
            value = row[1]

            if len(raw_date) == 8:
                label = f"{raw_date[4:6]}/{raw_date[6:8]}"
            else:
                label = raw_date

            temp.append({
                "label": label,
                "value": value,
                "raw_date": raw_date,
            })

        if not temp:
            return []

        latest_points = temp[:6]
        latest_points.reverse()

        return [{"label": p["label"], "value": p["value"]} for p in latest_points]

    # ============================================================
    # 汇总统计（12字段）
    # ============================================================

    def _build_summary(self, profile_data: dict[str, Any]) -> dict[str, Any]:
        overview = self._find_rank_overview(profile_data)

        if overview is None:
            return {
                "avg_tk": 0.0,
                "win_rate": 0.0,
                "play": 0,
                "avg_kill": 0.0,
                "top2_rate": 0.0,
                "avg_damage": 0.0,
                "avg_assist": 0.0,
                "top3_rate": 0.0,
                "avg_rank": 0.0,
                "avg_monster_kill": 0.0,
                "avg_vf_credit": 0.0,
                "avg_view_contribution": 0.0,
            }

        play_raw = int(overview.get("play", 0) or 0)
        play = max(play_raw, 1)

        win = float(overview.get("win", 0) or 0)
        top2 = float(overview.get("top2", 0) or 0)
        top3 = float(overview.get("top3", 0) or 0)

        team_kill = float(overview.get("teamKill", 0) or 0)
        player_kill = float(overview.get("playerKill", 0) or 0)
        player_assistant = float(overview.get("playerAssistant", 0) or 0)
        damage_to_player = float(overview.get("damageToPlayer", 0) or 0)
        place = float(overview.get("place", 0) or 0)
        monster_kill = float(overview.get("monsterKill", 0) or 0)
        total_gain_vf_credit = float(overview.get("totalGainVFCredit", 0) or 0)
        view_contribution = float(overview.get("viewContribution", 0) or 0)

        return {
            "avg_tk": round(team_kill / play, 2),
            "win_rate": round(win / play * 100, 1),
            "play": play_raw,
            "avg_kill": round(player_kill / play, 2),
            "top2_rate": round(top2 / play * 100, 1),
            "avg_damage": round(damage_to_player / play, 1),
            "avg_assist": round(player_assistant / play, 2),
            "top3_rate": round(top3 / play * 100, 1),
            "avg_rank": round(place / play, 2),
            "avg_monster_kill": round(monster_kill / play, 1),
            "avg_vf_credit": round(total_gain_vf_credit / play, 0),
            "avg_view_contribution": round(view_contribution / play, 2),
        }

    # ============================================================
    # 常用英雄（rank）
    # ============================================================

    def _build_common_heroes(self, profile_data: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
        overview = self._find_rank_overview(profile_data)

        if overview is None:
            return []

        result = []
        for stat in overview.get("characterStats", [])[:limit]:
            char_id = int(stat.get("key", 0) or 0)
            play = int(stat.get("play", 0) or 0)
            if play <= 0:
                continue

            avg_kill = (stat.get("playerKill", 0) or 0) / play
            avg_assist = (stat.get("playerAssistant", 0) or 0) / play
            avg_damage = (stat.get("damageToPlayer", 0) or 0) / play
            avg_rank = (stat.get("place", 0) or 0) / play

            result.append({
                "character_id": char_id,
                "character_name": self.assets.get_character_name(char_id),
                "character_icon": self.assets.get_character_icon_path(char_id),
                "play": play,
                "win": int(stat.get("win", 0) or 0),
                "win_rate": round((stat.get("win", 0) or 0) / play * 100, 1),
                "avg_rank": round(avg_rank, 2),
                "avg_kill": round(avg_kill, 2),
                "avg_assist": round(avg_assist, 2),
                "avg_damage": round(avg_damage, 1),
                "rp": int(stat.get("mmrGain", 0) or 0),
            })

        return result

    # ============================================================
    # 对局
    # ============================================================

    def _build_matches(self, matches_data: dict[str, Any], match_count: int) -> list[dict[str, Any]]:
        result = []
        for match in matches_data.get("matches", [])[:match_count]:
            result.append(self._build_single_match(match))
        return result

    def _build_single_match(self, match: dict[str, Any]) -> dict[str, Any]:
        char_id = int(match.get("characterNum", 0) or 0)
        weapon_id = int(match.get("bestWeapon", 0) or 0)
        tactical_id = int(match.get("tacticalSkillGroup", 0) or 0)

        skin_id = int(match.get("skinCode", 0) or 0)
        skin_icon = self.assets.get_character_skin_icon_path(skin_id) if skin_id else ""

        matching_mode_raw = match.get("matchingMode", "")
        matching_mode = str(matching_mode_raw or "").upper()
        is_rank_match = matching_mode == "RANK" or int(matching_mode_raw or 0) == 3
        mode_label = "排位" if is_rank_match else "一般"

        path_id = (
            match.get("routeIdOfStart")
            or match.get("pathId")
            or match.get("routeId")
            or match.get("routeID")
            or 0
        )

        place_of_start = int(match.get("placeOfStart", 0) or 0)
        start_area = AREA_NAME_MAP_ZH.get(place_of_start, "")

        return {
            "game_id": match.get("gameId"),
            "rank": int(match.get("gameRank", 0) or 0),

            "character_id": char_id,
            "character_name": self.assets.get_character_name(char_id),
            "character_icon": skin_icon or self.assets.get_character_icon_path(char_id),
            "skin_id": skin_id,

            "weapon_id": weapon_id,
            "weapon_name": self.assets.get_mastery_name(weapon_id),
            "weapon_icon": self.assets.get_mastery_icon_path(weapon_id),

            "kda": f"{int(match.get('playerKill', 0) or 0)}/{int(match.get('playerDeaths', 0) or 0)}/{int(match.get('playerAssistant', 0) or 0)}",
            "kills": int(match.get("playerKill", 0) or 0),
            "deaths": int(match.get("playerDeaths", 0) or 0),
            "assists": int(match.get("playerAssistant", 0) or 0),
            "team_kill": int(match.get("teamKill", 0) or 0),

            "damage": int(match.get("damageToPlayer", 0) or 0),

            "mmr_before": int(match.get("mmrBefore", 0) or 0),
            "mmr_after": int(match.get("mmrAfter", 0) or 0),
            "mmr_change": int(match.get("mmrGain", 0) or 0),

            "matching_mode": matching_mode,
            "is_rank_match": is_rank_match,
            "mode_label": mode_label,

            "path_id": int(path_id or 0),
            "start_area": str(start_area or ""),

            "start_time": self._format_time(match.get("startDtm", "")),

            "tactical_skill": self.assets.build_tactical_skill_render_data(tactical_id) if tactical_id else {},
            "tactical_skill_level": int(match.get("tacticalSkillLevel", 0) or 0),

            "traits": self._build_traits(match),
            "trait_core_icon": self._get_trait_core_icon(match),
            "trait_second_group_icon": self._get_trait_second_group_icon(match),

            "items": self._build_items(match),
        }

    # ============================================================
    # 装备 / traits / 时间
    # ============================================================

    def _build_items(self, match: dict[str, Any]) -> list[dict[str, Any]]:
        items = []
        for item_id in match.get("equipment", []):
            try:
                item_id = int(item_id)
            except Exception:
                continue
            items.append(self.assets.build_item_render_data(item_id))
        return items

    def _build_traits(self, match: dict[str, Any]) -> list[dict[str, Any]]:
        result = []

        core = match.get("traitFirstCore")
        if core:
            result.append(self.assets.build_trait_render_data(int(core)))

        for trait_id in match.get("traitFirstSub", []):
            result.append(self.assets.build_trait_render_data(int(trait_id)))

        for trait_id in match.get("traitSecondSub", []):
            result.append(self.assets.build_trait_render_data(int(trait_id)))

        return result

    def _format_time(self, value: str) -> str:
        if not value:
            return ""

        try:
            dt = datetime.fromisoformat(value)
            return dt.strftime("%m-%d %H:%M")
        except Exception:
            return value