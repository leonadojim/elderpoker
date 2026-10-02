"""
基础渲染模块，供所有游戏共用。
"""
import pygame
import os
from .constants import *

# ==================== 字体缓存 ====================
_fonts = {}

_FONT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "fonts", "NotoSansCJKsc-Regular.otf",
)


def get_font(size):
    if size not in _fonts:
        if os.path.exists(_FONT_PATH):
            _fonts[size] = pygame.font.Font(_FONT_PATH, size)
        else:
            font = None
            for name in ("simhei", "microsoftyahei", "notosanscjksc",
                         "wenquanyizenhei", "droidsansfallback"):
                path = pygame.font.match_font(name)
                if path:
                    font = pygame.font.Font(path, size)
                    break
            _fonts[size] = font if font else pygame.font.Font(None, size)
    return _fonts[size]


# ==================== 图片缓存 ====================
_image_cache = {}


def _load_image(path, target_size=None):
    """加载图片并缓存（包含缩放结果）"""
    cache_key = (path, target_size)
    if cache_key not in _image_cache:
        if not os.path.exists(path):
            return None
        img = pygame.image.load(path).convert_alpha()
        if target_size:
            img = pygame.transform.smoothscale(img, target_size)
        _image_cache[cache_key] = img
    return _image_cache[cache_key]


def get_card_image(card, size=(CARD_WIDTH, CARD_HEIGHT)):
    """根据牌面获取素材图片"""
    from .cards import JOKERS, JOKER_TO_NAME, SUIT_TO_NAME, RANK_TO_NAME
    rank, suit = card
    if rank in JOKERS:
        filename = os.path.join(ASSET_DIR, f"{JOKER_TO_NAME[rank]}.png")
    else:
        filename = os.path.join(ASSET_DIR, f"{SUIT_TO_NAME[suit]}{RANK_TO_NAME[rank]}.png")
    return _load_image(filename, size)


def get_card_back(size=(CARD_WIDTH, CARD_HEIGHT)):
    """获取牌背素材"""
    path = os.path.join(ASSET_DIR, "Background.png")
    return _load_image(path, size)


# ==================== 绘制函数 ====================
def wrap_text(font, text, max_width):
    """按像素宽度把文本（含中文）折行，返回行列表。"""
    lines = []
    cur = ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if cur and font.size(cur + ch)[0] > max_width:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    lines.append(cur)
    return lines


def draw_rounded_rect(surface, color, rect, radius):
    """绘制圆角矩形"""
    pygame.draw.rect(surface, color, rect, border_radius=radius)


def draw_card(surface, card, x, y, selected=False, size=(CARD_WIDTH, CARD_HEIGHT)):
    """
    绘制一张扑克牌（使用素材图片）。
    card: (rank, suit) 或 ('小王',None)/('大王',None)
    selected: 是否被选中（抬起效果）
    size: (width, height) 元组
    """
    from .cards import SUITS, JOKERS, COLOR_GOLD
    w, h = size
    offset_y = -15 if selected else 0
    draw_y = y + offset_y

    img = get_card_image(card, size)
    if img:
        # 阴影
        shadow_rect = pygame.Rect(x + 3, draw_y + 3, w, h)
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 60))
        surface.blit(s, shadow_rect.topleft)
        surface.blit(img, (x, draw_y))
    else:
        # 素材缺失时回退到程序绘制
        bg_rect = pygame.Rect(x, draw_y, w, h)
        draw_rounded_rect(surface, COLOR_CARD_BG, bg_rect, CARD_CORNER_RADIUS)
        pygame.draw.rect(surface, COLOR_CARD_BORDER, bg_rect, width=2, border_radius=CARD_CORNER_RADIUS)
        rank, suit = card
        if rank in JOKERS:
            color = COLOR_GOLD
            font = get_font(FONT_SIZE_MEDIUM)
            text_surf = font.render(rank, True, color)
            text_rect = text_surf.get_rect(center=(x + w // 2, draw_y + h // 2))
            surface.blit(text_surf, text_rect)
        else:
            suit_char, color = SUITS[suit]
            font = get_font(FONT_SIZE_CARD)
            rank_surf = font.render(rank, True, color)
            surface.blit(rank_surf, (x + 8, draw_y + 8))
            suit_surf = font.render(suit_char, True, color)
            surface.blit(suit_surf, (x + 8, draw_y + 38))


def draw_card_back(surface, x, y, size=(CARD_WIDTH, CARD_HEIGHT)):
    """绘制牌背面（使用素材 Background.png）"""
    w, h = size
    img = get_card_back(size)
    if img:
        surface.blit(img, (x, y))
    else:
        # 素材缺失时回退到程序绘制
        bg_rect = pygame.Rect(x, y, w, h)
        draw_rounded_rect(surface, (30, 60, 120), bg_rect, CARD_CORNER_RADIUS)
        pygame.draw.rect(surface, (80, 120, 180), bg_rect, width=3, border_radius=CARD_CORNER_RADIUS)
        inner = pygame.Rect(x + 8, y + 8, w - 16, h - 16)
        pygame.draw.rect(surface, (50, 90, 150), inner, width=2, border_radius=4)
        pygame.draw.circle(surface, (80, 120, 180), (x + w // 2, y + h // 2), 15)


def draw_button(surface, text, x, y, w, h, hover=False):
    """绘制按钮，返回rect"""
    rect = pygame.Rect(x, y, w, h)
    color = COLOR_BUTTON_HOVER if hover else COLOR_BUTTON_BG
    draw_rounded_rect(surface, color, rect, 10)
    pygame.draw.rect(surface, (150, 100, 50), rect, width=3, border_radius=10)
    font = get_font(FONT_SIZE_MEDIUM)
    text_surf = font.render(text, True, COLOR_BUTTON_TEXT)
    text_rect = text_surf.get_rect(center=rect.center)
    surface.blit(text_surf, text_rect)
    return rect


def draw_table(surface):
    """绘制桌面背景（深绿色桌布）"""
    surface.fill(COLOR_TABLE)
    center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    pygame.draw.ellipse(surface, COLOR_TABLE_BORDER,
                        pygame.Rect(center[0] - 620, center[1] - 350, 1240, 700))
    pygame.draw.ellipse(surface, (0, 80, 0),
                        pygame.Rect(center[0] - 600, center[1] - 330, 1200, 660))
