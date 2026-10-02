import random
import sys
sys.path.insert(0, '..')
from common.constants import DIFFICULTY_EASY, DIFFICULTY_NORMAL, DIFFICULTY_HARD
from common.cards import RANK_POWER, JOKERS
from doudizhu.engine import get_hand_type, can_beat, card_power, HAND_ROCKET, HAND_BOMB, HAND_STRAIGHT, HAND_DOUBLE_STRAIGHT, HAND_PLAIN, HAND_PLAIN_WING_SINGLE, HAND_PLAIN_WING_PAIR, HAND_TRIPLE_SINGLE, HAND_TRIPLE_PAIR, HAND_TRIPLE, HAND_PAIR


def _evaluate_hand_power(cards):
    power = 0
    has_rocket = ('小王', None) in cards and ('大王', None) in cards
    if has_rocket:
        power += 5

    rank_counts = {}
    for c in cards:
        rank_counts[c[0]] = rank_counts.get(c[0], 0) + 1

    bomb_count = 0
    for r, cnt in rank_counts.items():
        if cnt == 4:
            power += 4
            bomb_count += 1

    for r in ['2', 'A', 'K']:
        if r in rank_counts:
            power += rank_counts[r] * 1.5

    if '小王' in rank_counts:
        power += 2.5
    if '大王' in rank_counts:
        power += 3

    from common.cards import RANKS
    unique_ranks = sorted(set([RANK_POWER[c[0]] for c in cards if c[0] in RANKS]))
    if len(unique_ranks) >= 5:
        consecutive = 1
        for i in range(1, len(unique_ranks)):
            if unique_ranks[i] == unique_ranks[i-1] + 1:
                consecutive += 1
            else:
                if consecutive >= 5:
                    power += 1.5
                consecutive = 1

    return power, bomb_count, has_rocket


def _choose_smallest_beatable(beatable):
    beatable.sort(key=lambda p: (len(p), max(card_power(c) for c in p)))
    return beatable[0]


def _choose_optimal_beatable(beatable, cards, is_teammate_play=False):
    beatable.sort(key=lambda p: (len(p), max(card_power(c) for c in p)))
    if not is_teammate_play:
        return beatable[0]

    best = beatable[0]
    if len(beatable) > 1:
        def breaks_good(cand):
            h = get_hand_type(cand)
            rank_counts = {}
            for c in cards:
                rank_counts[c[0]] = rank_counts.get(c[0], 0) + 1
            for c in cand:
                if rank_counts.get(c[0], 0) == 4:
                    return True
                if c[0] in ['2', '大王', '小王'] and len(cand) > 1:
                    return True
            return False
        if breaks_good(best):
            for alt in beatable[1:3]:
                if not breaks_good(alt):
                    return alt
    return best


class AIPlayer:
    def __init__(self, player_id, difficulty=DIFFICULTY_EASY):
        self.player_id = player_id
        self.difficulty = difficulty

    def decide_bid(self, game):
        cards = game.player_cards[self.player_id]
        power, bomb_count, has_rocket = _evaluate_hand_power(cards)

        if self.difficulty == DIFFICULTY_EASY:
            if random.random() < 0.35:
                power -= 4
            if random.random() < 0.2:
                return 0

        elif self.difficulty == DIFFICULTY_NORMAL:
            pass

        else:
            power += 1
            if has_rocket or bomb_count >= 2:
                return 3

        if power >= 9:
            return 3
        elif power >= 6:
            return 2
        elif power >= 3:
            return 1
        else:
            return 0

    def decide_play(self, game):
        cards = game.player_cards[self.player_id]
        is_first = (game.last_play is None or game.consecutive_pass >= 2)
        last_hand = game.last_play[2] if game.last_play and not is_first else None

        legal = game.get_legal_plays(self.player_id, last_hand, is_first)
        if not legal:
            if is_first:
                return "play", [cards[0]]
            return "pass", []

        if not is_first and last_hand is not None:
            return self._follow_play(game, cards, legal, last_hand)

        return self._lead_play(game, cards, legal)

    def _follow_play(self, game, cards, legal, last_hand):
        last_player = game.last_play[0]
        is_teammate = (game.landlord != self.player_id and
                       last_player != self.player_id and
                       last_player != game.landlord)

        beatable = [p for p in legal if can_beat(get_hand_type(p), last_hand)]
        if not beatable:
            return "pass", []

        if self.difficulty == DIFFICULTY_EASY:
            if is_teammate and random.random() < 0.45:
                return "pass", []
            chosen = _choose_smallest_beatable(beatable)
            if random.random() < 0.25 and len(beatable) > 1:
                chosen = beatable[1]
            return "play", chosen

        elif self.difficulty == DIFFICULTY_NORMAL:
            if is_teammate:
                return "pass", []
            chosen = _choose_smallest_beatable(beatable)
            return "play", chosen

        else:
            if is_teammate:
                t, p, l = last_hand
                if p >= RANK_POWER['K'] and t not in (HAND_BOMB, HAND_ROCKET):
                    return "pass", []
                chosen = _choose_optimal_beatable(beatable, cards, True)
                return "play", chosen
            else:
                chosen = _choose_optimal_beatable(beatable, cards, False)
                return "play", chosen

    def _lead_play(self, game, cards, legal):
        if self.difficulty == DIFFICULTY_EASY:
            if random.random() < 0.3:
                chosen = random.choice(legal[:min(5, len(legal))])
            else:
                legal.sort(key=self._play_value_easy)
                chosen = legal[0]
            return "play", chosen

        elif self.difficulty == DIFFICULTY_NORMAL:
            legal.sort(key=self._play_value_normal)
            chosen = legal[0]
            return "play", chosen

        else:
            legal.sort(key=self._play_value_hard)
            chosen = legal[0]
            if len(cards) <= 3:
                legal.sort(key=lambda p: max(card_power(c) for c in p), reverse=True)
                chosen = legal[0]
            return "play", chosen

    def _play_value_easy(self, p):
        h = get_hand_type(p)
        n = len(p)
        max_p = max(card_power(c) for c in p)
        return (random.random() * 0.5, n, max_p)

    def _play_value_normal(self, p):
        h = get_hand_type(p)
        n = len(p)
        max_p = max(card_power(c) for c in p)
        if h[0] in (HAND_STRAIGHT, HAND_DOUBLE_STRAIGHT, HAND_PLAIN,
                    HAND_PLAIN_WING_SINGLE, HAND_PLAIN_WING_PAIR):
            return (0, n, max_p)
        return (1, n, max_p)

    def _play_value_hard(self, p):
        h = get_hand_type(p)
        n = len(p)
        max_p = max(card_power(c) for c in p)
        ht = h[0]

        if ht == HAND_ROCKET:
            return (10, 0, 0)
        if ht == HAND_BOMB:
            return (9, 0, 0)

        if ht in (HAND_STRAIGHT, HAND_DOUBLE_STRAIGHT, HAND_PLAIN,
                  HAND_PLAIN_WING_SINGLE, HAND_PLAIN_WING_PAIR):
            return (0, n, max_p)

        if ht in (HAND_TRIPLE_SINGLE, HAND_TRIPLE_PAIR):
            return (1, n, max_p)

        if ht == HAND_TRIPLE:
            return (2, n, max_p)

        if ht == HAND_PAIR:
            return (3, n, max_p)

        return (4, n, max_p)
