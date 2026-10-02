"""
牌的基础定义与工具，供斗地主和升级共用。
"""
from .constants import COLOR_RED, COLOR_BLACK, COLOR_GOLD, ASSET_DIR

# ==================== 花色 ====================
SUITS = {
    'spade': ('♠', COLOR_BLACK),   # 黑桃
    'heart': ('♥', COLOR_RED),     # 红桃
    'diamond': ('♦', COLOR_RED),   # 方块
    'club': ('♣', COLOR_BLACK),    # 梅花
}

SUIT_LIST = ['spade', 'heart', 'diamond', 'club']

# ==================== 点数 ====================
RANKS = ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2']
JOKERS = ['小王', '大王']

# ==================== 牌力映射（斗地主用，升级另有主牌逻辑）====================
RANK_POWER = {}
for i, r in enumerate(RANKS):
    RANK_POWER[r] = i
RANK_POWER['小王'] = 13
RANK_POWER['大王'] = 14

# ==================== 素材文件名映射 ====================
SUIT_TO_NAME = {
    'spade': 'Spade',
    'heart': 'Heart',
    'diamond': 'Diamond',
    'club': 'Club',
}
RANK_TO_NAME = {
    '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8',
    '9': '9', '10': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A', '2': '2'
}
JOKER_TO_NAME = {
    '小王': 'JOKER-B',
    '大王': 'JOKER-A',
}


def card_power(card):
    """返回单张牌的牌力数值（斗地主通用）"""
    return RANK_POWER[card[0]]


def sort_cards(cards):
    """按牌力从小到大排序"""
    return sorted(cards, key=card_power)


def is_score_card(card):
    """判断是否为分牌（5=5分, 10=10分, K=10分）"""
    rank = card[0]
    if rank == '5':
        return 5
    elif rank == '10':
        return 10
    elif rank == 'K':
        return 10
    return 0


def format_card_text(card):
    """格式化牌的语音文本"""
    rank, suit = card
    if rank in JOKERS:
        return rank
    suit_names = {'spade': '黑桃', 'heart': '红桃', 'diamond': '方块', 'club': '梅花'}
    return f"{suit_names.get(suit, '')}{rank}"
