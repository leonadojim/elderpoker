"""
四副牌升级专用渲染模块（4人布局，52张手牌叠放显示）。
"""
import pygame
import os
import sys
sys.path.insert(0, '..')
from common.constants import *
from common.renderer_base import get_font, get_card_image, draw_card, draw_card_back, draw_button, draw_table, wrap_text
from common.cards import SUITS, JOKERS
from shengji.engine import PHASE_ENDED

# 升级专用小牌尺寸（手牌区与底牌区统一使用）
SJ_CARD_W = 80
SJ_CARD_H = 115

# 庄家图标缓存
_dizhu_img = None

def _get_dizhu_icon(size=(28, 28)):
    global _dizhu_img
    if _dizhu_img is None:
        path = os.path.join("assets", "logos", "dizhu.png")
        if os.path.exists(path):
            raw = pygame.image.load(path).convert_alpha()
            _dizhu_img = pygame.transform.smoothscale(raw, size)
        else:
            _dizhu_img = False
    return _dizhu_img if _dizhu_img else None


def draw_player_bottom(surface, cards, selected_indices, power_eval):
    """
    绘制底部玩家手牌（叠放显示）。
    返回每张牌的点击区域 [(x, y, w, h, original_index), ...]
    """
    trump_cards = []
    suit_cards = {s: [] for s in ['spade', 'heart', 'diamond', 'club']}

    for i, c in enumerate(cards):
        if power_eval.is_trump(c):
            trump_cards.append((i, c))
        else:
            suit_cards[c[1]].append((i, c))

    rows = []
    if trump_cards:
        rows.append(("主牌", trump_cards))
    for s in ['spade', 'heart', 'diamond', 'club']:
        if suit_cards[s]:
            suit_name = {'spade': '黑桃', 'heart': '红桃', 'diamond': '方块', 'club': '梅花'}
            rows.append((suit_name[s], suit_cards[s]))

    # 最多4行：主牌+各花色各一行，仍超出则后面的行合并为"其他"
    if len(rows) > 4:
        new_rows = rows[:3]
        merged = []
        for _, items in rows[3:]:
            merged.extend(items)
        if merged:
            new_rows.append(("其他", merged))
        rows = new_rows

    if not rows:
        return []

    CARD_W = SJ_CARD_W
    CARD_H = SJ_CARD_H
    ROW_GAP = 58
    SELECT_LIFT = -22

    LEFT_MARGIN = 90   # 左侧给行标签留位
    RIGHT_MARGIN = 90
    usable_w = SCREEN_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

    # 按最宽行动态计算每张牌的可见宽度
    max_n = max(len(items) for _, items in rows)
    if max_n > 1:
        overlap_x = min(48, (usable_w - CARD_W) // (max_n - 1))
    else:
        overlap_x = 0

    max_row_width = (max_n - 1) * overlap_x + CARD_W
    start_x = LEFT_MARGIN + (usable_w - max_row_width) // 2
    bottom_margin = 5
    start_y = SCREEN_HEIGHT - bottom_margin - CARD_H

    click_areas = []
    label_font = get_font(FONT_SIZE_SMALL)

    for row_idx in range(len(rows) - 1, -1, -1):
        label, items = rows[row_idx]
        n = len(items)
        y = start_y - row_idx * ROW_GAP
        # 被下一行压住的行只有 ROW_GAP 高度可见，最底行整牌可见
        visible_h = CARD_H if row_idx == 0 else ROW_GAP

        label_surf = label_font.render(label, True, COLOR_TEXT_YELLOW)
        label_x = max(8, start_x - label_surf.get_width() - 12)
        label_y = y + (visible_h - label_surf.get_height()) // 2
        surface.blit(label_surf, (label_x, label_y))

        for i, (orig_idx, card) in enumerate(items):
            x = start_x + i * overlap_x
            sel = orig_idx in selected_indices
            draw_y = y + (SELECT_LIFT if sel else 0)
            draw_card(surface, card, x, draw_y, selected=False, size=(CARD_W, CARD_H))

            if i < n - 1:
                click_w = overlap_x
            else:
                click_w = CARD_W
            click_areas.append((x, draw_y, click_w, visible_h, orig_idx))

    return click_areas


def draw_player_left(surface, n, name, is_dealer=False):
    """左侧AI"""
    start_y = 345
    small_w, small_h = 44, 64
    overlap = 5
    display_n = min(n, 10)

    name_font = get_font(FONT_SIZE_SMALL)
    name_surf = name_font.render(name, True, COLOR_TEXT_YELLOW)
    name_y = 300
    surface.blit(name_surf, (10, name_y))

    # 庄家图标
    if is_dealer:
        icon = _get_dizhu_icon((28, 28))
        if icon:
            surface.blit(icon, (10 + name_surf.get_width() + 6, name_y))

    for i in range(display_n):
        x = 10
        y = start_y + i * overlap
        draw_card_back(surface, x, y, size=(small_w, small_h))

    count_font = get_font(FONT_SIZE_SMALL)
    count_surf = count_font.render(f"剩{n}张", True, COLOR_TEXT_YELLOW)
    count_y = start_y + display_n * overlap + small_h + 6
    surface.blit(count_surf, (10, count_y))


def draw_player_right(surface, n, name, is_dealer=False):
    """右侧AI"""
    start_y = 345
    small_w, small_h = 44, 64
    overlap = 5
    display_n = min(n, 10)

    name_font = get_font(FONT_SIZE_SMALL)
    name_surf = name_font.render(name, True, COLOR_TEXT_YELLOW)
    name_x = SCREEN_WIDTH - 10 - name_surf.get_width()
    name_y = 300
    surface.blit(name_surf, (name_x, name_y))

    if is_dealer:
        icon = _get_dizhu_icon((28, 28))
        if icon:
            surface.blit(icon, (name_x - 34, name_y))

    for i in range(display_n):
        x = SCREEN_WIDTH - small_w - 10
        y = start_y + i * overlap
        draw_card_back(surface, x, y, size=(small_w, small_h))

    count_font = get_font(FONT_SIZE_SMALL)
    count_surf = count_font.render(f"剩{n}张", True, COLOR_TEXT_YELLOW)
    count_x = SCREEN_WIDTH - 10 - count_surf.get_width()
    count_y = start_y + display_n * overlap + small_h + 6
    surface.blit(count_surf, (count_x, count_y))


def draw_player_top(surface, n, name, is_dealer=False):
    """上方AI"""
    small_w, small_h = 44, 64
    overlap = 5
    display_n = min(n, 12)

    total_width = (display_n - 1) * overlap + small_w
    start_x = (SCREEN_WIDTH - total_width) // 2
    card_y = 50

    for i in range(display_n):
        x = start_x + i * overlap
        draw_card_back(surface, x, card_y, size=(small_w, small_h))

    name_font = get_font(FONT_SIZE_SMALL)
    name_surf = name_font.render(name, True, COLOR_TEXT_YELLOW)
    name_x = start_x + total_width - name_surf.get_width()
    name_y = card_y - name_surf.get_height() - 4
    surface.blit(name_surf, (name_x, name_y))

    if is_dealer:
        icon = _get_dizhu_icon((28, 28))
        if icon:
            surface.blit(icon, (name_x - 34, name_y))

    count_font = get_font(FONT_SIZE_SMALL)
    count_surf = count_font.render(f"剩{n}张", True, COLOR_TEXT_YELLOW)
    count_x = start_x + total_width - count_surf.get_width()
    count_y = card_y + small_h + 4
    surface.blit(count_surf, (count_x, count_y))


def draw_play_area_shengji(surface, current_trick, power_eval, names=None, skip_player=None, passes=None):
    """绘制当前轮出牌区域"""
    if names is None:
        names = ["你", "左家", "对家", "右家"]

    # 整体往中间挪，避免遮挡边缘对手信息
    positions = [
        (SCREEN_WIDTH // 2, 420),       # 底部（居中）
        (360, 340),                      # 左侧（左对齐）
        (SCREEN_WIDTH // 2, 220),        # 上方（居中）
        (SCREEN_WIDTH - 360, 340),       # 右侧（右对齐）
    ]

    CARD_W = 80
    CARD_H = 115
    MAX_W = 4 * (CARD_W + 4)  # 4张平铺的最大宽度

    # 先画pass（不要）
    if passes:
        font = get_font(FONT_SIZE_MEDIUM)
        for p in passes:
            if p == skip_player:
                continue
            cx, cy = positions[p]
            text = font.render("不要", True, COLOR_TEXT_YELLOW)
            surface.blit(text, (cx - text.get_width() // 2, cy + 20))

    if not current_trick:
        return

    for player_idx, cards, hand in current_trick:
        if player_idx == skip_player:
            continue
        cx, cy = positions[player_idx]
        n = len(cards)

        # 超过4张时重叠显示，总宽不超过4张平铺
        if n > 4:
            step = MAX_W // n
            total_w = n * step
        else:
            step = CARD_W + 4
            total_w = n * step

        # 对齐方式：左侧左对齐，右侧右对齐，底部和上方居中
        if player_idx == 1:       # 左侧，左对齐
            start_x = cx
        elif player_idx == 3:     # 右侧，右对齐
            start_x = cx - total_w
        else:                     # 底部和上方，居中
            start_x = cx - total_w // 2

        for i, card in enumerate(cards):
            x = start_x + i * step
            draw_card(surface, card, x, cy, size=(CARD_W, CARD_H))


def draw_info_panel_shengji(surface, game, names=None):
    """左上角信息面板"""
    if names is None:
        names = ["你", "左家", "对家", "右家"]

    font = get_font(FONT_SIZE_SMALL)
    y = 20
    x = 20

    suit_name = {None: "无主", 'spade': '黑桃', 'heart': '红桃', 'diamond': '方块', 'club': '梅花'}
    dealer_name = names[game.dealer] if game.dealer >= 0 else "未确定"
    trump_text = suit_name.get(game.trump_suit, "未确定")

    texts = [
        f"打 {game.level}",
        f"主花色: {trump_text}",
        f"庄家: {dealer_name}",
        f"庄家方得分: {game.scores[0]}",
        f"抓分方得分: {game.scores[1]}",
        f"轮到: {names[game.current_player]}",
    ]

    if game.phase == PHASE_ENDED and game.winner_team >= 0:
        win_text = "庄家方胜利" if game.winner_team == 0 else "抓分方胜利"
        texts.append(f"结果: {win_text}")

    line_h = font.size("测")[1] + 1  # 不小于字号实际渲染高度，避免行间重叠
    panel = pygame.Rect(x - 10, y - 10, 280, len(texts) * line_h + 20)
    s = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
    s.fill(COLOR_PANEL)
    surface.blit(s, panel.topleft)

    for i, t in enumerate(texts):
        surf = font.render(t, True, COLOR_TEXT)
        surface.blit(surf, (x, y + i * line_h))


def _apply_names(msg, names):
    """把消息里的 玩家N/庄家N 替换成实际昵称"""
    for i, name in enumerate(names):
        msg = msg.replace(f"玩家{i}", name).replace(f"庄家{i}", name)
    return msg


def draw_messages_shengji(surface, messages, names=None):
    """右上角消息日志（按面板宽度自动换行，高度自适应，底缘不超过底牌缩略图区域）"""
    if not messages:
        return
    if names is None:
        names = ["你", "左家", "对家", "右家"]
    font = get_font(FONT_SIZE_SMALL)
    panel_w = 360
    panel_x = SCREEN_WIDTH - 20 - panel_w
    text_x = panel_x + 10
    text_w = panel_w - 20
    y = 20
    line_h = 40
    max_lines = 4  # 面板底缘保持在 y≈205 以内，不压到底牌缩略图

    lines = []
    for msg in messages:
        lines.extend(wrap_text(font, _apply_names(msg, names), text_w))
    lines = lines[-max_lines:]

    panel = pygame.Rect(panel_x, y - 10, panel_w, len(lines) * line_h + 20)
    s = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
    s.fill(COLOR_PANEL)
    surface.blit(s, panel.topleft)
    for i, line in enumerate(lines):
        surf = font.render(line, True, COLOR_TEXT)
        surface.blit(surf, (text_x, y + i * line_h))


def draw_captured_cards(surface, captured, scores):
    """顶部展示双方吃到的分牌（5/10/K）。庄家方在左上，抓分方在右上（右对齐）。"""
    font = get_font(FONT_SIZE_SMALL)
    card_w, card_h = 33, 48
    step = 7
    label_y = 8
    row_y0 = 50
    row_gap = 50   # 两行时底缘 148，不超过顶部出牌区（y=220）和闹钟区域
    # (标签, 队伍, 左缘, 右缘, 是否右对齐)
    groups = [
        ("庄家方", 0, 300, 860, False),   # 信息面板（x≤290）之右
        ("抓分方", 1, 920, 1210, True),   # 顶部闹钟（x≤914）之右、消息面板（x=1220）之左
    ]
    for label, team, x0, x1, right_align in groups:
        cards = captured[team]
        text = f"{label} {scores[team]}分"
        surf = font.render(text, True, COLOR_TEXT_YELLOW)
        tx = x1 - surf.get_width() if right_align else x0
        surface.blit(surf, (tx, label_y))
        if not cards:
            continue
        max_per_row = max(1, (x1 - x0 - card_w) // step + 1)
        rows = [cards[i:i + max_per_row] for i in range(0, len(cards), max_per_row)][:2]
        for r, row in enumerate(rows):
            y = row_y0 + r * row_gap
            for i, card in enumerate(row):
                x = x1 - card_w - i * step if right_align else x0 + i * step
                draw_card(surface, card, x, y, size=(card_w, card_h))


def draw_bottom_cards(surface, bottom_cards, center_y=240):
    """绘制底牌（叫主/扣底阶段，放在屏幕中央）"""
    if not bottom_cards:
        return
    n = len(bottom_cards)
    total_w = n * (SJ_CARD_W + 5)
    start_x = SCREEN_WIDTH // 2 - total_w // 2
    y = center_y

    font = get_font(FONT_SIZE_SMALL)
    label = font.render("底牌", True, COLOR_TEXT_YELLOW)
    surface.blit(label, (SCREEN_WIDTH // 2 - label.get_width() // 2, y - 32))

    for i, card in enumerate(bottom_cards):
        x = start_x + i * (SJ_CARD_W + 5)
        draw_card(surface, card, x, y, size=(SJ_CARD_W, SJ_CARD_H))


def draw_bottom_cards_mini(surface, bottom_cards):
    """绘制底牌缩略图（出牌阶段，放在右上角消息面板下方）"""
    if not bottom_cards:
        return
    n = len(bottom_cards)
    small_w, small_h = 40, 58
    gap = 3
    total_w = n * small_w + (n - 1) * gap

    # 放在右上角消息面板下方
    x = SCREEN_WIDTH - total_w - 30
    y = 215

    font = get_font(FONT_SIZE_SMALL)
    label = font.render("底牌", True, COLOR_TEXT_YELLOW)
    # 标签竖排，放在牌左侧同一行
    label_rot = pygame.transform.rotate(label, -90)
    label_x = x - label_rot.get_width() - 5
    label_y = y + (small_h - label_rot.get_height()) // 2
    surface.blit(label_rot, (label_x, label_y))

    for i, card in enumerate(bottom_cards):
        cx = x + i * (small_w + gap)
        draw_card(surface, card, cx, y, size=(small_w, small_h))
