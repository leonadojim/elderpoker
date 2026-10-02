"""
四副牌升级AI（简化版）。
"""
import random
import sys
sys.path.insert(0, '..')
from common.cards import JOKERS
from shengji.engine import get_shengji_hand_type, can_beat_shengji


class ShengjiAI:
    def __init__(self, player_id):
        self.player_id = player_id

    def decide_bid(self, game):
        """
        决定是否亮主。
        返回 (action, cards)
        action: "bid" 或 "pass"
        """
        cards = game.player_cards[self.player_id]
        level = game.level

        # 找所有当前级别的牌
        level_cards = [c for c in cards if c[0] == level]
        jokers = [c for c in cards if c[0] in JOKERS]

        # 优先亮对子级别
        from collections import Counter
        suit_counts = Counter(c[1] for c in level_cards)
        for suit, count in suit_counts.items():
            if count >= 2:
                bid_cards = [c for c in level_cards if c[1] == suit][:2]
                return "bid", bid_cards

        # 其次亮单张级别
        if level_cards:
            return "bid", [level_cards[0]]

        # 有4张王亮无主
        if len(jokers) >= 4:
            return "bid", jokers[:4]

        return "pass", []

    def decide_discard(self, game):
        """
        庄家扣底：选出8张最不需要的牌。
        策略：优先扣小牌、非分牌。
        """
        cards = game.player_cards[self.player_id]
        # 按牌力排序，扣最小的8张
        sorted_cards = sorted(cards, key=lambda c: game.power_eval.power(c))
        return sorted_cards[:8]

    def decide_play(self, game):
        """
        决定出牌。
        返回 (action, cards)
        """
        cards = game.player_cards[self.player_id]
        legal = game.get_legal_plays(self.player_id)

        if not legal:
            # 没有合法出牌，出最小牌的n张（避免单张 fallback 导致卡死）
            n = len(game.current_trick[0][1]) if game.current_trick else 1
            if cards:
                sorted_cards = sorted(cards, key=lambda c: game.power_eval.power(c))
                if len(sorted_cards) >= n:
                    return "play", sorted_cards[:n]
            return "pass", []

        # 过滤空列表并排序：优先出小牌、少张的
        legal = [p for p in legal if p]
        if not legal:
            if cards:
                return "play", [cards[0]]
            return "pass", []
        
        def sort_key(p):
            return (len(p), max(game.power_eval.power(c) for c in p))

        legal.sort(key=sort_key)
        chosen = legal[0]
        return "play", chosen
