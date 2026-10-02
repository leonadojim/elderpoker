"""
四副牌升级核心引擎（V1 简化版）
核心流程：发牌 → 叫主 → 扣底 → 出牌 → 结算
"""
import random
from collections import Counter
import sys
sys.path.insert(0, '..')
from common.cards import RANKS, SUITS, SUIT_LIST, JOKERS, sort_cards, is_score_card, format_card_text

# ==================== 阶段定义 ====================
PHASE_DEALING = "dealing"
PHASE_BIDDING = "bidding"      # 叫主/亮主
PHASE_DISCARD = "discard"      # 庄家扣底
PHASE_PLAYING = "playing"
PHASE_ENDED = "ended"

# ==================== 牌型定义 ====================
SJ_SINGLE = "single"
SJ_PAIR = "pair"
SJ_TRIPLE = "triple"
SJ_QUAD = "quad"
SJ_TRACTOR_2 = "tractor_2"     # 两连拖（相邻两对）
SJ_TRACTOR_3 = "tractor_3"     # 三连拖（相邻三对）
SJ_TRACTOR_4 = "tractor_4"     # 四连拖（相邻四对）
SJ_TRIPLE_TRACTOR_2 = "triple_tractor_2"  # 三条两连拖（相邻两三条）
SJ_TRIPLE_TRACTOR_3 = "triple_tractor_3"  # 三条三连拖
SJ_QUAD_TRACTOR_2 = "quad_tractor_2"      # 四条连拖（相邻两四条）


# 升级专用牌力：需要考虑主牌、级别、花色
class ShengjiCardPower:
    def __init__(self, level_rank='3'):
        self.level_rank = level_rank
        self.trump_suit = None  # 主花色

    def set_trump(self, suit):
        self.trump_suit = suit

    def power(self, card):
        """
        返回牌的绝对牌力，越大越强。
        王 > 主级别 > 副级别 > 主A..主2 > 副A..副2
        """
        rank, suit = card
        if rank == '大王':
            return 1000
        if rank == '小王':
            return 999

        is_trump_suit = (suit == self.trump_suit)
        is_level = (rank == self.level_rank)

        # 主级别（主花色的级别牌）
        if is_level and is_trump_suit:
            return 998
        # 副级别（其他花色的级别牌）
        if is_level and not is_trump_suit:
            return 997

        # 主花色的普通牌
        if is_trump_suit:
            base = {'A': 14, 'K': 13, 'Q': 12, 'J': 11, '10': 10, '9': 9,
                    '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2}
            return 500 + base.get(rank, 0)

        # 副花色的普通牌
        base = {'A': 14, 'K': 13, 'Q': 12, 'J': 11, '10': 10, '9': 9,
                '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2}
        # 按花色给基础分，确保同rank不同花色也有大小（黑桃>红桃>方块>梅花）
        suit_order = {'spade': 30, 'heart': 20, 'diamond': 10, 'club': 0}
        return 100 + base.get(rank, 0) * 4 + suit_order.get(suit, 0)

    def is_trump(self, card):
        """判断是否为主牌"""
        rank, suit = card
        if rank in JOKERS:
            return True
        if rank == self.level_rank:
            return True
        if suit == self.trump_suit:
            return True
        return False

    def is_same_suit_for_follow(self, card, lead_suit):
        """
        判断card是否属于跟牌要求的花色。
        lead_suit 为首家出的花色（可能为None表示全主牌）。
        """
        if lead_suit is None:
            return self.is_trump(card)
        rank, suit = card
        # 首家出副牌，其他家有此花色的副牌必须跟
        if rank == self.level_rank:
            return False  # 级别牌不算普通花色
        if rank in JOKERS:
            return False
        return suit == lead_suit


def get_shengji_hand_type(cards, power_eval: ShengjiCardPower):
    """
    判断升级牌型。
    返回 (hand_type, primary_power, length, is_trump) 或 None
    - is_trump: 是否全为主牌（用于比较）
    """
    if not cards:
        return None
    n = len(cards)

    # 所有牌必须同花色类别（全主或全同一副牌花色）
    suits = set()
    trump_count = 0
    for c in cards:
        if power_eval.is_trump(c):
            trump_count += 1
        else:
            suits.add(c[1])

    is_trump_hand = (trump_count == n)
    if not is_trump_hand:
        if len(suits) != 1:
            return None  # 混花色非法

    # 按点数分组
    ranks = [c[0] for c in cards]
    rank_counts = Counter(ranks)

    # 获取该手牌的"有效点数"（用于拖拉机判断）
    # 对于主牌，需要把主级别当作特殊点处理
    def effective_rank_key(card):
        r, s = card
        if r in JOKERS:
            return (99, r)
        if r == power_eval.level_rank:
            if s == power_eval.trump_suit:
                return (98, r)  # 主级别最高
            else:
                return (97, r)  # 副级别次之
        # 普通牌按rank排序
        order = {'A': 14, 'K': 13, 'Q': 12, 'J': 11, '10': 10, '9': 9, '8': 8,
                 '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2}
        return (order.get(r, 0), r)

    # 单张
    if n == 1:
        return (SJ_SINGLE, power_eval.power(cards[0]), 1, is_trump_hand)

    # 对子
    if n == 2 and len(rank_counts) == 1:
        return (SJ_PAIR, power_eval.power(cards[0]), 1, is_trump_hand)

    # 三条
    if n == 3 and len(rank_counts) == 1:
        return (SJ_TRIPLE, power_eval.power(cards[0]), 1, is_trump_hand)

    # 四条
    if n == 4 and len(rank_counts) == 1:
        return (SJ_QUAD, power_eval.power(cards[0]), 1, is_trump_hand)

    # 拖拉机判断（相邻同数量组）
    # 按effective_rank_key排序，然后检查相邻rank是否有连续的数量相同的组
    sorted_cards = sorted(cards, key=effective_rank_key)

    # 分组：按rank分组，保持排序
    groups = []
    current_rank = None
    current_group = []
    for c in sorted_cards:
        if c[0] != current_rank:
            if current_group:
                groups.append(current_group)
            current_rank = c[0]
            current_group = [c]
        else:
            current_group.append(c)
    if current_group:
        groups.append(current_group)

    if len(groups) >= 2:
        group_sizes = [len(g) for g in groups]
        # 所有组大小相同
        if len(set(group_sizes)) == 1:
            size = group_sizes[0]
            # 检查rank是否连续（用effective_rank_key的数值部分）
            keys = [effective_rank_key(g[0])[0] for g in groups]
            if all(keys[i+1] - keys[i] == 1 for i in range(len(keys)-1)):
                if size == 2:
                    if len(groups) == 2:
                        return (SJ_TRACTOR_2, keys[0], 2, is_trump_hand)
                    if len(groups) == 3:
                        return (SJ_TRACTOR_3, keys[0], 3, is_trump_hand)
                    if len(groups) == 4:
                        return (SJ_TRACTOR_4, keys[0], 4, is_trump_hand)
                if size == 3:
                    if len(groups) == 2:
                        return (SJ_TRIPLE_TRACTOR_2, keys[0], 2, is_trump_hand)
                    if len(groups) == 3:
                        return (SJ_TRIPLE_TRACTOR_3, keys[0], 3, is_trump_hand)
                if size == 4 and len(groups) == 2:
                    return (SJ_QUAD_TRACTOR_2, keys[0], 2, is_trump_hand)

    # 混合牌型：n张同花色（或全主牌），不构成上述标准牌型（用于跟牌垫牌）
    if n > 1:
        return ("mixed", 0, n, is_trump_hand)

    return None


def can_beat_shengji(hand1, hand2):
    """
    判断hand1是否能打过hand2。
    hand1, hand2 都是 get_shengji_hand_type 返回的元组。
    """
    if hand2 is None:
        return hand1 is not None
    if hand1 is None:
        return False

    t1, p1, l1, trump1 = hand1
    t2, p2, l2, trump2 = hand2

    # mixed牌型打不过标准牌型，标准牌型总能打败mixed
    if t1 == "mixed" and t2 != "mixed":
        return False
    if t2 == "mixed" and t1 != "mixed":
        return True

    # 类型和长度必须相同
    if t1 != t2 or l1 != l2:
        return False

    # 主牌 > 副牌
    if trump1 and not trump2:
        return True
    if trump2 and not trump1:
        return False

    # 同为 trump 或同为非trump，比primary_power
    return p1 > p2


class ShengjiGame:
    def __init__(self):
        self.reset()

    def reset(self):
        self.deck = []
        self.player_cards = [[], [], [], []]
        self.bottom_cards = []
        self.level = '3'           # 当前打的级别
        self.trump_suit = None     # 主花色
        self.dealer = -1           # 庄家
        self.current_player = 0
        self.phase = PHASE_DEALING
        self.power_eval = ShengjiCardPower(self.level)
        self.last_play = None      # (player, cards, hand_type)
        self.consecutive_pass = 0
        self.current_trick = []    # 当前轮出的牌 [(player, cards), ...]
        self.current_passes = []   # 本轮pass的玩家
        self.trick_complete = False  # 本轮是否已出满，等待结算
        self.trick_scores = []     # 每轮的得分记录
        self.scores = [0, 0]       # [庄家方得分, 抓分方得分]（仅计分牌）
        self.winner_team = -1      # 0=庄家方赢, 1=抓分方赢
        self.messages = []
        self.bid_history = []      # 叫主记录
        self.koudi_multiplier = 1  # 抠底倍数（最后一轮主牌扣底）

    def build_deck(self):
        """4副牌"""
        self.deck = []
        for _ in range(4):
            for rank in RANKS:
                for suit in SUITS:
                    self.deck.append((rank, suit))
            self.deck.append(('小王', None))
            self.deck.append(('大王', None))
        random.shuffle(self.deck)

    def deal(self):
        self.build_deck()
        for i in range(4):
            self.player_cards[i] = sort_cards(self.deck[i*52:(i+1)*52])
        self.bottom_cards = sort_cards(self.deck[208:216])
        self.phase = PHASE_BIDDING
        self.current_player = 0
        self.add_message(f"发牌完成，当前打 {self.level}")
        self.add_message("请亮主确定主花色")

    def add_message(self, msg):
        self.messages.append(msg)
        if len(self.messages) > 15:
            self.messages.pop(0)

    def get_bid_level(self, cards):
        """
        判断一组牌能否用于叫主，以及叫主级别。
        简化规则：只能亮当前级别（如3）的牌。
        返回 (can_bid, level_num)
        level_num: 1=单张, 2=对子, 3=三张/对王, 4=四张/三张王, 5=四张王
        """
        if not cards:
            return False, 0

        ranks = [c[0] for c in cards]
        rank_counts = Counter(ranks)

        # 检查是否全是当前级别或王
        for r in ranks:
            if r != self.level and r not in JOKERS:
                return False, 0

        n = len(cards)
        joker_count = sum(1 for r in ranks if r in JOKERS)
        level_count = n - joker_count

        # 王可替代级别牌
        # 简化：单张级别=1, 对子级别=2, 对王=3, 三张级别=3, 三张王=4, 四张级别=4, 四张王=5
        if n == 1:
            if level_count == 1:
                return True, 1
        elif n == 2:
            if level_count == 2:
                return True, 2
            if joker_count == 2:
                return True, 3
        elif n == 3:
            if level_count == 3:
                return True, 3
            if joker_count == 3:
                return True, 4
        elif n == 4:
            if level_count == 4:
                return True, 4
            if joker_count == 4:
                return True, 5

        return False, 0

    def bid(self, player, cards):
        """
        玩家叫主/亮主。
        cards: 用于亮主的牌（从手牌中选出）
        返回 (success, msg)
        """
        if self.phase != PHASE_BIDDING:
            return False, "不在叫主阶段"

        # 从手牌中移除这些牌检查
        hand_copy = self.player_cards[player][:]
        for c in cards:
            if c not in hand_copy:
                return False, f"手里没有 {format_card_text(c)}"
            hand_copy.remove(c)

        can, level = self.get_bid_level(cards)
        if not can:
            return False, "不能用于亮主"

        # 确定花色（从级别牌中取花色）
        level_cards = [c for c in cards if c[0] == self.level]
        if level_cards:
            suit = level_cards[0][1]
        else:
            # 全王亮主 = 无主
            suit = None

        # 检查是否比当前已亮的主级别高
        current_best = 0
        if self.bid_history:
            current_best = max(b[2] for b in self.bid_history)

        if level <= current_best:
            return False, "亮主级别不够高"

        # 执行亮主
        for c in cards:
            self.player_cards[player].remove(c)

        self.bid_history.append((player, suit, level))
        self.trump_suit = suit
        self.power_eval.set_trump(suit)
        self.dealer = player

        suit_name = {None: "无主", 'spade': '黑桃', 'heart': '红桃', 'diamond': '方块', 'club': '梅花'}
        level_desc = {1: '单张', 2: '对子', 3: '对王/三张', 4: '三张王/四张', 5: '四张王'}
        self.add_message(f"玩家{player} 亮{suit_name[suit]} {level_desc[level]}")

        # 简化：任意亮主即结束叫主阶段
        self._finish_bidding()
        return True, "ok"

    def auto_bid_from_bottom(self):
        """无人亮主时，翻底牌第一张确定主花色"""
        if not self.bottom_cards:
            return
        first = self.bottom_cards[0]
        rank, suit = first
        if rank in JOKERS:
            self.trump_suit = None
            self.add_message("底牌第一张为王，无主")
        else:
            self.trump_suit = suit
            suit_name = {'spade': '黑桃', 'heart': '红桃', 'diamond': '方块', 'club': '梅花'}
            self.add_message(f"底牌第一张为{suit_name[suit]}，主花色为{suit_name[suit]}")
        self.power_eval.set_trump(self.trump_suit)
        # 第一局随机庄家
        self.dealer = 0
        self._finish_bidding()

    def _finish_bidding(self):
        """叫主结束，庄家拿底牌，进入扣底阶段"""
        if self.dealer < 0:
            self.dealer = 0
        # 庄家拿底牌
        self.player_cards[self.dealer].extend(self.bottom_cards)
        self.player_cards[self.dealer] = sort_cards(self.player_cards[self.dealer])
        self.bottom_cards = []
        self.current_player = self.dealer
        self.phase = PHASE_DISCARD
        self.add_message(f"庄家{self.dealer}拿底牌，请扣底")

    def discard_bottom(self, player, cards):
        """庄家扣底"""
        if self.phase != PHASE_DISCARD:
            return False, "不在扣底阶段"
        if player != self.dealer:
            return False, "只有庄家能扣底"
        if len(cards) != 8:
            return False, "必须扣8张底牌"

        hand_copy = self.player_cards[player][:]
        for c in cards:
            if c not in hand_copy:
                return False, f"手里没有 {format_card_text(c)}"
            hand_copy.remove(c)

        for c in cards:
            self.player_cards[player].remove(c)
        self.bottom_cards = cards[:]
        self.phase = PHASE_PLAYING
        self.current_trick = []
        self.add_message("扣底完成，开始出牌")
        return True, "ok"

    def play(self, player, cards):
        """出牌"""
        if self.phase != PHASE_PLAYING:
            return False, "不在出牌阶段"
        if player != self.current_player:
            return False, "还没轮到你"
        if not cards:
            return False, "不能出空牌"

        # 检查牌是否在手中
        hand_copy = self.player_cards[player][:]
        for c in cards:
            if c not in hand_copy:
                return False, f"手里没有这张牌"
            hand_copy.remove(c)

        # 判断牌型
        hand = get_shengji_hand_type(cards, self.power_eval)
        if hand is None:
            return False, "不合法的牌型"

        # 第一手或新一轮
        is_first = (len(self.current_trick) == 0)

        if not is_first:
            # 检查跟牌规则
            first_player, first_cards, first_hand = self.current_trick[0]
            first_type, first_power, first_len, first_trump = first_hand

            # 必须出相同张数
            if len(cards) != len(first_cards):
                return False, f"必须出{len(first_cards)}张牌"

            # 获取首家出的"花色"
            lead_suit = self._get_lead_suit(first_cards)

            # 检查是否尽力跟牌了
            if not self._check_follow_rule(player, cards, first_cards, lead_suit):
                return False, "没有按规则跟牌"

            # 可以毙牌：用主牌出相同牌型
            # V1简化：允许垫牌（同张数、尽量跟花色即可，不强制同牌型或打得过）
            # _check_follow_rule 已确保尽力跟牌，此处不再额外限制主副牌转换

        # 执行出牌
        for c in cards:
            self.player_cards[player].remove(c)
        self.current_trick.append((player, cards, hand))

        # 下一位玩家：跳过已经出完牌的
        next_p = (player + 1) % 4
        for _ in range(4):
            if len(self.player_cards[next_p]) > 0:
                break
            next_p = (next_p + 1) % 4
        self.current_player = next_p

        # 检查一轮是否结束（如果剩下的人都出完了也结束）
        active_in_trick = [p for p, _, _ in self.current_trick]
        remaining_active = [p for p in range(4) if len(self.player_cards[p]) > 0 and p not in active_in_trick]
        if len(self.current_trick) == 4 or not remaining_active:
            self.trick_complete = True

        return True, "ok"

    def _get_lead_suit(self, cards):
        """确定首家出的花色（用于跟牌判断）"""
        # 找第一个非主牌的suit
        for c in cards:
            if not self.power_eval.is_trump(c):
                return c[1]
        return None  # 全主牌

    def _check_follow_rule(self, player, played_cards, first_cards, lead_suit):
        """
        检查跟牌是否符合规则（V1简化版）。
        简化规则：有同花色必须跟同花色（尽量），否则可垫牌。
        """
        hand = self.player_cards[player] + played_cards  # 还原出手前的手牌

        # 统计手牌中lead_suit的牌（非主牌的该花色牌）
        lead_suit_cards = [c for c in hand if not self.power_eval.is_trump(c) and c[1] == lead_suit]

        if lead_suit and lead_suit_cards:
            # 有该花色的牌，必须尽量跟
            played_lead_suit = [c for c in played_cards if not self.power_eval.is_trump(c) and c[1] == lead_suit]
            # 简化：只要出了至少一张该花色，就算尽力（V1简化，避免复杂验证）
            if len(played_lead_suit) == 0 and len(played_cards) == len(first_cards):
                # 一张都没跟，但有该花色，不允许
                return False

        return True

    def _finish_trick(self):
        """一轮结束，判断赢家，计分"""
        first_player, first_cards, first_hand = self.current_trick[0]
        lead_suit = self._get_lead_suit(first_cards)

        winner = 0
        win_hand = first_hand
        for i, (p, cards, hand) in enumerate(self.current_trick[1:], 1):
            # 比较大小
            if can_beat_shengji(hand, win_hand):
                winner = i
                win_hand = hand

        win_player, win_cards, _ = self.current_trick[winner]

        # 计算该轮分牌
        trick_score = 0
        for p, cards, _ in self.current_trick:
            for c in cards:
                trick_score += is_score_card(c)

        # 确定赢家的队伍
        win_team = 0 if win_player in (self.dealer, (self.dealer + 2) % 4) else 1
        self.scores[win_team] += trick_score

        self.add_message(f"玩家{win_player} 赢本轮，得{trick_score}分")

        # 检查是否是最后一轮
        total_left = sum(len(c) for c in self.player_cards)
        if total_left == 0:
            self._finish_game(win_player, win_team)
        else:
            self.current_trick = []
            self.current_passes = []
            self.consecutive_pass = 0
            # 下一轮的出牌者：赢家优先，但如果赢家已经没牌，找下一个有牌的玩家
            next_p = win_player
            for _ in range(4):
                if len(self.player_cards[next_p]) > 0:
                    break
                next_p = (next_p + 1) % 4
            self.current_player = next_p

    def _finish_game(self, last_winner, last_winner_team):
        """本局结束，结算"""
        self.current_trick = []   # 清空最后一轮的牌
        self.current_passes = []
        self.phase = PHASE_ENDED

        # 抠底：最后一轮赢家用主牌扣底，底牌分数翻倍
        koudi_score = 0
        for c in self.bottom_cards:
            koudi_score += is_score_card(c)

        # 简化：最后一轮赢家队伍获得底牌分数
        self.scores[last_winner_team] += koudi_score
        if koudi_score > 0:
            self.add_message(f"抠底！底牌{koudi_score}分给{'庄家方' if last_winner_team == 0 else '抓分方'}")

        # 判断胜负
        score_fang = self.scores[1]
        if score_fang >= 160:
            self.winner_team = 1
            levels_up = max(1, (score_fang - 80) // 80)
            self.add_message(f"抓分方得{score_fang}分，上台！升{levels_up}级")
        else:
            self.winner_team = 0
            self.add_message(f"抓分方得{score_fang}分，庄家方守庄成功")

    def pass_turn(self, player):
        """不要"""
        if self.phase != PHASE_PLAYING:
            return False, "不在出牌阶段"
        if player != self.current_player:
            return False, "还没轮到你"
        if len(self.current_trick) == 0:
            return False, "第一手必须出牌"

        self.add_message(f"玩家{player} 不要")
        self.current_passes.append(player)
        self.consecutive_pass += 1
        self.current_player = (player + 1) % 4

        # 如果其他三家都不要（不太可能，因为4人轮流出牌）
        # 实际上升级没有pass的概念，所有人必须出牌
        # 这里只是为了兼容AI偶尔无法出牌的情况
        if self.consecutive_pass >= 3:
            self._finish_trick()

        return True, "pass"

    def get_legal_plays(self, player, trick_so_far=None):
        """
        获取所有合法出牌（用于AI和提示）。
        trick_so_far: 当前轮已出的牌 [(player, cards, hand), ...]
        """
        if trick_so_far is None:
            trick_so_far = self.current_trick

        cards = self.player_cards[player]
        is_first = (len(trick_so_far) == 0)

        if is_first:
            # 自由出牌
            return self._get_all_hand_types(cards)

        # 跟牌
        first_player, first_cards, first_hand = trick_so_far[0]
        lead_suit = self._get_lead_suit(first_cards)
        first_type, first_power, first_len, first_trump = first_hand
        n = len(first_cards)

        legal = []

        # 1. 尝试同花色同牌型且能大过（正跟）
        same_suit_cards = [c for c in cards if not self.power_eval.is_trump(c) and c[1] == lead_suit]
        if lead_suit and same_suit_cards:
            combos = self._find_combinations(same_suit_cards, n, first_type)
            for combo in combos:
                h = get_shengji_hand_type(combo, self.power_eval)
                if h and can_beat_shengji(h, first_hand):
                    legal.append(combo)

        # 2. 尝试主牌毙（同牌型且更大）
        trump_cards = [c for c in cards if self.power_eval.is_trump(c)]
        combos = self._find_combinations(trump_cards, n, first_type)
        for combo in combos:
            h = get_shengji_hand_type(combo, self.power_eval)
            if h and can_beat_shengji(h, first_hand):
                legal.append(combo)

        # 3. 垫牌：任意n张（V1简化，垫牌总是允许，不比较大小）
        if not legal:
            from itertools import combinations
            # 优先从同花色选，必须全部使用该花色的牌（如果够的话）
            if same_suit_cards:
                if len(same_suit_cards) >= n:
                    for combo in combinations(same_suit_cards, n):
                        legal.append(list(combo))
                        if len(legal) > 50:
                            break
                else:
                    # 同花色不够，全部出同花色，再补其他最小的牌
                    remaining = [c for c in cards if c not in same_suit_cards]
                    remaining.sort(key=lambda c: self.power_eval.power(c))
                    need = n - len(same_suit_cards)
                    legal.append(same_suit_cards + remaining[:need])
            else:
                # 没有同花色，出最小的n张
                sorted_hand = sorted(cards, key=lambda c: self.power_eval.power(c))
                legal.append(sorted_hand[:n])

        # 最终验证：确保所有选项都通过跟牌规则
        validated = []
        for combo in legal:
            if self._check_follow_rule(player, combo, first_cards, lead_suit):
                validated.append(combo)
        
        # 如果验证后全空，强制构造一个合规垫牌
        if not validated:
            if same_suit_cards:
                need = min(n, len(same_suit_cards))
                pad = same_suit_cards[:need]
                if len(pad) < n:
                    rest = [c for c in cards if c not in same_suit_cards]
                    rest.sort(key=lambda c: self.power_eval.power(c))
                    pad = pad + rest[:n - len(pad)]
                validated.append(pad)
            else:
                sorted_hand = sorted(cards, key=lambda c: self.power_eval.power(c))
                validated.append(sorted_hand[:n])

        return validated

    def _get_all_hand_types(self, cards):
        """获取手牌中所有可能的出牌组合"""
        result = []
        n = len(cards)

        # 单张
        for c in cards:
            result.append([c])

        # 对子、三条、四条
        from itertools import combinations
        rank_groups = {}
        for c in cards:
            key = (c[0], c[1] if c[1] else 'joker')
            rank_groups.setdefault(key, []).append(c)

        for group in rank_groups.values():
            for size in [2, 3, 4]:
                if len(group) >= size:
                    result.append(group[:size])

        # 拖拉机（简化：只找相邻的对子/三条/四条）
        # 按花色分组，每组内部找拖拉机
        suit_groups = {}
        for c in cards:
            s = c[1] if c[1] else 'trump'
            suit_groups.setdefault(s, []).append(c)

        for suit, group in suit_groups.items():
            sorted_group = sorted(group, key=lambda c: self.power_eval.power(c))
            # 按rank分组
            rgroups = []
            current_rank = None
            cg = []
            for c in sorted_group:
                if c[0] != current_rank:
                    if cg:
                        rgroups.append(cg)
                    current_rank = c[0]
                    cg = [c]
                else:
                    cg.append(c)
            if cg:
                rgroups.append(cg)

            # 找连续对子（拖拉机），用get_shengji_hand_type验证确保合法
            for i in range(len(rgroups) - 1):
                if len(rgroups[i]) >= 2 and len(rgroups[i+1]) >= 2:
                    candidate = rgroups[i][:2] + rgroups[i+1][:2]
                    h = get_shengji_hand_type(candidate, self.power_eval)
                    if h and 'tractor' in h[0]:
                        result.append(candidate)
                # 三连拖
                if i < len(rgroups) - 2:
                    if len(rgroups[i]) >= 2 and len(rgroups[i+1]) >= 2 and len(rgroups[i+2]) >= 2:
                        candidate = rgroups[i][:2] + rgroups[i+1][:2] + rgroups[i+2][:2]
                        h = get_shengji_hand_type(candidate, self.power_eval)
                        if h and 'tractor' in h[0]:
                            result.append(candidate)
                # 三条连拖
                if len(rgroups[i]) >= 3 and len(rgroups[i+1]) >= 3:
                    candidate = rgroups[i][:3] + rgroups[i+1][:3]
                    h = get_shengji_hand_type(candidate, self.power_eval)
                    if h and 'tractor' in h[0]:
                        result.append(candidate)
                # 四条连拖
                if len(rgroups[i]) >= 4 and len(rgroups[i+1]) >= 4:
                    candidate = rgroups[i][:4] + rgroups[i+1][:4]
                    h = get_shengji_hand_type(candidate, self.power_eval)
                    if h and 'tractor' in h[0]:
                        result.append(candidate)

        return result

    def _find_combinations(self, cards, n, hand_type):
        """从cards中找到n张、符合hand_type的组合（优化版，避免全排列）"""
        from itertools import combinations
        result = []

        if hand_type == SJ_SINGLE:
            return [[c] for c in cards]

        # 按 rank 分组
        rank_groups = {}
        for c in cards:
            rank_groups.setdefault(c[0], []).append(c)

        if hand_type == SJ_PAIR:
            for group in rank_groups.values():
                if len(group) >= 2:
                    for combo in combinations(group, 2):
                        result.append(list(combo))
            return result

        if hand_type == SJ_TRIPLE:
            for group in rank_groups.values():
                if len(group) >= 3:
                    for combo in combinations(group, 3):
                        result.append(list(combo))
            return result

        if hand_type == SJ_QUAD:
            for group in rank_groups.values():
                if len(group) >= 4:
                    for combo in combinations(group, 4):
                        result.append(list(combo))
            return result

        # 拖拉机需要连续 rank
        def eff_key(card):
            r, s = card
            if r in JOKERS:
                return (99, r)
            if r == self.power_eval.level_rank:
                if s == self.power_eval.trump_suit:
                    return (98, r)
                else:
                    return (97, r)
            order = {'A': 14, 'K': 13, 'Q': 12, 'J': 11, '10': 10, '9': 9, '8': 8,
                     '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2}
            return (order.get(r, 0), r)

        sorted_items = sorted(rank_groups.items(), key=lambda x: eff_key(x[1][0]))

        if hand_type == SJ_TRACTOR_2:
            for i in range(len(sorted_items) - 1):
                r1, g1 = sorted_items[i]
                r2, g2 = sorted_items[i + 1]
                k1, k2 = eff_key(g1[0])[0], eff_key(g2[0])[0]
                if k2 - k1 == 1 and len(g1) >= 2 and len(g2) >= 2:
                    for c1 in combinations(g1, 2):
                        for c2 in combinations(g2, 2):
                            result.append(list(c1) + list(c2))
            return result

        if hand_type == SJ_TRACTOR_3:
            for i in range(len(sorted_items) - 2):
                g1, g2, g3 = sorted_items[i][1], sorted_items[i+1][1], sorted_items[i+2][1]
                k1, k2, k3 = eff_key(g1[0])[0], eff_key(g2[0])[0], eff_key(g3[0])[0]
                if k2 - k1 == 1 and k3 - k2 == 1 and len(g1) >= 2 and len(g2) >= 2 and len(g3) >= 2:
                    for c1 in combinations(g1, 2):
                        for c2 in combinations(g2, 2):
                            for c3 in combinations(g3, 2):
                                result.append(list(c1) + list(c2) + list(c3))
            return result

        if hand_type == SJ_TRACTOR_4:
            for i in range(len(sorted_items) - 3):
                g1, g2, g3, g4 = (sorted_items[i][1], sorted_items[i+1][1],
                                  sorted_items[i+2][1], sorted_items[i+3][1])
                k1, k2, k3, k4 = (eff_key(g1[0])[0], eff_key(g2[0])[0],
                                  eff_key(g3[0])[0], eff_key(g4[0])[0])
                if (k2 - k1 == 1 and k3 - k2 == 1 and k4 - k3 == 1 and
                        len(g1) >= 2 and len(g2) >= 2 and len(g3) >= 2 and len(g4) >= 2):
                    for c1 in combinations(g1, 2):
                        for c2 in combinations(g2, 2):
                            for c3 in combinations(g3, 2):
                                for c4 in combinations(g4, 2):
                                    result.append(list(c1) + list(c2) + list(c3) + list(c4))
            return result

        if hand_type == SJ_TRIPLE_TRACTOR_2:
            for i in range(len(sorted_items) - 1):
                g1, g2 = sorted_items[i][1], sorted_items[i+1][1]
                k1, k2 = eff_key(g1[0])[0], eff_key(g2[0])[0]
                if k2 - k1 == 1 and len(g1) >= 3 and len(g2) >= 3:
                    for c1 in combinations(g1, 3):
                        for c2 in combinations(g2, 3):
                            result.append(list(c1) + list(c2))
            return result

        if hand_type == SJ_TRIPLE_TRACTOR_3:
            for i in range(len(sorted_items) - 2):
                g1, g2, g3 = sorted_items[i][1], sorted_items[i+1][1], sorted_items[i+2][1]
                k1, k2, k3 = eff_key(g1[0])[0], eff_key(g2[0])[0], eff_key(g3[0])[0]
                if k2 - k1 == 1 and k3 - k2 == 1 and len(g1) >= 3 and len(g2) >= 3 and len(g3) >= 3:
                    for c1 in combinations(g1, 3):
                        for c2 in combinations(g2, 3):
                            for c3 in combinations(g3, 3):
                                result.append(list(c1) + list(c2) + list(c3))
            return result

        if hand_type == SJ_QUAD_TRACTOR_2:
            for i in range(len(sorted_items) - 1):
                g1, g2 = sorted_items[i][1], sorted_items[i+1][1]
                k1, k2 = eff_key(g1[0])[0], eff_key(g2[0])[0]
                if k2 - k1 == 1 and len(g1) >= 4 and len(g2) >= 4:
                    for c1 in combinations(g1, 4):
                        for c2 in combinations(g2, 4):
                            result.append(list(c1) + list(c2))
            return result

        return result
