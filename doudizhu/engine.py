import random
from collections import Counter
import sys
sys.path.insert(0, '..')
from common.cards import RANK_POWER, RANKS, JOKERS, SUITS, sort_cards, card_power

# ==================== 斗地主阶段 ====================
PHASE_DEALING = "dealing"
PHASE_BIDDING = "bidding"
PHASE_PLAYING = "playing"
PHASE_ENDED = "ended"

# ==================== 牌型定义 ====================
HAND_PASS = "pass"
HAND_SINGLE = "single"
HAND_PAIR = "pair"
HAND_TRIPLE = "triple"
HAND_TRIPLE_SINGLE = "triple_single"
HAND_TRIPLE_PAIR = "triple_pair"
HAND_STRAIGHT = "straight"
HAND_DOUBLE_STRAIGHT = "double_straight"
HAND_PLAIN = "plain"              # 飞机（连续三张）
HAND_PLAIN_WING_SINGLE = "plain_wing_single"
HAND_PLAIN_WING_PAIR = "plain_wing_pair"
HAND_BOMB = "bomb"
HAND_ROCKET = "rocket"
HAND_FOUR_TWO = "four_two"
HAND_FOUR_TWO_PAIRS = "four_two_pairs"


def get_hand_type(cards):
    """
    判断牌型。
    返回 (hand_type, primary_power, length) 或 None（非法）
    """
    if not cards:
        return None
    n = len(cards)
    ranks = [c[0] for c in cards]
    rank_counts = Counter(ranks)
    powers = sorted([RANK_POWER[r] for r in ranks])
    unique_powers = sorted(set(powers))

    # 王炸
    if n == 2 and set(ranks) == {'小王', '大王'}:
        return (HAND_ROCKET, 15, 1)

    # 单张
    if n == 1:
        return (HAND_SINGLE, powers[0], 1)

    # 对子
    if n == 2 and len(unique_powers) == 1:
        return (HAND_PAIR, powers[0], 1)

    # 三张
    if n == 3 and len(unique_powers) == 1:
        return (HAND_TRIPLE, powers[0], 1)

    # 三带一
    if n == 4:
        if sorted(rank_counts.values()) == [1, 3]:
            triple_rank = [r for r, cnt in rank_counts.items() if cnt == 3][0]
            return (HAND_TRIPLE_SINGLE, RANK_POWER[triple_rank], 1)

    # 三带二
    if n == 5:
        if sorted(rank_counts.values()) == [2, 3]:
            triple_rank = [r for r, cnt in rank_counts.items() if cnt == 3][0]
            return (HAND_TRIPLE_PAIR, RANK_POWER[triple_rank], 1)

    # 炸弹
    if n == 4 and len(unique_powers) == 1:
        return (HAND_BOMB, powers[0], 1)

    # 顺子 (5张及以上，单张连续，不能含2和王)
    if n >= 5 and len(unique_powers) == n:
        if all(p <= RANK_POWER['A'] for p in powers):
            if all(unique_powers[i+1] - unique_powers[i] == 1 for i in range(len(unique_powers)-1)):
                return (HAND_STRAIGHT, unique_powers[0], n)

    # 连对 (3对及以上，连续对子，不能含2和王)
    if n >= 6 and n % 2 == 0 and len(rank_counts) == n // 2:
        if all(cnt == 2 for cnt in rank_counts.values()):
            if all(p <= RANK_POWER['A'] for p in unique_powers):
                if all(unique_powers[i+1] - unique_powers[i] == 1 for i in range(len(unique_powers)-1)):
                    return (HAND_DOUBLE_STRAIGHT, unique_powers[0], n // 2)

    # 飞机/连续三张 (2段及以上，不能含2和王)
    triples = [(r, RANK_POWER[r]) for r, cnt in rank_counts.items() if cnt == 3]
    if len(triples) >= 2:
        triple_powers = sorted([p for _, p in triples])
        if all(triple_powers[i+1] - triple_powers[i] == 1 for i in range(len(triple_powers)-1)):
            if all(p <= RANK_POWER['A'] for p in triple_powers):
                if n == len(triples) * 3:
                    return (HAND_PLAIN, triple_powers[0], len(triples))
                if n == len(triples) * 4:
                    singles = [r for r, cnt in rank_counts.items() if cnt == 1]
                    if len(singles) == len(triples):
                        return (HAND_PLAIN_WING_SINGLE, triple_powers[0], len(triples))
                if n == len(triples) * 5:
                    pairs = [r for r, cnt in rank_counts.items() if cnt == 2]
                    if len(pairs) == len(triples):
                        return (HAND_PLAIN_WING_PAIR, triple_powers[0], len(triples))

    # 四带二
    if n == 6:
        if sorted(rank_counts.values()) == [1, 1, 4]:
            four_rank = [r for r, cnt in rank_counts.items() if cnt == 4][0]
            return (HAND_FOUR_TWO, RANK_POWER[four_rank], 1)

    # 四带两对
    if n == 8:
        if sorted(rank_counts.values()) == [2, 2, 4]:
            four_rank = [r for r, cnt in rank_counts.items() if cnt == 4][0]
            return (HAND_FOUR_TWO_PAIRS, RANK_POWER[four_rank], 1)

    return None


def can_beat(hand1, hand2):
    """
    判断 hand1 是否能打过 hand2。
    """
    if hand2 is None:
        return hand1 is not None
    if hand1 is None:
        return False

    t1, p1, l1 = hand1
    t2, p2, l2 = hand2

    if t1 == HAND_ROCKET:
        return True
    if t2 == HAND_ROCKET:
        return False

    if t1 == HAND_BOMB:
        if t2 == HAND_BOMB:
            return p1 > p2
        return True
    if t2 == HAND_BOMB:
        return False

    if t1 != t2 or l1 != l2:
        return False

    return p1 > p2


def is_valid_play(cards, last_hand_type, is_first=False):
    """判断出的牌是否合法"""
    hand = get_hand_type(cards)
    if hand is None:
        return False
    if is_first or last_hand_type is None:
        return True
    return can_beat(hand, last_hand_type)


class DoudizhuGame:
    def __init__(self):
        self.reset()

    def reset(self):
        self.deck = []
        self.player_cards = [[], [], []]
        self.landlord = -1
        self.current_player = 0
        self.phase = PHASE_DEALING
        self.bids = [-1, -1, -1]
        self.current_bid = 0
        self.bid_turn = 0
        self.last_play = None
        self.last_valid_player = None
        self.consecutive_pass = 0
        self.winner = -1
        self.dizhu_score = 0
        self.bottom_cards = []
        self.messages = []

    def build_deck(self):
        self.deck = []
        for rank in RANKS:
            for suit in SUITS:
                self.deck.append((rank, suit))
        self.deck.append(('小王', None))
        self.deck.append(('大王', None))
        random.shuffle(self.deck)

    def deal(self):
        self.build_deck()
        self.player_cards = [sort_cards(self.deck[i*17:(i+1)*17]) for i in range(3)]
        self.bottom_cards = sort_cards(self.deck[51:54])
        self.phase = PHASE_BIDDING
        self.bid_turn = 0
        self.bids = [-1, -1, -1]
        self.current_bid = 0
        self.add_message("发牌完成，开始叫分")

    def add_message(self, msg):
        self.messages.append(msg)
        if len(self.messages) > 10:
            self.messages.pop(0)

    def bid(self, player, score):
        if self.phase != PHASE_BIDDING:
            return False, -1
        self.bids[player] = score
        if score > self.current_bid:
            self.current_bid = score
        names = ["你", "机器人A", "机器人B"]
        if score == 0:
            self.add_message(f"{names[player]} 不叫")
        else:
            self.add_message(f"{names[player]} 叫 {score} 分")

        self.bid_turn += 1

        if score == 3:
            self.landlord = player
            self._assign_landlord()
            return True, self.landlord

        if self.bid_turn >= 3:
            if self.current_bid > 0:
                winner = self.bids.index(self.current_bid)
                self.landlord = winner
                self._assign_landlord()
                return True, self.landlord
            else:
                self.add_message("无人叫分，重新发牌")
                self.deal()
                return False, -1
        return False, -1

    def _assign_landlord(self):
        names = ["你", "机器人A", "机器人B"]
        self.add_message(f"{names[self.landlord]} 成为地主！")
        self.player_cards[self.landlord].extend(self.bottom_cards)
        self.player_cards[self.landlord] = sort_cards(self.player_cards[self.landlord])
        self.current_player = self.landlord
        self.last_play = None
        self.last_valid_player = None
        self.consecutive_pass = 0
        self.phase = PHASE_PLAYING

    def play(self, player, cards):
        if self.phase != PHASE_PLAYING:
            return False, "不在出牌阶段"
        if player != self.current_player:
            return False, "还没轮到你"
        if not cards:
            return False, "不能出空牌（请使用pass）"

        hand_copy = self.player_cards[player][:]
        for c in cards:
            if c not in hand_copy:
                return False, f"手里没有这张牌: {c}"
            hand_copy.remove(c)

        is_first = (self.last_play is None or self.consecutive_pass >= 2)
        hand = get_hand_type(cards)
        if hand is None:
            return False, "不合法的牌型"

        last_hand = self.last_play[2] if self.last_play and self.consecutive_pass < 2 else None
        if not can_beat(hand, last_hand) and not is_first:
            return False, "打不过上家"

        for c in cards:
            self.player_cards[player].remove(c)
        self.last_play = (player, cards, hand)
        self.last_valid_player = player
        self.consecutive_pass = 0
        self.current_player = (player + 1) % 3

        if len(self.player_cards[player]) == 0:
            self.winner = player
            self.phase = PHASE_ENDED
            return True, "win"

        return True, "ok"

    def pass_turn(self, player):
        if self.phase != PHASE_PLAYING:
            return False, "不在出牌阶段"
        if player != self.current_player:
            return False, "还没轮到你"

        is_first = (self.last_play is None or self.consecutive_pass >= 2)
        if is_first:
            return False, "第一手必须出牌"

        names = ["你", "机器人A", "机器人B"]
        self.add_message(f"{names[player]} 不要")
        self.consecutive_pass += 1
        self.current_player = (player + 1) % 3

        if self.consecutive_pass >= 2:
            self.last_play = None

        return True, "pass"

    def get_legal_plays(self, player, last_hand_type=None, is_first=False):
        if last_hand_type is None:
            last_hand_type = self.last_play[2] if self.last_play and self.consecutive_pass < 2 else None
        if is_first or last_hand_type is None:
            is_first = True

        cards = self.player_cards[player]
        legal = []
        n = len(cards)
        from itertools import combinations

        if is_first:
            sizes = list(range(1, min(n+1, 9)))
        else:
            t2, p2, l2 = last_hand_type
            if t2 in (HAND_SINGLE, HAND_PAIR, HAND_TRIPLE, HAND_TRIPLE_SINGLE,
                      HAND_TRIPLE_PAIR, HAND_BOMB, HAND_FOUR_TWO, HAND_FOUR_TWO_PAIRS, HAND_ROCKET):
                if t2 == HAND_SINGLE:
                    sizes = [1]
                elif t2 == HAND_PAIR:
                    sizes = [2]
                elif t2 == HAND_TRIPLE:
                    sizes = [3]
                elif t2 == HAND_TRIPLE_SINGLE:
                    sizes = [4]
                elif t2 == HAND_TRIPLE_PAIR:
                    sizes = [5]
                elif t2 == HAND_BOMB:
                    sizes = [4]
                elif t2 == HAND_FOUR_TWO:
                    sizes = [6]
                elif t2 == HAND_FOUR_TWO_PAIRS:
                    sizes = [8]
                elif t2 == HAND_ROCKET:
                    sizes = [2]
            elif t2 in (HAND_STRAIGHT,):
                sizes = [l2]
            elif t2 == HAND_DOUBLE_STRAIGHT:
                sizes = [l2 * 2]
            elif t2 in (HAND_PLAIN, HAND_PLAIN_WING_SINGLE, HAND_PLAIN_WING_PAIR):
                if t2 == HAND_PLAIN:
                    sizes = [l2 * 3]
                elif t2 == HAND_PLAIN_WING_SINGLE:
                    sizes = [l2 * 4]
                else:
                    sizes = [l2 * 5]
            else:
                sizes = []

        def check_combo(combo):
            h = get_hand_type(list(combo))
            if h is None:
                return False
            if is_first or last_hand_type is None:
                return True
            return can_beat(h, last_hand_type)

        for size in sizes:
            if size > n:
                continue
            seen = set()
            for combo in combinations(cards, size):
                key = tuple(sorted([card_power(c) for c in combo]))
                if key in seen:
                    continue
                seen.add(key)
                if check_combo(combo):
                    legal.append(list(combo))
                    if len(legal) > 200:
                        break
            if len(legal) > 200:
                break

        return legal
