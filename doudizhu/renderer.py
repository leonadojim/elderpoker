"""
斗地主专用渲染模块（3人布局）。
"""
import pygame
import os
import sys
sys.path.insert(0, '..')
from common.constants import *
from common.renderer_base import get_font, get_card_image, draw_card, draw_card_back, draw_button, draw_table, wrap_text
from doudizhu.engine import PHASE_BIDDING, PHASE_PLAYING, PHASE_ENDED


def draw_player_area(surface, game, player_idx, selected_indices=None, names=None, landlord=-1):
    """绘制玩家的手牌区域"""
    if selected_indices is None:
        selected_indices = set()
    if names is None:
        names = ["你", "玩家A", "玩家B"]

    cards = game.player_cards[player_idx]
    n = len(cards)

    dizhu_small = None
    if landlord >= 0:
        # 绝对路径：安卓上 SDL 对相对路径会去 APK assets 里找（找不到）
        dizhu_path = os.path.join(os.path.dirname(ASSET_DIR), "logos", "dizhu.png")
        if os.path.exists(dizhu_path):
            raw = pygame.image.load(dizhu_path).convert_alpha()
            dizhu_small = pygame.transform.smoothscale(raw, (56, 56))

    if player_idx == 0:
        total_width = min(SCREEN_WIDTH - 260, n * (CARD_WIDTH + 12))
        start_x = (SCREEN_WIDTH - total_width) // 2
        gap = total_width // max(n, 1) if n > 1 else 0
        y = SCREEN_HEIGHT - CARD_HEIGHT - 70
        for i, card in enumerate(cards):
            x = start_x + i * (gap if n > 1 else 0)
            if n == 1:
                x = (SCREEN_WIDTH - CARD_WIDTH) // 2
            draw_card(surface, card, x, y, selected=(i in selected_indices))
        if player_idx == landlord and dizhu_small:
            surface.blit(dizhu_small, (20, y + CARD_HEIGHT - 56))
        return [(start_x + i * (gap if n > 1 else 0), y) for i in range(n)]

    elif player_idx == 1:
        start_y = 220
        gap = 16
        name_font = get_font(FONT_SIZE_MEDIUM)
        name_surf = name_font.render(names[1], True, COLOR_TEXT_YELLOW)
        surface.blit(name_surf, (10, 172))
        if player_idx == landlord and dizhu_small:
            surface.blit(dizhu_small, (10 + name_surf.get_width() + 8, 172))
        for i in range(n):
            x = 10
            y = start_y + i * gap
            draw_card_back(surface, x, y)
        font = get_font(FONT_SIZE_MEDIUM)
        bottom_y = start_y + (n - 1) * gap + CARD_HEIGHT + 16
        count_surf = font.render(f"剩{n}张", True, COLOR_TEXT_YELLOW)
        surface.blit(count_surf, (10, bottom_y))
        return []

    else:
        start_y = 220
        gap = 16
        name_font = get_font(FONT_SIZE_MEDIUM)
        name_surf = name_font.render(names[2], True, COLOR_TEXT_YELLOW)
        name_x = SCREEN_WIDTH - 10 - name_surf.get_width()
        surface.blit(name_surf, (name_x, 172))
        if player_idx == landlord and dizhu_small:
            surface.blit(dizhu_small, (name_x - 66, 172))
        for i in range(n):
            x = SCREEN_WIDTH - CARD_WIDTH - 10
            y = start_y + i * gap
            draw_card_back(surface, x, y)
        font = get_font(FONT_SIZE_MEDIUM)
        bottom_y = start_y + (n - 1) * gap + CARD_HEIGHT + 16
        count_surf = font.render(f"剩{n}张", True, COLOR_TEXT_YELLOW)
        surface.blit(count_surf, (SCREEN_WIDTH - CARD_WIDTH - 10, bottom_y))
        return []


def draw_play_area(surface, game):
    """绘制出牌区域"""
    if game.last_play:
        player, cards, hand = game.last_play
        names = ["你", "玩家A", "玩家B"]
        n = len(cards)
        total_w = n * (CARD_WIDTH + 5)

        if player == 0:
            y = 370
            start_x = SCREEN_WIDTH // 2 - total_w // 2
        elif player == 1:
            y = 350
            start_x = 20 + CARD_WIDTH + 20
        else:
            y = 350
            start_x = SCREEN_WIDTH - CARD_WIDTH - 20 - total_w

        for i, card in enumerate(cards):
            draw_card(surface, card, start_x + i * (CARD_WIDTH + 5), y)

    if game.phase != PHASE_BIDDING and game.bottom_cards:
        bx = SCREEN_WIDTH // 2 - (3 * (CARD_WIDTH + 5)) // 2
        by = 50
        font = get_font(FONT_SIZE_SMALL)
        surface.blit(font.render("底牌", True, COLOR_TEXT_YELLOW), (SCREEN_WIDTH // 2 - 20, by - 40))
        for i, card in enumerate(game.bottom_cards):
            draw_card(surface, card, bx + i * (CARD_WIDTH + 5), by)


def draw_info_panel(surface, game, difficulty="简单", names=None):
    """绘制信息面板（左上角），行距不小于字号实际渲染高度，尺寸按内容自适应"""
    if names is None:
        names = ["你", "玩家A", "玩家B"]
    font = get_font(FONT_SIZE_SMALL)
    y = 20
    x = 20
    line_h = font.size("测")[1] + 1

    texts = []
    texts.append(f"难度: {difficulty}  叫分: {game.current_bid}")
    if game.landlord >= 0:
        texts.append(f"地主: {names[game.landlord]}")
    else:
        texts.append("地主: 未确定")
    texts.append(f"轮到: {names[game.current_player]}")
    if game.phase == PHASE_ENDED and game.winner >= 0:
        win_team = "农民" if game.winner != game.landlord else "地主"
        texts.append(f"赢家: {names[game.winner]} ({win_team})")

    panel_w = max(240, max(font.size(t)[0] for t in texts) + 20)
    panel = pygame.Rect(x - 10, y - 10, panel_w, len(texts) * line_h + 20)
    s = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
    s.fill(COLOR_PANEL)
    surface.blit(s, panel.topleft)

    for i, t in enumerate(texts):
        surf = font.render(t, True, COLOR_TEXT)
        surface.blit(surf, (x, y + i * line_h))


def draw_messages(surface, game):
    """绘制消息日志（右上角，自动换行，高度自适应，底缘不碰到右侧玩家名字）"""
    if not game.messages:
        return
    font = get_font(FONT_SIZE_SMALL)
    panel_w = 360
    panel_x = SCREEN_WIDTH - 20 - panel_w
    text_x = panel_x + 10
    text_w = panel_w - 20
    y = 20
    line_h = 40
    max_lines = 3  # 面板底缘保持在 y≈165 以内，避开右侧玩家名字（y=172）

    lines = []
    for msg in game.messages:
        lines.extend(wrap_text(font, msg, text_w))
    lines = lines[-max_lines:]

    panel = pygame.Rect(panel_x, y - 10, panel_w, len(lines) * line_h + 20)
    s = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
    s.fill(COLOR_PANEL)
    surface.blit(s, panel.topleft)
    for i, line in enumerate(lines):
        surf = font.render(line, True, COLOR_TEXT)
        surface.blit(surf, (text_x, y + i * line_h))


def draw_card_panel(surface, cards_list, title_text, top_y=10, landlord=-1, names=None):
    """显示三家手牌面板"""
    if names is None:
        names = ["你", "玩家A", "玩家B"]
    panel_w = 1560
    panel_h = 730
    panel_x = (SCREEN_WIDTH - panel_w) // 2
    panel_y = top_y
    panel = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

    s = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    s.fill((10, 30, 10, 235))
    surface.blit(s, panel.topleft)
    pygame.draw.rect(surface, COLOR_GOLD, panel, width=5, border_radius=20)

    title_font = get_font(FONT_SIZE_LARGE + 12)
    title = title_font.render(title_text, True, COLOR_TEXT_YELLOW)
    tx = panel_x + panel_w // 2 - title.get_width() // 2
    surface.blit(title, (tx, panel_y + 18))

    line_y = panel_y + 18 + title.get_height() + 8
    pygame.draw.line(surface, COLOR_GOLD,
                     (panel_x + 60, line_y),
                     (panel_x + panel_w - 60, line_y), 3)

    small_card_w = 55
    small_card_h = 80
    card_offset = 78
    start_y = panel_y + 160
    row_gap = 195

    dizhu_img = None
    if landlord >= 0:
        dizhu_path = os.path.join(os.path.dirname(ASSET_DIR), "logos", "dizhu.png")
        if os.path.exists(dizhu_path):
            raw = pygame.image.load(dizhu_path).convert_alpha()
            dizhu_img = pygame.transform.smoothscale(raw, (56, 56))

    for row, player_idx in enumerate([0, 1, 2]):
        cards = cards_list[player_idx] if player_idx < len(cards_list) else []
        n = len(cards)
        y = start_y + row * row_gap

        label_font = get_font(FONT_SIZE_MEDIUM + 4)
        label_text = f"{names[player_idx]}   {n} 张"
        label = label_font.render(label_text, True, COLOR_TEXT)
        text_w = label.get_width()
        text_h = label.get_height()
        pad_x = 22
        pad_y = 14
        label_bg = pygame.Rect(panel_x + 40, y - pad_y, text_w + pad_x * 2, text_h + pad_y * 2)
        pygame.draw.rect(surface, (20, 60, 20), label_bg, border_radius=8)
        pygame.draw.rect(surface, COLOR_GOLD, label_bg, width=2, border_radius=8)
        surface.blit(label, (panel_x + 40 + pad_x, y))

        if player_idx == landlord and dizhu_img:
            surface.blit(dizhu_img, (label_bg.right + 10, label_bg.centery - 28))

        if n > 0:
            usable_width = panel_w - 120
            gap = min(75, (usable_width - small_card_w) // max(n - 1, 1))
            total_width = small_card_w + (n - 1) * gap
            start_x = panel_x + panel_w // 2 - total_width // 2

            for i, card in enumerate(cards):
                x = start_x + i * gap
                img = get_card_image(card, (small_card_w, small_card_h))
                if img:
                    surface.blit(img, (x, y + card_offset))
                else:
                    rect = pygame.Rect(x, y + card_offset, small_card_w, small_card_h)
                    pygame.draw.rect(surface, COLOR_CARD_BG, rect, border_radius=4)
                    rank, suit = card
                    from common.cards import JOKERS, SUITS
                    c = COLOR_GOLD if rank in JOKERS else SUITS[suit][1]
                    sf = get_font(FONT_SIZE_SMALL).render(rank[:2], True, c)
                    surface.blit(sf, (x + 4, y + card_offset + 4))
