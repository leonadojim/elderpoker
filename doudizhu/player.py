import pygame
import sys
sys.path.insert(0, '..')
from common.constants import CARD_WIDTH, CARD_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT
from doudizhu.engine import get_hand_type, can_beat
from common.cards import RANK_POWER


class HumanPlayer:
    def __init__(self):
        self.selected_indices = set()

    def handle_click(self, mouse_pos, card_positions):
        x, y = mouse_pos
        clicked = False
        for i in range(len(card_positions) - 1, -1, -1):
            cx, cy = card_positions[i]
            rect = pygame.Rect(cx, cy - 15, CARD_WIDTH, CARD_HEIGHT + 15)
            if rect.collidepoint(x, y):
                if i in self.selected_indices:
                    self.selected_indices.remove(i)
                else:
                    self.selected_indices.add(i)
                clicked = True
                break
        return clicked

    def get_selected_cards(self, cards):
        return [cards[i] for i in sorted(self.selected_indices) if 0 <= i < len(cards)]

    def clear_selection(self):
        self.selected_indices.clear()

    def select_cards(self, indices):
        self.selected_indices = set(indices)

    def find_hint(self, game):
        player = 0
        is_first = (game.last_play is None or game.consecutive_pass >= 2)
        last_hand = game.last_play[2] if game.last_play and not is_first else None
        legal = game.get_legal_plays(player, last_hand, is_first)
        if not legal:
            return False, []

        def sort_key(p):
            h = get_hand_type(p)
            return (len(p), max(RANK_POWER[c[0]] for c in p))

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
