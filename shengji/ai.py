"""
四副牌升级AI（简化版）。
"""
import random
import sys
sys.path.insert(0, '..')
from common.cards import JOKERS, is_score_card
from shengji.engine import get_shengji_hand_type, can_beat_shengji


def choose_lead(game, legal):
    """首家领出选牌（AI 与人类提示共用）。
    优先出副牌的组合牌（拖拉机/四条/三条/对子）：张数最多且最大牌力最小者；
    没有合适的副牌组合则出最小单张（副牌优先）；主牌组合保留不轻易拆。
    """
    power = game.power_eval

    def max_power(p):
        return max(power.power(c) for c in p)

    def has_trump(p):
        return any(power.is_trump(c) for c in p)

    side_combos = [p for p in legal if len(p) >= 2 and not has_trump(p)]
    if side_combos:
        side_combos.sort(key=lambda p: (-len(p), max_power(p)))
        return side_combos[0]

    singles = [p for p in legal if len(p) == 1]
    side_singles = [p for p in singles if not has_trump(p)]
    pool = side_singles or singles or legal
    pool.sort(key=max_power)
    return pool[0]


def choose_follow(game, legal):
    """跟牌选牌（AI 与人类提示共用）。
    最小代价：先尽量少送分牌（5/10/K），再取最大牌力最小者。
    候选已由 engine.get_legal_plays 保证满足跟牌型规则（有对必跟对等）。
    """
    power = game.power_eval

    def cost(p):
        score_cards = sum(1 for c in p if is_score_card(c))
        return (score_cards, max(power.power(c) for c in p))

    return min(legal, key=cost)


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
        legal = [p for p in game.get_legal_plays(self.player_id) if p]

        if not legal:
            # 没有合法出牌，出最小牌的n张（避免单张 fallback 导致卡死）
            n = len(game.current_trick[0][1]) if game.current_trick else 1
            if cards:
                sorted_cards = sorted(cards, key=lambda c: game.power_eval.power(c))
                if len(sorted_cards) >= n:
                    return "play", sorted_cards[:n]
            return "pass", []

        if game.current_trick:
            chosen = choose_follow(game, legal)
        else:
            chosen = choose_lead(game, legal)
        return "play", chosen
