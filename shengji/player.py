"""
四副牌升级人类玩家交互（多行选牌）。
"""
import pygame
import sys
sys.path.insert(0, '..')
from common.constants import *


class HumanPlayerShengji:
    def __init__(self):
        self.selected_indices = set()

    def handle_click(self, mouse_pos, click_areas):
        """
        处理点击选牌。
        click_areas: [(x, y, w, h, original_index), ...]
        返回是否有点击到牌
        """
        x, y = mouse_pos
        clicked = False
        # 倒序遍历，优先点中上层牌
        for i in range(len(click_areas) - 1, -1, -1):
            cx, cy, cw, ch, orig_idx = click_areas[i]
            rect = pygame.Rect(cx, cy, cw, ch)
            if rect.collidepoint(x, y):
                if orig_idx in self.selected_indices:
                    self.selected_indices.remove(orig_idx)
                else:
                    self.selected_indices.add(orig_idx)
                clicked = True
                break
        return clicked

    def get_selected_cards(self, cards):
        """获取当前选中的牌"""
        return [cards[i] for i in sorted(self.selected_indices) if 0 <= i < len(cards)]

    def clear_selection(self):
        self.selected_indices.clear()

    def select_cards(self, indices):
        """按索引选中牌（用于提示）"""
        self.selected_indices = set(indices)

    def find_hint(self, game):
        """
        找到一个提示。
        返回 (success, indices) 或 (False, [])
        """
        player = 0
        legal = game.get_legal_plays(player)
        if not legal:
            return False, []

        # 找一手最小的牌
        def sort_key(p):
            return (len(p), max(game.power_eval.power(c) for c in p))

        legal.sort(key=sort_key)
        chosen = legal[0]
        cards = game.player_cards[player]
        indices = []
        used = set()
        for c in chosen:
            for i, hand_c in enumerate(cards):
                if hand_c == c and i not in used:
                    indices.append(i)
                    used.add(i)
                    break
        return True, indices
