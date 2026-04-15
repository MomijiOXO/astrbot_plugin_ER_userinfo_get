from __future__ import annotations
import uuid
import time
from pathlib import Path
from typing import Any, List, Optional

from PIL import Image, ImageDraw, ImageFont


class ERRenderer:
    def __init__(self, assets, output_dir: Path):
        self.assets = assets
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.data_dir = self.output_dir.parent
        self.fonts_dir = self.data_dir / "fonts"

        self.W = 1080
        self.PADDING = 20

        self.HEADER_H = 210
        self.SUMMARY_H = 190
        self.HEROES_H = 210
        self.MATCH_H = 136

        # MiSans 字体分层
        self.font_title = self._load_named_font("MiSans-Bold", 40)         # 玩家名
        self.font_big = self._load_named_font("MiSans-Bold", 30)           # 大数字 / 名次 / KDA / MMR

        self.font = self._load_named_font("MiSans-Semibold", 24)           # 模块标题
        self.font_small = self._load_named_font("MiSans-Medium", 20)       # 正文 / summary 主体

        self.font_tiny = self._load_named_font("MiSans-Regular", 18)       # 小字说明
        self.font_mini = self._load_named_font("MiSans-Regular", 12)       # 极小字（折线图坐标 / 战术等级）

        # ===== 白色主题 =====
        self.bg = (255, 255, 255)          # 整体背景
        self.card = (245, 247, 250)        # 主卡片（浅灰）
        self.card_2 = (235, 238, 243)      # 子卡片（更浅）

        self.text = (30, 30, 30)           # 主文字（深色）
        self.sub_text = (120, 120, 120)    # 次级文字

        self.green = (0, 170, 90)          # 上分
        self.red = (220, 60, 60)           # 掉分

        self.gold = (200, 150, 40)         # 第一名
        self.blue = (60, 120, 220)

        self.white = (30, 30, 30)          # 排名默认（改成深色）
        self.gray_line = (210, 210, 210)   # 分割线（可用）

    # =========================
    # 对外入口
    # =========================
    def render(self, data: dict[str, Any]) -> str:
        matches = data.get("matches", [])
        match_count = len(matches)

        heroes = data.get("common_heroes", [])
        hero_count = len(heroes)
        heroes_block_h = 48 + hero_count * 92 + 20 if hero_count > 0 else 120

        total_h = (
            self.PADDING
            + self.HEADER_H
            + self.PADDING
            + self.SUMMARY_H
            + self.PADDING
            + heroes_block_h
            + self.PADDING
            + match_count * self.MATCH_H
            + self.PADDING
        )

        img = Image.new("RGBA", (self.W, total_h), self.bg + (255,))
        draw = ImageDraw.Draw(img)

        y = self.PADDING
        y = self._draw_header(img, draw, data.get("player", {}), y)
        y += self.PADDING

        y = self._draw_summary(draw, data.get("summary", {}), y)
        y += self.PADDING

        y = self._draw_common_heroes(img, draw, data.get("common_heroes", []), y)
        y += self.PADDING

        y = self._draw_matches(img, draw, data.get("matches", []), y)

        output_path = self.output_dir / f"er_profile_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}.png"
        img.convert("RGB").save(output_path, "PNG")
        return str(output_path)

    # =========================
    # 字体
    # =========================
    def _load_named_font(self, font_stem: str, size: int):
        candidates = [
            f"{font_stem}.ttf",
            f"{font_stem}.otf",
            f"{font_stem}.ttc",
        ]
        for name in candidates:
            path = self.fonts_dir / name
            if path.exists():
                try:
                    return ImageFont.truetype(str(path), size)
                except Exception:
                    pass
        return self._load_font(size)

    def _load_font(self, size: int):
        candidates = [
            "msyh.ttc",
            "msyh.ttf",
            "Microsoft YaHei.ttf",
            "simhei.ttf",
            "simsun.ttc",
            "SourceHanSansCN-Regular.otf",
            "SourceHanSansSC-Regular.otf",
            "NotoSansCJKsc-Regular.otf",
        ]
        for name in candidates:
            font_path = self.fonts_dir / name
            if font_path.exists():
                try:
                    return ImageFont.truetype(str(font_path), size)
                except Exception:
                    pass
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            return ImageFont.load_default()

    # =========================
    # 顶部
    # =========================
    def _draw_header(self, img: Image.Image, draw: ImageDraw.ImageDraw, player: dict, y: int) -> int:
        x1 = self.PADDING
        x2 = self.W - self.PADDING
        header_h = 190
        y2 = y + header_h

        self._draw_card(draw, x1, y, x2, y2)

        # ===== 左侧基础信息 =====
        name_x = x1 + 18
        name_y = y + 18

        draw.text(
            (name_x, name_y),
            player.get("name", ""),
            font=self.font_title,
            fill=self.text,
        )

        draw.text(
            (name_x + 4, name_y + 58),
            f"Lv.{int(player.get('level', 0) or 0)}",
            font=self.font_small,
            fill=self.sub_text,
        )

        draw.text(
            (name_x, name_y + 100),
            f"MMR: {int(player.get('mmr', 0) or 0)}",
            font=self.font_big,
            fill=self.text,
        )

        # ===== 中间折线图 =====
        chart_x = x1 + 215
        chart_y = y + 12
        chart_w = 550
        chart_h = 145

        mmr_chart = player.get("mmr_chart", [])
        if mmr_chart:
            try:
                self._draw_mmr_chart(
                    img=img,
                    draw=draw,
                    data=mmr_chart,
                    x=chart_x,
                    y=chart_y,
                    w=chart_w,
                    h=chart_h,
                )
            except TypeError:
                try:
                    self._draw_mmr_chart(
                        img=img,
                        draw=draw,
                        player=player,
                        x=chart_x,
                        y=chart_y,
                        w=chart_w,
                        h=chart_h,
                    )
                except Exception:
                    pass
            except Exception:
                pass

        # ===== 右侧段位图标 =====
        tier_icon_path = player.get("tier_full") or player.get("tier_icon", "")
        tier_icon_size = 96
        tier_icon_x = x2 - 190
        tier_icon_y = y + 12

        tier_icon = self._load_icon(tier_icon_path, (tier_icon_size, tier_icon_size))
        if tier_icon:
            self._paste_icon(img, tier_icon, (tier_icon_x, tier_icon_y))

        icon_center_x = tier_icon_x + tier_icon_size / 2

        # ===== 段位名称 =====
        tier_name = player.get("tier_name", "")
        if tier_name:
            tier_font = self.font_big
            bbox = draw.textbbox((0, 0), tier_name, font=tier_font)
            text_w = bbox[2] - bbox[0]

            tier_text_x = int(icon_center_x - text_w / 2)
            tier_text_y = tier_icon_y + tier_icon_size - 10

            draw.text(
                (tier_text_x, tier_text_y),
                tier_name,
                font=tier_font,
                fill=self.text,
            )

        # ===== 排名 =====
        global_rank = int(player.get("rank_global", 0) or 0)
        global_percent = float(player.get("rank_global_percent", 0.0) or 0.0)
        local_rank = int(player.get("rank_local", 0) or 0)
        local_percent = float(player.get("rank_local_percent", 0.0) or 0.0)

        rank_font = self.font_tiny

        global_text = f"Global {global_rank:,}名 (上位 {global_percent:.2f}%)" if global_rank > 0 else ""
        local_text = f"Asia {local_rank:,}名 (上位 {local_percent:.2f}%)" if local_rank > 0 else ""

        rank_y1 = y + 138
        rank_gap = 24

        if global_text:
            g_bbox = draw.textbbox((0, 0), global_text, font=rank_font)
            g_w = g_bbox[2] - g_bbox[0]
            g_x = int(icon_center_x - g_w / 2)

            draw.text(
                (g_x, rank_y1),
                global_text,
                font=rank_font,
                fill=self.sub_text,
            )

        if local_text:
            l_bbox = draw.textbbox((0, 0), local_text, font=rank_font)
            l_w = l_bbox[2] - l_bbox[0]
            l_x = int(icon_center_x - l_w / 2)

            draw.text(
                (l_x, rank_y1 + rank_gap),
                local_text,
                font=rank_font,
                fill=self.sub_text,
            )

        return y2 + 12

    def _draw_mmr_chart(self, img: Image.Image, draw: ImageDraw.ImageDraw, data: list[dict], x: int, y: int, w: int, h: int) -> None:
        if not data or len(data) < 2:
            return

        values = []
        labels = []
        for item in data:
            try:
                values.append(float(item.get("value", 0)))
                labels.append(str(item.get("label", "")))
            except Exception:
                continue

        if len(values) < 2:
            return

        pad_left = 52
        pad_right = 10
        pad_top = 8
        pad_bottom = 2

        chart_x1 = x + pad_left
        chart_y1 = y + pad_top
        chart_x2 = x + w - pad_right
        chart_y2 = y + h - pad_bottom

        chart_w = chart_x2 - chart_x1
        chart_h = chart_y2 - chart_y1

        if chart_w <= 0 or chart_h <= 0:
            return

        v_min = min(values)
        v_max = max(values)

        if v_min == v_max:
            v_min -= 1
            v_max += 1

        span = v_max - v_min
        v_min -= span * 0.08
        v_max += span * 0.08
        span = v_max - v_min

        grid_count = 5
        label_font = self.font_mini

        for i in range(grid_count):
            ratio = i / (grid_count - 1)
            yy = chart_y1 + chart_h * ratio
            value = v_max - span * ratio

            draw.line(
                [(chart_x1, yy), (chart_x2, yy)],
                fill=(200, 200, 200),
                width=1,
            )

            text = f"{int(round(value)):,}"
            bbox = draw.textbbox((0, 0), text, font=label_font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]

            draw.text(
                (chart_x1 - tw - 8, yy - th / 2),
                text,
                font=label_font,
                fill=(130, 130, 130),
            )

        points = []
        n = len(values)
        for i, v in enumerate(values):
            if n == 1:
                px = chart_x1 + chart_w / 2
            else:
                px = chart_x1 + chart_w * i / (n - 1)

            py = chart_y2 - ((v - v_min) / span) * chart_h
            points.append((px, py))

        draw.line(points, fill=(193, 132, 83), width=4)

        r = 5
        for px, py in points:
            draw.ellipse((px - r, py - r, px + r, py + r), fill=(193, 132, 83))

        for (px, _py), label in zip(points, labels):
            bbox = draw.textbbox((0, 0), label, font=label_font)
            tw = bbox[2] - bbox[0]

            draw.text(
                (px - tw / 2, chart_y2 + 6),
                label,
                font=label_font,
                fill=(130, 130, 130),
            )

    # =========================
    # 总览
    # =========================
    def _draw_summary(self, draw: ImageDraw.ImageDraw, summary: dict, y: int) -> int:
        x1 = self.PADDING
        x2 = self.W - self.PADDING
        y2 = y + self.SUMMARY_H
        self._draw_card(draw, x1, y, x2, y2)

        # 标题
        draw.text(
            (x1 + 18, y + 8),
            "RANK统计",
            font=self.font_small,
            fill=self.text,
        )

        stats = [
            ("平均TK", f"{summary.get('avg_tk', 0)}"),
            ("胜率", f"{summary.get('win_rate', 0)}%"),
            ("游戏场次", f"{summary.get('play', 0)}"),

            ("平均击杀", f"{summary.get('avg_kill', 0)}"),
            ("TOP 2", f"{summary.get('top2_rate', 0)}%"),
            ("平均伤害", f"{summary.get('avg_damage', 0)}"),

            ("平均助攻", f"{summary.get('avg_assist', 0)}"),
            ("TOP 3", f"{summary.get('top3_rate', 0)}%"),
            ("平均排名", f"#{summary.get('avg_rank', 0)}"),

            ("平均狩猎野生动物", f"{summary.get('avg_monster_kill', 0)}"),
            ("获得平均学分", f"{int(summary.get('avg_vf_credit', 0) or 0):,}"),
            ("平均视野贡献", f"{summary.get('avg_view_contribution', 0)}"),
        ]

        start_x = x1 + 18
        start_y = y + 36
        col_w = 330
        row_h = 36

        dot_color = (40, 140, 255)

        for i, (label, value) in enumerate(stats):
            col = i % 3
            row = i // 3

            text_x = start_x + col * col_w
            text_y = start_y + row * row_h

            dot_x = text_x
            dot_y = text_y + 6
            draw.ellipse(
                (dot_x, dot_y, dot_x + 8, dot_y + 8),
                fill=dot_color,
            )

            draw.text(
                (text_x + 14, text_y),
                f"{label}：{value}",
                font=self.font_small,
                fill=self.text,
            )

        return y2

    # =========================
    # 常用英雄
    # =========================
    def _draw_common_heroes(self, img: Image.Image, draw: ImageDraw.ImageDraw, heroes: List[dict], y: int) -> int:
        hero_count = len(heroes[:5])
        row_h = 82
        block_h = 48 + hero_count * row_h + 16 if hero_count > 0 else 120

        x1 = self.PADDING
        x2 = self.W - self.PADDING
        y2 = y + block_h
        self._draw_card(draw, x1, y, x2, y2)

        draw.text((x1 + 20, y + 12), "常用英雄", font=self.font, fill=self.text)

        start_y = y + 48

        for i, hero in enumerate(heroes[:5]):
            row_y1 = start_y + i * row_h
            row_y2 = row_y1 + row_h - 8

            self._draw_inner_card(draw, x1 + 14, row_y1, x2 - 14, row_y2)

            avatar_x = x1 + 24
            avatar_y = row_y1 + 12

            name_x = x1 + 92
            play_x = x1 + 250
            rp_x = x1 + 390
            rank_x = x1 + 500
            ka_x = x1 + 620
            dmg_x = x1 + 800

            top_y = row_y1 + 12
            sub_y = row_y1 + 40

            icon = self._load_icon_crop_center(hero.get("character_icon", ""), (54, 54))
            if icon:
                self._paste_icon(img, icon, (avatar_x, avatar_y))

            draw.text(
                (name_x, top_y),
                hero.get("character_name", ""),
                font=self.font_small,
                fill=self.text,
            )
            draw.text(
                (name_x, sub_y),
                "英雄",
                font=self.font_tiny,
                fill=self.sub_text,
            )

            rp_value = int(hero.get("rp", 0) or 0)
            triangle_x = rp_x
            triangle_y = top_y + 6
            triangle_color = self._draw_delta_triangle(draw, triangle_x, triangle_y, rp_value, size=8)

            rp_text = f"{abs(rp_value)}" if rp_value != 0 else "0"
            draw.text(
                (rp_x + 14, top_y),
                rp_text,
                font=self.font_small,
                fill=self.text,
            )
            draw.text(
                (rp_x, sub_y),
                "RP",
                font=self.font_tiny,
                fill=self.sub_text,
            )

            draw.text(
                (play_x, top_y),
                f"{hero.get('play', 0)}场 | {hero.get('win_rate', 0)}%",
                font=self.font_small,
                fill=self.text,
            )
            draw.text(
                (play_x, sub_y),
                "场次 / 胜率",
                font=self.font_tiny,
                fill=self.sub_text,
            )

            draw.text(
                (rank_x, top_y),
                f"{hero.get('avg_rank', 0)}",
                font=self.font_small,
                fill=self.text,
            )
            draw.text(
                (rank_x, sub_y),
                "场均排名",
                font=self.font_tiny,
                fill=self.sub_text,
            )

            draw.text(
                (ka_x, top_y),
                f"K {hero.get('avg_kill', 0)} / A {hero.get('avg_assist', 0)}",
                font=self.font_small,
                fill=self.text,
            )
            draw.text(
                (ka_x, sub_y),
                "平均击杀 / 助攻",
                font=self.font_tiny,
                fill=self.sub_text,
            )

            draw.text(
                (dmg_x, top_y),
                f"{hero.get('avg_damage', 0)}",
                font=self.font_small,
                fill=self.text,
            )
            draw.text(
                (dmg_x, sub_y),
                "平均伤害",
                font=self.font_tiny,
                fill=self.sub_text,
            )

        return y2

    # =========================
    # 战绩列表
    # =========================
    def _draw_matches(self, img: Image.Image, draw: ImageDraw.ImageDraw, matches: List[dict], y: int) -> int:
        for match in matches:
            y = self._draw_single_match(img, draw, match, y)
        return y

    def _draw_single_match(self, img: Image.Image, draw: ImageDraw.ImageDraw, match: dict, y: int) -> int:
        x1 = self.PADDING
        x2 = self.W - self.PADDING
        y2 = y + self.MATCH_H - 8

        self._draw_card(draw, x1, y, x2, y2)

        rank = int(match.get("rank", 0) or 0)
        kills = int(match.get("kills", 0) or 0)
        deaths = int(match.get("deaths", 0) or 0)
        assists = int(match.get("assists", 0) or 0)
        team_kill = int(match.get("team_kill", 0) or 0)
        damage = int(match.get("damage", 0) or 0)
        mmr_after = match.get("mmr_after")
        mmr_change = int(match.get("mmr_change", 0) or 0)

        is_rank_match = bool(match.get("is_rank_match", False))
        mode_label = str(match.get("mode_label", "") or "")

        tkka_text = f"{team_kill}/{kills}/{assists}"

        if deaths == 0:
            kda_value = round(kills + assists, 2)
        else:
            kda_value = round((kills + assists) / max(deaths, 1), 2)

        avatar_x = x1 + 14
        avatar_y = y + 32

        time_x = x1 + 12
        time_y = y + 6

        rank_x = x1 + 92
        rank_y = y + 34

        change_x = x1 + 150
        change_y = y + 38

        stat_x = x1 + 92
        stat_y = y + 66

        label_x = x1 + 92
        label_y = y + 100

        icon_x = x1 + 250
        icon_y = y + 28
        trait_row_y = y + 82

        damage_x = x1 + 360
        kda_x = x1 + 505
        rp_x = x1 + 625

        value_y = y + 42
        sub_y = y + 82

        item_x = x2 - 250
        item_y = y + 22

        # ===== 左侧头像 =====
        avatar_size = 64
        hero_icon = self._load_icon(match.get("character_icon", ""), (avatar_size, avatar_size))
        if hero_icon:
            self._paste_icon(img, hero_icon, (avatar_x, avatar_y))

        # ===== 头像下方：实验体名字 =====
        character_name = str(match.get("character_name", "") or "")
        if character_name:
            name_font = self.font_tiny
            bbox = draw.textbbox((0, 0), character_name, font=name_font)
            text_w = bbox[2] - bbox[0]

            name_x = int(avatar_x + avatar_size / 2 - text_w / 2)
            name_y = avatar_y + avatar_size + 4

            draw.text(
                (name_x, name_y),
                character_name,
                font=name_font,
                fill=self.sub_text,
            )

        # ===== 时间 =====
        draw.text(
            (time_x, time_y),
            match.get("start_time", ""),
            font=self.font_tiny,
            fill=self.sub_text,
        )

        # ===== 排名 =====
        rank_color = self.text
        if rank == 1:
            rank_color = self.gold
        elif rank in (2, 3):
            rank_color = (255, 180, 90)

        draw.text((rank_x, rank_y), f"#{rank}", font=self.font_big, fill=rank_color)

        # ===== 排位 / 一般 =====
        if is_rank_match:
            if mmr_change > 0:
                change_color = self.red
            elif mmr_change < 0:
                change_color = self.green
            else:
                change_color = self.text

            draw.text(
                (change_x, change_y),
                f"{mmr_change:+}",
                font=self.font_small,
                fill=change_color,
            )
        else:
            draw.text(
                (change_x, change_y),
                mode_label or "一般",
                font=self.font_small,
                fill=self.text,
            )

        # ===== TK / K / A =====
        draw.text((stat_x, stat_y), tkka_text, font=self.font_big, fill=self.text)
        draw.text((label_x, label_y), "TK / K / A", font=self.font_tiny, fill=self.sub_text)

        # ===== 第一行：武器 + 战术技能 =====
        draw.rounded_rectangle(
            (icon_x, icon_y, icon_x + 36, icon_y + 36),
            radius=8,
            fill=(30, 30, 30),
        )
        weapon_icon = self._load_icon(match.get("weapon_icon", ""), (28, 28))
        if weapon_icon:
            self._paste_icon(img, weapon_icon, (icon_x + 4, icon_y + 4))

        tactical = match.get("tactical_skill", {})
        tactical_icon = self._load_icon(tactical.get("icon", ""), (34, 34))
        if tactical_icon:
            tactical_pos = (icon_x + 48, icon_y + 1)
            self._paste_icon(img, tactical_icon, tactical_pos)

            tactical_level = int(match.get("tactical_skill_level", 0) or 0)
            if tactical_level > 0:
                badge_x = tactical_pos[0] - 2
                badge_y = tactical_pos[1] + 20

                draw.rounded_rectangle(
                    (badge_x, badge_y, badge_x + 16, badge_y + 16),
                    radius=4,
                    fill=(245, 245, 245),
                    outline=(60, 60, 60),
                    width=1,
                )
                draw.text(
                    (badge_x + 4, badge_y - 1),
                    str(tactical_level),
                    font=self.font_mini if hasattr(self, "font_mini") else self._load_font(12),
                    fill=(20, 20, 20),
                )

        # ===== 第二行：主天赋图标 + 副组类型图标 =====
        core_icon = self._load_icon(match.get("trait_core_icon", ""), (30, 30))
        if core_icon:
            self._paste_icon(img, core_icon, (icon_x + 3, trait_row_y))

        second_group_icon = self._load_icon(match.get("trait_second_group_icon", ""), (30, 30))
        if second_group_icon:
            self._paste_icon(img, second_group_icon, (icon_x + 51, trait_row_y))

        # ===== 伤害 =====
        draw.text((damage_x, value_y), f"{damage}", font=self.font_big, fill=self.text)
        draw.text((damage_x, sub_y), "伤害", font=self.font_tiny, fill=self.sub_text)

        # ===== KDA =====
        draw.text((kda_x, value_y), f"{kda_value:.2f}", font=self.font_big, fill=self.text)
        draw.text((kda_x, sub_y), "KDA", font=self.font_tiny, fill=self.sub_text)

        # ===== 起始地点 / 路径ID =====
        path_id = int(match.get("path_id", 0) or 0)
        start_area = str(match.get("start_area", "") or "").strip()

        if start_area:
            top_text = start_area
            bottom_text = "起始地点"
            top_font = self.font_small
            bottom_font = self.font_tiny
        elif path_id > 0:
            top_text = str(path_id)
            bottom_text = "路径ID"
            top_font = self.font_big
            bottom_font = self.font_tiny
        else:
            top_text = "未知"
            bottom_text = "起始地点"
            top_font = self.font_small
            bottom_font = self.font_tiny

        top_bbox = draw.textbbox((0, 0), top_text, font=top_font)
        bottom_bbox = draw.textbbox((0, 0), bottom_text, font=bottom_font)

        top_w = top_bbox[2] - top_bbox[0]
        bottom_w = bottom_bbox[2] - bottom_bbox[0]

        center_x = rp_x + 40

        top_x = int(center_x - top_w / 2)
        bottom_x = int(center_x - bottom_w / 2)

        draw.text((top_x, value_y), top_text, font=top_font, fill=self.text)
        draw.text((bottom_x, sub_y), bottom_text, font=bottom_font, fill=self.sub_text)

        # ===== 装备：3上2下，下排居中 =====
        items = match.get("items", [])[:5]

        top_gap_x = 56
        bottom_gap_x = 56
        top_y = item_y
        bottom_y = item_y + 45  # 调小会更像五环，调大则更松

        # 第一排三格中心
        top_row_width = top_gap_x * 2
        top_center_x = item_x + top_row_width / 2

        # 第二排两格整体宽度
        bottom_row_width = bottom_gap_x
        bottom_start_x = int(top_center_x - bottom_row_width / 2)

        positions = [
            (item_x + 0 * top_gap_x, top_y),
            (item_x + 1 * top_gap_x, top_y),
            (item_x + 2 * top_gap_x, top_y),
            (bottom_start_x, bottom_y),
            (bottom_start_x + bottom_gap_x, bottom_y),
        ]

        for i, item in enumerate(items):
            if i >= len(positions):
                break

            ix, iy = positions[i]

            item_grade = item.get("grade", "")
            bg_color = self._get_item_bg_color(item_grade)

            draw.rounded_rectangle(
                (ix, iy, ix + 44, iy + 34),
                radius=6,
                fill=bg_color,
            )

            item_icon = self._load_icon(item.get("icon", ""), (34, 34))
            if item_icon:
                self._paste_icon(img, item_icon, (ix + 5, iy))

        return y + self.MATCH_H

    # =========================
    # 工具
    # =========================
    def _load_icon_crop_center(self, path: str, size: tuple[int, int]) -> Optional[Image.Image]:
        if not path:
            return None

        p = Path(path)
        if not p.exists():
            return None

        try:
            img = Image.open(p).convert("RGBA")

            target_w, target_h = size
            src_w, src_h = img.size

            scale = max(target_w / src_w, target_h / src_h)
            new_w = int(src_w * scale)
            new_h = int(src_h * scale)

            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            left = (new_w - target_w) // 2
            top = (new_h - target_h) // 2
            right = left + target_w
            bottom = top + target_h

            img = img.crop((left, top, right, bottom))
            return img
        except Exception:
            return None

    def _get_item_bg_color(self, grade: str) -> tuple[int, int, int]:
        grade = (grade or "").strip()

        grade_map = {
            "Common": (150, 150, 150),
            "Uncommon": (70, 120, 220),
            "Rare": (70, 120, 220),
            "Epic": (160, 90, 210),
            "Hero": (160, 90, 210),
            "Legend": (183, 145, 67),
            "Mythic": (180, 60, 60),
        }

        return grade_map.get(grade, (150, 150, 150))

    def _load_icon(self, path: str, size: tuple[int, int]) -> Optional[Image.Image]:
        if not path:
            return None
        p = Path(path)
        if not p.exists():
            return None
        try:
            icon = Image.open(p).convert("RGBA")
            icon = icon.resize(size, Image.Resampling.LANCZOS)
            return icon
        except Exception:
            return None

    def _paste_icon(self, base_img: Image.Image, icon: Optional[Image.Image], pos: tuple[int, int]) -> None:
        if icon is None:
            return
        base_img.paste(icon, pos, icon)

    def _draw_card(self, draw, x1, y1, x2, y2):
        draw.rounded_rectangle(
            (x1, y1, x2, y2),
            radius=18,
            fill=self.card,
            outline=(220, 220, 220),
            width=1,
        )

    def _draw_inner_card(self, draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
        draw.rounded_rectangle((x1, y1, x2, y2), radius=12, fill=self.card_2)
    
    def _draw_delta_triangle(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        delta: int,
        size: int = 8,
    ) -> tuple[int, int, int]:
        if delta > 0:
            color = (220, 90, 90)   # 红
            points = [
                (x, y + size),
                (x + size, y + size),
                (x + size / 2, y),
            ]
        elif delta < 0:
            color = (90, 150, 220)  # 蓝绿/青蓝，接近 dak 的下箭头感觉
            points = [
                (x, y),
                (x + size, y),
                (x + size / 2, y + size),
            ]
        else:
            color = self.sub_text
            points = [
                (x, y + size),
                (x + size, y + size),
                (x + size / 2, y),
            ]

        draw.polygon(points, fill=color)
        return color