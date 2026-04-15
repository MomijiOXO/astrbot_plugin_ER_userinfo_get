from pathlib import Path
from typing import Optional
import time
import json
import requests
import threading
from datetime import datetime, timedelta

from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

from .api_client import ERApiClient, PlayerNotFoundError
from .asset_manager import AssetManager
from .mapper import DataMapper
from .renderer import ERRenderer


@register(
    "astrbot_plugin_er_profile",
    "你",
    "Eternal Return 战绩查询插件（出图版）",
    "1.0.0",
)
class ERProfilePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

        # ===== 路径（AstrBot 环境防御性修复） =====
        current_path = Path(__file__).resolve()
        if current_path.is_file():
            self.plugin_dir = current_path.parent
        else:
            self.plugin_dir = current_path

        async def initialize(self):
            self._delete_output_files_older_than(days=1)
            self._start_output_cleanup_task()

        self.data_dir = self.plugin_dir / "data"
        self.output_dir = self.data_dir / "output"
        self.sync_cache_file = self.data_dir / "cache" / "player_sync_cache.json"

        self.sync_cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # ===== 核心模块 =====
        self.assets = AssetManager(self.data_dir)
        self.api = ERApiClient()
        self.mapper = DataMapper(self.assets)
        self.renderer = ERRenderer(self.assets, self.output_dir)
        self.default_season = self._get_latest_season_key()

        # ===== 默认配置 =====
        self.default_match_count = 20
        self.max_match_count = 20
        self.default_season = self._get_latest_season_key()

        self._cleanup_task_started = False

    def _get_latest_season_key(self) -> str:
        try:
            season_key = self.api.get_current_season_key(hl="zh_CN")
            if season_key:
                return season_key
        except Exception:
            pass
        return "SEASON_19"

    def _clear_output_dir(self) -> None:
        if not self.output_dir.exists():
            return

        for path in self.output_dir.iterdir():
            try:
                if path.is_file():
                    path.unlink()
            except Exception:
                pass

    def _start_output_cleanup_task(self) -> None:
        if self._cleanup_task_started:
            return

        self._cleanup_task_started = True

        def worker():
            while True:
                now = datetime.now()
                next_run = now.replace(hour=4, minute=0, second=0, microsecond=0)

                if now >= next_run:
                    next_run = next_run + timedelta(days=1)

                sleep_seconds = (next_run - now).total_seconds()
                time.sleep(max(sleep_seconds, 1))

                try:
                    self._clear_output_dir()
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    def _delete_output_files_older_than(self, days: int = 1) -> None:
        if not self.output_dir.exists():
            return

        cutoff = time.time() - days * 24 * 60 * 60

        for path in self.output_dir.iterdir():
            try:
                if not path.is_file():
                    continue

                mtime = path.stat().st_mtime
                if mtime < cutoff:
                    path.unlink()
            except Exception:
                pass

    def _load_sync_cache(self) -> dict:
        if not self.sync_cache_file.exists():
            return {}
        try:
            return json.loads(self.sync_cache_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_sync_cache(self, data: dict) -> None:
        self.sync_cache_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _should_skip_sync(self, player_name: str, ttl_seconds: int = 300) -> bool:
        cache = self._load_sync_cache()
        key = player_name.strip().lower()
        last_ts = float(cache.get(key, 0) or 0)
        return (time.time() - last_ts) < ttl_seconds

    def _fetch_profile_and_matches_with_retry(
        self,
        player_name: str,
        match_count: int,
        max_retries: int = 2,
    ):
        last_error = None
        cache_key = player_name.strip().lower()
        retryable_errors = (
            requests.Timeout,
            requests.ConnectTimeout,
            requests.ReadTimeout,
            requests.ConnectionError,
        )

        for attempt in range(max_retries + 1):
            try:
                if self._should_skip_sync(cache_key):
                    profile_data = self.api.get_profile(
                        player_name,
                        season=self.default_season,
                    )
                else:
                    profile_data = self.api.sync_and_wait_for_profile(
                        player_name,
                        season=self.default_season,
                        max_attempts=6,
                        interval_seconds=2.0,
                    )

                    cache = self._load_sync_cache()
                    cache[cache_key] = time.time()
                    self._save_sync_cache(cache)

                matches_data = self.api.get_matches(
                    player_name,
                    season=self.default_season,
                    matching_mode="ALL",
                    team_mode="ALL",
                    page=1,
                )

                return profile_data, matches_data

            except PlayerNotFoundError:
                raise
            except retryable_errors as e:
                last_error = e
                if attempt >= max_retries:
                    raise
                time.sleep(1.0)
            except Exception:
                raise

        raise last_error if last_error else Exception("unknown error")
    # =========================
    # 主命令
    # =========================
    @filter.command("战绩")
    async def er_profile(
        self,
        event: AstrMessageEvent,
        player_name: str = "",
        match_count: Optional[int] = None,
    ):
        """
        用法:
        /战绩 xxx
        """

        player_name = player_name.strip()

        if not player_name:
            yield event.plain_result("请输入玩家名，例如：/战绩 XXX")
            return

        if match_count is None:
            match_count = self.default_match_count

        try:
            match_count = int(match_count)
        except Exception:
            match_count = self.default_match_count

        if match_count < 20:
            match_count = 20
        elif match_count > self.max_match_count:
            match_count = self.max_match_count

        self.default_season = self._get_latest_season_key()

        try:
            profile_data, matches_data = self._fetch_profile_and_matches_with_retry(
                player_name=player_name,
                match_count=match_count,
                max_retries=2,
            )

            render_data = self.mapper.build_render_data(
                profile_data=profile_data,
                matches_data=matches_data,
                match_count=match_count,
            )

            image_path = self.renderer.render(render_data)
            yield event.image_result(image_path)

        except PlayerNotFoundError:
            yield event.plain_result("查询用户不存在")
        except (requests.Timeout, requests.ConnectTimeout, requests.ReadTimeout, requests.ConnectionError):
            yield event.plain_result("查询失败，网络请求异常")
        except Exception:
            yield event.plain_result("查询失败")

    # =========================
    # 查看配置
    # =========================
    @filter.command("战绩配置")
    async def er_profile_config(self, event: AstrMessageEvent):
        yield event.plain_result(
            f"默认场次: {self.default_match_count}\n"
            f"最大场次: {self.max_match_count}\n"
            f"赛季: {self.default_season}"
        )

    # =========================
    # 刷新资源
    # =========================
    @filter.command("战绩刷新资源")
    async def er_refresh_assets(self, event: AstrMessageEvent):
        try:
            self.assets.reload()
            yield event.plain_result("资源索引已刷新。")
        except Exception as e:
            yield event.plain_result(f"刷新失败：{e}")