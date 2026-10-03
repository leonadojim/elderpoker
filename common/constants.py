import os
import pygame

# ==================== 屏幕设置（老人专用大屏幕）====================
SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900
FPS = 30

# ==================== 颜色 ====================
COLOR_TABLE = (0, 100, 0)          # 深绿色桌布
COLOR_TABLE_BORDER = (0, 60, 0)
COLOR_CARD_BG = (255, 255, 255)    # 牌背景白色
COLOR_CARD_BORDER = (0, 0, 0)      # 牌边框黑色
COLOR_RED = (200, 0, 0)            # 红桃/方块
COLOR_BLACK = (0, 0, 0)            # 黑桃/梅花
COLOR_GOLD = (255, 215, 0)         # 金色（王）
COLOR_BUTTON_BG = (220, 180, 100)  # 按钮背景
COLOR_BUTTON_HOVER = (240, 200, 120)
COLOR_BUTTON_TEXT = (80, 40, 0)
COLOR_PANEL = (0, 0, 0, 180)       # 半透明面板
COLOR_TEXT = (255, 255, 255)
COLOR_TEXT_YELLOW = (255, 255, 0)
COLOR_HIGHLIGHT = (255, 255, 0, 100)

# ==================== 牌尺寸 ====================
# 标准尺寸（斗地主用）
CARD_WIDTH = 110
CARD_HEIGHT = 158
# 小尺寸（四副牌升级用，52张牌多行显示）
SMALL_CARD_WIDTH = 80
SMALL_CARD_HEIGHT = 115
CARD_CORNER_RADIUS = 8

# ==================== 字体大小 ====================
FONT_SIZE_LARGE = 56
FONT_SIZE_MEDIUM = 36
FONT_SIZE_SMALL = 28
FONT_SIZE_CARD = 32

# ==================== 素材路径 ====================
# 必须用绝对路径：安卓上 SDL 对相对路径会去 APK assets 里找（找不到），绝对路径才走文件系统
ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "cards")

# ==================== 难度 ====================
DIFFICULTY_EASY = "easy"
DIFFICULTY_NORMAL = "normal"
DIFFICULTY_HARD = "hard"

# ==================== AI昵称池（老年人风格）====================
AI_NICKNAMES = [
    "花开富贵", "吉祥平安", "幸福一生", "万事如意",
    "快乐每一天", "顺心如意", "家和万事兴", "平安是福",
    "笑口常开", "福寿安康", "好运连连", "恭喜发财",
    "年年有余", "春风得意", "金玉满堂", "心想事成",
    "国泰民安", "龙腾虎跃", "喜气洋洋", "步步高升",
]
