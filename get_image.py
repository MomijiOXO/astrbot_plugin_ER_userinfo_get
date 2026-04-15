import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = "https://er.dakgg.io/api/v1/data"
HL = "zh_CN"

ROOT = Path("data")
API_DIR = ROOT / "cache" / "api"
ASSET_DIR = ROOT / "assets"

TIMEOUT = 20
SLEEP_SECONDS = 1

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/plain,*/*",
})


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def normalize_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    return url


def get_ext_from_url(url: str) -> str:
    path = urlparse(url).path
    suffix = Path(path).suffix.lower()
    return suffix if suffix else ".png"


def safe_name(value: str) -> str:
    value = value.strip()
    value = re.sub(r'[\\/:*?"<>|]+', "_", value)
    return value or "unknown"


def fetch_json(endpoint: str) -> dict:
    url = f"{BASE}/{endpoint}?hl={HL}"
    resp = session.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def save_json(data: dict, path: Path) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def download_file(url: str, path: Path) -> bool:
    url = normalize_url(url)
    if not url:
        return False

    ensure_dir(path.parent)

    if path.exists() and path.stat().st_size > 0:
        return True

    try:
        with session.get(url, timeout=TIMEOUT, stream=True) as resp:
            resp.raise_for_status()
            with open(path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        time.sleep(SLEEP_SECONDS)
        return True
    except Exception as e:
        print(f"[FAIL] {url} -> {path} | {e}")
        time.sleep(max(SLEEP_SECONDS, 1.0))
        return False


def write_index(name: str, data: dict) -> None:
    path = API_DIR / f"{name}.json"
    save_json(data, path)


def download_collection(
    collection: list,
    folder: Path,
    id_key: str = "id",
    url_key: str = "imageUrl",
    extra_fields: tuple[str, ...] = ("name", "key"),
    index_name: str | None = None,
) -> dict:
    ensure_dir(folder)
    index = {}

    total = len(collection)
    ok_count = 0

    for i, item in enumerate(collection, 1):
        raw_id = item.get(id_key)
        if raw_id is None:
            continue

        url = item.get(url_key, "")
        url = normalize_url(url)
        if not url:
            continue

        ext = get_ext_from_url(url)
        file_path = folder / f"{raw_id}{ext}"

        ok = download_file(url, file_path)
        if ok:
            ok_count += 1

        index[str(raw_id)] = {
            "id": raw_id,
            "file": str(file_path.as_posix()),
            "url": url,
        }

        for field in extra_fields:
            if field in item:
                index[str(raw_id)][field] = item[field]

        print(f"[{i}/{total}] {'OK' if ok else 'FAIL'} {folder.name}/{raw_id}{ext}")

    if index_name:
        save_json(index, API_DIR / f"{index_name}_index.json")

    print(f"[DONE] {folder.name}: {ok_count}/{total}")
    return index


def main() -> None:
    ensure_dir(API_DIR)
    ensure_dir(ASSET_DIR)

    # 1. 拉取字典 JSON
    print("=== Fetching JSON data ===")
    characters_data = fetch_json("characters")
    items_data = fetch_json("items")
    tiers_data = fetch_json("tiers")
    tactical_skills_data = fetch_json("tactical-skills")
    trait_skills_data = fetch_json("trait-skills")
    masteries_data = fetch_json("masteries")
    skills_data = fetch_json("skills")

    write_index("characters", characters_data)
    write_index("items", items_data)
    write_index("tiers", tiers_data)
    write_index("tactical_skills", tactical_skills_data)
    write_index("trait_skills", trait_skills_data)
    write_index("masteries", masteries_data)
    write_index("skills", skills_data)

    # 2. 下载角色头像
    print("\n=== Downloading character images ===")
    download_collection(
        collection=characters_data.get("characters", []),
        folder=ASSET_DIR / "characters",
        id_key="id",
        url_key="imageUrl",
        index_name="characters",
    )

    # 角色皮肤图也一起下，可选
    print("\n=== Downloading character skins ===")
    skins = []
    for char in characters_data.get("characters", []):
        for skin in char.get("skins", []):
            skin_copy = dict(skin)
            skin_copy["characterId"] = char.get("id")
            skins.append(skin_copy)

    download_collection(
        collection=skins,
        folder=ASSET_DIR / "character_skins",
        id_key="id",
        url_key="imageUrl",
        extra_fields=("name", "imageName", "characterId"),
        index_name="character_skins",
    )

    # 3. 下载物品图标
    print("\n=== Downloading item icons ===")
    download_collection(
        collection=items_data.get("items", []),
        folder=ASSET_DIR / "items",
        id_key="id",
        url_key="imageUrl",
        index_name="items",
    )

    # 4. 下载段位图标
    print("\n=== Downloading tier icons ===")
    tier_items = []
    for t in tiers_data.get("tiers", []):
        icon_item = dict(t)
        icon_item["__url"] = normalize_url(t.get("iconUrl", ""))
        tier_items.append(icon_item)

    download_collection(
        collection=tier_items,
        folder=ASSET_DIR / "tiers",
        id_key="id",
        url_key="__url",
        index_name="tiers",
    )

    # 同时下载 full 图，可选
    print("\n=== Downloading tier full images ===")
    tier_full_items = []
    for t in tiers_data.get("tiers", []):
        full_item = dict(t)
        full_item["__url"] = normalize_url(t.get("imageUrl", ""))
        tier_full_items.append(full_item)

    download_collection(
        collection=tier_full_items,
        folder=ASSET_DIR / "tiers_full",
        id_key="id",
        url_key="__url",
        index_name="tiers_full",
    )

    # 5. 下载战术技能图标
    print("\n=== Downloading tactical skill icons ===")
    download_collection(
        collection=tactical_skills_data.get("tacticalSkills", []),
        folder=ASSET_DIR / "tactical_skills",
        id_key="id",
        url_key="imageUrl",
        index_name="tactical_skills",
    )

    # 6. 下载特性图标
    print("\n=== Downloading trait skill icons ===")
    download_collection(
        collection=trait_skills_data.get("traitSkills", []),
        folder=ASSET_DIR / "trait_skills",
        id_key="id",
        url_key="imageUrl",
        index_name="trait_skills",
    )

    # 7. 下载特性分组图标
    print("\n=== Downloading trait skill group icons ===")
    group_folder = ASSET_DIR / "trait_skill_groups"
    ensure_dir(group_folder)
    group_index = {}

    groups = trait_skills_data.get("traitSkillGroups", [])
    for i, g in enumerate(groups, 1):
        key = safe_name(g.get("key", "unknown"))
        url = normalize_url(g.get("imageUrl", ""))
        ext = get_ext_from_url(url)
        path = group_folder / f"{key}{ext}"

        ok = download_file(url, path)
        group_index[key] = {
            "key": g.get("key"),
            "name": g.get("name"),
            "file": str(path.as_posix()),
            "url": url,
        }
        print(f"[{i}/{len(groups)}] {'OK' if ok else 'FAIL'} trait_skill_groups/{key}{ext}")

    save_json(group_index, API_DIR / "trait_skill_groups_index.json")

    # 8. 下载武器/熟练度图标
    print("\n=== Downloading mastery icons ===")
    mastery_items = []
    for m in masteries_data.get("masteries", []):
        item = dict(m)
        item["__url"] = normalize_url(m.get("iconUrl", ""))
        mastery_items.append(item)

    download_collection(
        collection=mastery_items,
        folder=ASSET_DIR / "masteries",
        id_key="id",
        url_key="__url",
        index_name="masteries",
    )

    # 9. 下载角色技能图标
    print("\n=== Downloading skill icons ===")
    download_collection(
        collection=skills_data.get("skills", []),
        folder=ASSET_DIR / "skills",
        id_key="id",
        url_key="imageUrl",
        extra_fields=("name", "slot", "characterId"),
        index_name="skills",
    )

    print("\nAll done.")


if __name__ == "__main__":
    main()