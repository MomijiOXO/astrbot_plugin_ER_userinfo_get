from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


class AssetManager:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.api_dir = self.data_dir / "cache" / "api"
        self.assets_dir = self.data_dir / "assets"

        self.characters: dict[int, dict[str, Any]] = {}
        self.character_skins: dict[int, dict[str, Any]] = {}
        self.items: dict[int, dict[str, Any]] = {}
        self.tiers: dict[int, dict[str, Any]] = {}
        self.tactical_skills: dict[int, dict[str, Any]] = {}
        self.trait_skills: dict[int, dict[str, Any]] = {}
        self.trait_skill_groups: dict[str, dict[str, Any]] = {}
        self.masteries: dict[int, dict[str, Any]] = {}
        self.skills: dict[int, dict[str, Any]] = {}

        self.reload()

    def reload(self) -> None:
        self.characters = self._load_id_map("characters.json", "characters")
        self.character_skins = self._load_index_map("character_skins_index.json")
        self.items = self._load_id_map("items.json", "items")
        self.tiers = self._load_id_map("tiers.json", "tiers")
        self.tactical_skills = self._load_id_map("tactical_skills.json", "tacticalSkills")
        self.trait_skills = self._load_id_map("trait_skills.json", "traitSkills")
        self.masteries = self._load_id_map("masteries.json", "masteries")
        self.skills = self._load_id_map("skills.json", "skills")
        self.trait_skill_groups = self._load_key_map("trait_skills.json", "traitSkillGroups", "key")

    def _read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"JSON 文件不存在: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_id_map(self, filename: str, root_key: str) -> dict[int, dict[str, Any]]:
        data = self._read_json(self.api_dir / filename)
        result: dict[int, dict[str, Any]] = {}

        for item in data.get(root_key, []):
            item_id = item.get("id")
            if item_id is None:
                continue
            result[int(item_id)] = item

        return result

    def _load_key_map(self, filename: str, root_key: str, key_name: str) -> dict[str, dict[str, Any]]:
        data = self._read_json(self.api_dir / filename)
        result: dict[str, dict[str, Any]] = {}

        for item in data.get(root_key, []):
            key = item.get(key_name)
            if not key:
                continue
            result[str(key)] = item

        return result

    def _load_index_map(self, filename: str) -> dict[int, dict[str, Any]]:
        path = self.api_dir / filename
        if not path.exists():
            return {}

        data = self._read_json(path)
        result: dict[int, dict[str, Any]] = {}

        for k, v in data.items():
            try:
                result[int(k)] = v
            except Exception:
                continue

        return result

    def _find_asset_path(self, folder: str, file_stem: str) -> Optional[Path]:
        base = self.assets_dir / folder
        if not base.exists():
            return None

        for ext in (".png", ".webp", ".jpg", ".jpeg"):
            path = base / f"{file_stem}{ext}"
            if path.exists():
                return path

        return None

    def _path_str(self, path: Optional[Path]) -> str:
        return str(path) if path else ""

    # ---------- 角色 ----------
    def get_character(self, character_id: int) -> dict[str, Any]:
        return self.characters.get(int(character_id), {})

    def get_character_name(self, character_id: int) -> str:
        return self.get_character(character_id).get("name", f"角色{character_id}")

    def get_character_icon_path(self, character_id: int) -> str:
        return self._path_str(self._find_asset_path("characters", str(character_id)))

    def get_character_skin_icon_path(self, skin_id: int) -> str:
        skin = self.character_skins.get(int(skin_id), {})
        file_path = skin.get("file", "")
        if not file_path:
            return ""

        p = Path(file_path)
        if p.exists():
            return str(p)

        p = self.data_dir.parent / file_path
        if p.exists():
            return str(p)

        return ""

    # ---------- 物品 ----------
    def get_item(self, item_id: int) -> dict[str, Any]:
        return self.items.get(int(item_id), {})

    def get_item_name(self, item_id: int) -> str:
        return self.get_item(item_id).get("name", f"物品{item_id}")

    def get_item_icon_path(self, item_id: int) -> str:
        return self._path_str(self._find_asset_path("items", str(item_id)))

    # ---------- 段位 ----------
    def get_tier(self, tier_id: int) -> dict[str, Any]:
        return self.tiers.get(int(tier_id), {})

    def get_tier_name(self, tier_id: int) -> str:
        return self.get_tier(tier_id).get("name", f"段位{tier_id}")

    def get_tier_icon_path(self, tier_id: int) -> str:
        return self._path_str(self._find_asset_path("tiers", str(tier_id)))

    def get_tier_full_path(self, tier_id: int) -> str:
        return self._path_str(self._find_asset_path("tiers_full", str(tier_id)))

    # ---------- 战术技能 ----------
    def get_tactical_skill(self, skill_id: int) -> dict[str, Any]:
        return self.tactical_skills.get(int(skill_id), {})

    def get_tactical_skill_name(self, skill_id: int) -> str:
        return self.get_tactical_skill(skill_id).get("name", f"战术技能{skill_id}")

    def get_tactical_skill_icon_path(self, skill_id: int) -> str:
        return self._path_str(self._find_asset_path("tactical_skills", str(skill_id)))

    # ---------- 特性 ----------
    def get_trait_skill(self, trait_id: int) -> dict[str, Any]:
        return self.trait_skills.get(int(trait_id), {})

    def get_trait_skill_name(self, trait_id: int) -> str:
        return self.get_trait_skill(trait_id).get("name", f"特性{trait_id}")

    def get_trait_skill_icon_path(self, trait_id: int) -> str:
        return self._path_str(self._find_asset_path("trait_skills", str(trait_id)))

    def get_trait_group(self, group_key: str) -> dict[str, Any]:
        return self.trait_skill_groups.get(str(group_key), {})

    def get_trait_group_name(self, group_key: str) -> str:
        return self.get_trait_group(group_key).get("name", str(group_key))

    def get_trait_group_icon_path(self, group_key: str) -> str:
        return self._path_str(self._find_asset_path("trait_skill_groups", str(group_key)))

    # ---------- 武器 / 熟练度 ----------
    def get_mastery(self, mastery_id: int) -> dict[str, Any]:
        return self.masteries.get(int(mastery_id), {})

    def get_mastery_name(self, mastery_id: int) -> str:
        return self.get_mastery(mastery_id).get("name", f"武器{mastery_id}")

    def get_mastery_icon_path(self, mastery_id: int) -> str:
        return self._path_str(self._find_asset_path("masteries", str(mastery_id)))

    # ---------- 角色技能 ----------
    def get_skill(self, skill_id: int) -> dict[str, Any]:
        return self.skills.get(int(skill_id), {})

    def get_skill_name(self, skill_id: int) -> str:
        return self.get_skill(skill_id).get("name", f"技能{skill_id}")

    def get_skill_icon_path(self, skill_id: int) -> str:
        return self._path_str(self._find_asset_path("skills", str(skill_id)))

    def get_character_skills(self, character_id: int) -> list[dict[str, Any]]:
        character_id = int(character_id)
        return [skill for skill in self.skills.values() if int(skill.get("characterId", -1)) == character_id]

    # ---------- 渲染辅助 ----------
    def build_item_render_data(self, item_id: int) -> dict[str, Any]:
        raw = self.get_item(item_id)
        return {
            "id": item_id,
            "name": self.get_item_name(item_id),
            "icon": self.get_item_icon_path(item_id),
            "grade": raw.get("grade", ""),
            "raw": raw,
        }

    def build_character_render_data(self, character_id: int) -> dict[str, Any]:
        return {
            "id": character_id,
            "name": self.get_character_name(character_id),
            "icon": self.get_character_icon_path(character_id),
            "raw": self.get_character(character_id),
        }

    def build_tactical_skill_render_data(self, skill_id: int) -> dict[str, Any]:
        return {
            "id": skill_id,
            "name": self.get_tactical_skill_name(skill_id),
            "icon": self.get_tactical_skill_icon_path(skill_id),
            "raw": self.get_tactical_skill(skill_id),
        }

    def build_trait_render_data(self, trait_id: int) -> dict[str, Any]:
        trait = self.get_trait_skill(trait_id)
        group_key = trait.get("group", "")
        return {
            "id": trait_id,
            "name": trait.get("name", f"特性{trait_id}"),
            "icon": self.get_trait_skill_icon_path(trait_id),
            "group_key": group_key,
            "group_name": self.get_trait_group_name(group_key) if group_key else "",
            "group_icon": self.get_trait_group_icon_path(group_key) if group_key else "",
            "raw": trait,
        }

    def build_mastery_render_data(self, mastery_id: int) -> dict[str, Any]:
        return {
            "id": mastery_id,
            "name": self.get_mastery_name(mastery_id),
            "icon": self.get_mastery_icon_path(mastery_id),
            "raw": self.get_mastery(mastery_id),
        }