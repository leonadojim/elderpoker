"""
四副牌升级游戏主程序。
"""
import pygame
import sys
import random
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.constants import *
from common.audio import speak, set_voice_enabled, is_voice_enabled
from common.renderer_base import draw_table, draw_button, get_font
from common.platform_compat import setup_display, present, map_pos
from common.utils import pick_nicknames
from shengji.engine import ShengjiGame, PHASE_BIDDING, PHASE_DISCARD, PHASE_PLAYING, PHASE_ENDED, get_shengji_hand_type
from shengji.ai import ShengjiAI
from shengji.renderer import (
    draw_player_bottom, draw_player_left, draw_player_right, draw_player_top,
    draw_play_area_shengji, draw_info_panel_shengji, draw_messages_shengji,
    draw_bottom_cards, draw_bottom_cards_mini, draw_captured_cards
)
from shengji.player import HumanPlayerShengji


class ShengjiApp:
    def __init__(self, screen, clock):
        self.screen = screen
        self.clock = clock
        self.game = ShengjiGame()
        self.human = HumanPlayerShengji()
        self.ais = [ShengjiAI(i) for i in range(1, 4)]
        self.click_areas = []  # [(x, y, w, h, orig_idx), ...]
        self.next_ai_time = 0
        self.running = True
        self.status_text = ""
        self.status_timer = 0
        self.pass_display = None
        self.player_names = ["你", "左家", "对家", "右家"]
        self.back_to_menu = False
        self.bid_auto_timer = 0  # 自动翻底牌计时
        self.human_deadline = None  # 人类出牌倒计时截止时刻（get_ticks），None表示未启用

    def set_status(self, text):
        self.status_text = text
        self.status_timer = 120

    def run(self):
        self.back_to_menu = False
        self.game.deal()
        self._pick_nicknames()
        self.bid_auto_timer = pygame.time.get_ticks() + 15000  # 15秒后自动翻底牌
        speak("四副牌升级，请亮主")

        while self.running and not self.back_to_menu:
            dt = self.clock.tick(FPS)
            self.handle_events()
            self.update(dt)
            self.draw()
        return self.back_to_menu

    def _pick_nicknames(self):
        picks = pick_nicknames(3)
        self.player_names = ["你"] + picks

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.handle_click(map_pos(event.pos))
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.do_hint()
                elif event.key == pygame.K_RETURN:
                    self.do_play()
                elif event.key == pygame.K_ESCAPE:
                    self.do_pass()

    def handle_click(self, pos):
        mx, my = pos

        # 语音开关（始终显示）
        if "voice" in self.action_buttons and self.action_buttons["voice"].collidepoint(mx, my):
            set_voice_enabled(not is_voice_enabled())
            return

        # 返回大厅
        if "menu" in self.action_buttons and self.action_buttons["menu"].collidepoint(mx, my):
            self.back_to_menu = True
            return

        # 叫主阶段
        if self.game.phase == PHASE_BIDDING and self.game.current_player == 0:
            if "bid" in self.action_buttons and self.action_buttons["bid"].collidepoint(mx, my):
                self.do_bid()
                return
            if "pass_bid" in self.action_buttons and self.action_buttons["pass_bid"].collidepoint(mx, my):
                self.do_pass_bid()
                return
            # 点击手牌选牌
            if self.click_areas:
                clicked = self.human.handle_click(pos, self.click_areas)
                if clicked:
                    return
            return

        # 扣底阶段
        if self.game.phase == PHASE_DISCARD and self.game.dealer == 0:
            if "discard" in self.action_buttons and self.action_buttons["discard"].collidepoint(mx, my):
                self.do_discard()
                return
            if self.click_areas:
                clicked = self.human.handle_click(pos, self.click_areas)
                if clicked:
                    return
            return

        # 出牌阶段
        if self.game.phase == PHASE_PLAYING and self.game.current_player == 0:
            if "play" in self.action_buttons and self.action_buttons["play"].collidepoint(mx, my):
                self.do_play()
                return
            if "pass" in self.action_buttons and self.action_buttons["pass"].collidepoint(mx, my):
                self.do_pass()
                return
            if "hint" in self.action_buttons and self.action_buttons["hint"].collidepoint(mx, my):
                self.do_hint()
                return
            if "sort" in self.action_buttons and self.action_buttons["sort"].collidepoint(mx, my):
                self.do_sort()
                return
            if self.click_areas:
                clicked = self.human.handle_click(pos, self.click_areas)
                if clicked:
                    return
            return

        # 结束阶段
        if self.game.phase == PHASE_ENDED:
            if "restart" in self.action_buttons and self.action_buttons["restart"].collidepoint(mx, my):
                self.restart()
                return

    def do_bid(self):
        cards = self.human.get_selected_cards(self.game.player_cards[0])
        if not cards:
            self.set_status("请先选择要亮的牌！")
            return
        success, msg = self.game.bid(0, cards)
        if success:
            suit_name = {None: "无主", 'spade': '黑桃', 'heart': '红桃', 'diamond': '方块', 'club': '梅花'}
            speak(f"亮主{suit_name.get(self.game.trump_suit, '')}")
            self.human.clear_selection()
            self.next_ai_time = pygame.time.get_ticks() + 5000
        else:
            if "不能用于亮主" in msg or "级别" in msg:
                tip = f"亮主需要当前打 {self.game.level} 的牌或王（对子、三张更大），请重新选择"
            else:
                tip = msg
            self.set_status(tip)
            speak(tip)
            # 重置自动定主倒计时，给足重新操作的时间
            self.bid_auto_timer = pygame.time.get_ticks() + 15000

    def do_pass_bid(self):
        # 玩家不亮主，交给AI
        self.game.current_player = 1
        self.next_ai_time = pygame.time.get_ticks() + 1500

    def do_discard(self):
        cards = self.human.get_selected_cards(self.game.player_cards[0])
        if len(cards) != 8:
            self.set_status(f"必须选择8张牌扣底，当前选了{len(cards)}张")
            return
        success, msg = self.game.discard_bottom(0, cards)
        if success:
            speak("扣底完成")
            self.human.clear_selection()
            self.next_ai_time = pygame.time.get_ticks() + 5000
        else:
            self.set_status(msg)

    def do_play(self):
        cards = self.human.get_selected_cards(self.game.player_cards[0])
        if not cards:
            self.set_status("请先选牌！")
            return
        success, msg = self.game.play(0, cards)
        if success:
            hand = get_shengji_hand_type(cards, self.game.power_eval)
            self._speak_play(hand, cards)
            self.human.clear_selection()
            self.human_deadline = None
            # 出满一轮时留 2.5 秒展示，再结算清桌
            delay = 2500 if self.game.trick_complete else 5000
            self.next_ai_time = pygame.time.get_ticks() + delay
        else:
            self.set_status(msg)

    def _speak_play(self, hand, cards):
        from common.cards import format_card_text
        if not hand:
            speak("出牌")
            return
        ht = hand[0]
        type_names = {
            "single": "", "pair": "对子", "triple": "三条", "quad": "四条",
            "tractor_2": "拖拉机", "tractor_3": "三连拖", "tractor_4": "四连拖",
            "triple_tractor_2": "三连拖", "triple_tractor_3": "三三连拖",
            "quad_tractor_2": "四条连拖",
        }
        tn = type_names.get(ht, "")
        if tn:
            speak(tn)
        else:
            speak(format_card_text(cards[0]))

    def auto_play_human(self):
        """出牌倒计时超时：自动打出提示牌，失败则用AI兜底"""
        speak("时间到，自动出牌")
        ok, indices = self.human.find_hint(self.game)
        if ok:
            self.human.select_cards(indices)
            self.do_play()
        self.human.clear_selection()
        # 检查是否真的轮到下一家了（do_play可能校验失败）
        if self.game.phase == PHASE_PLAYING and self.game.current_player == 0:
            action, cards = ShengjiAI(0).decide_play(self.game)
            if action == "play" and cards:
                success, msg = self.game.play(0, cards)
                if success:
                    hand = get_shengji_hand_type(cards, self.game.power_eval)
                    self._speak_play(hand, cards)
                else:
                    self.game.pass_turn(0)
            else:
                self.game.pass_turn(0)
            self.next_ai_time = pygame.time.get_ticks() + 1500

    def do_pass(self):
        success, msg = self.game.pass_turn(0)
        if success:
            speak("不要")
            self.human.clear_selection()
            self.next_ai_time = pygame.time.get_ticks() + 5000
        else:
            self.set_status(msg)

    def do_hint(self):
        ok, indices = self.human.find_hint(self.game)
        if ok:
            self.human.select_cards(indices)
        else:
            self.set_status("无法提示")

    def do_sort(self):
        """整理手牌：按主牌>花色>点数排序"""
        cards = self.game.player_cards[0]
        sorted_cards = sorted(cards, key=lambda c: (
            0 if self.game.power_eval.is_trump(c) else 1,
            {'spade': 0, 'heart': 1, 'diamond': 2, 'club': 3}.get(c[1], 4),
            -self.game.power_eval.power(c)
        ))
        self.game.player_cards[0] = sorted_cards
        self.human.clear_selection()
        speak("已整理")

    def restart(self):
        self.game.reset()
        self.human.clear_selection()
        self.game.deal()
        self._pick_nicknames()
        self.bid_auto_timer = pygame.time.get_ticks() + 15000
        speak("新的一局")

    def update(self, dt):
        now = pygame.time.get_ticks()

        if self.status_timer > 0:
            self.status_timer -= 1
        else:
            self.status_text = ""

        if self.game.phase == PHASE_ENDED:
            self.human_deadline = None
            return

        # 人类出牌30秒倒计时（放在AI逻辑之前，不受next_ai_time阻塞）
        if self.game.phase == PHASE_PLAYING and self.game.current_player == 0:
            # 一轮已出满：等展示延迟到期再结算，让玩家看清最后一家出的牌
            if self.game.trick_complete:
                self.human_deadline = None
                if now >= self.next_ai_time:
                    self.game._finish_trick()
                    self.game.trick_complete = False
                    self.next_ai_time = now + 300
                return
            if self.human_deadline is None:
                self.human_deadline = now + 30000
            elif now >= self.human_deadline:
                self.human_deadline = None
                self.auto_play_human()
                now = pygame.time.get_ticks()
        else:
            self.human_deadline = None

        # 叫主阶段自动翻底牌
        if self.game.phase == PHASE_BIDDING:
            if now > self.bid_auto_timer and not self.game.bid_history:
                self.game.auto_bid_from_bottom()
                speak("翻底牌确定主花色")
                self.next_ai_time = now + 2000
                return

        if now < self.next_ai_time:
            return

        # AI行动
        cp = self.game.current_player
        if cp == 0:
            return

        ai = self.ais[cp - 1]

        if self.game.phase == PHASE_BIDDING:
            action, cards = ai.decide_bid(self.game)
            if action == "bid" and cards:
                success, msg = self.game.bid(cp, cards)
                if success:
                    speak(f"玩家{cp} 亮主")
                self.next_ai_time = now + 2500
            else:
                # AI不亮主，下一个
                self.game.current_player = (cp + 1) % 4
                self.next_ai_time = now + 1000
                # 如果所有人都pass，翻底牌
                if self.game.current_player == 0 and not self.game.bid_history:
                    self.bid_auto_timer = now  # 立即触发
            return

        if self.game.phase == PHASE_DISCARD:
            if cp == self.game.dealer:
                cards = ai.decide_discard(self.game)
                success, msg = self.game.discard_bottom(cp, cards)
                if success:
                    speak("庄家扣底")
                self.next_ai_time = now + 2000
            return

        if self.game.phase == PHASE_PLAYING:
            # 本轮已出满，展示延迟到期后结算（到达此处说明 now >= next_ai_time）
            if self.game.trick_complete:
                self.game._finish_trick()
                self.game.trick_complete = False
                self.next_ai_time = now + 300
                return

            action, cards = ai.decide_play(self.game)
            if action == "play":
                success, msg = self.game.play(cp, cards)
                if success:
                    hand = get_shengji_hand_type(cards, self.game.power_eval)
                    self._speak_play(hand, cards)
                # 如果本轮出满，多给一点时间看清最后一家出的牌
                delay = 2500 if self.game.trick_complete else 1500
                self.next_ai_time = now + delay
            else:
                self.game.pass_turn(cp)
                self.next_ai_time = now + 2500
            return

    def draw(self):
        draw_table(self.screen)

        if self.game.phase in (PHASE_BIDDING, PHASE_DISCARD, PHASE_PLAYING):
            # 绘制4家
            self.click_areas = draw_player_bottom(
                self.screen, self.game.player_cards[0], self.human.selected_indices, self.game.power_eval
            )
            draw_player_left(self.screen, len(self.game.player_cards[1]), self.player_names[1],
                           is_dealer=(self.game.dealer == 1))
            draw_player_top(self.screen, len(self.game.player_cards[2]), self.player_names[2],
                          is_dealer=(self.game.dealer == 2))
            draw_player_right(self.screen, len(self.game.player_cards[3]), self.player_names[3],
                            is_dealer=(self.game.dealer == 3))

            # 出牌区
            skip = self.game.current_player if self.game.trick_complete else None
            draw_play_area_shengji(self.screen, self.game.current_trick, self.game.power_eval, self.player_names, skip_player=skip, passes=self.game.current_passes)

            # 底牌显示：叫主/扣底阶段放大在中央，出牌后缩小在右上角
            if self.game.phase in (PHASE_BIDDING, PHASE_DISCARD):
                draw_bottom_cards(self.screen, self.game.bottom_cards, center_y=325)
            elif self.game.phase in (PHASE_PLAYING, PHASE_ENDED) and self.game.bottom_cards:
                draw_bottom_cards_mini(self.screen, self.game.bottom_cards)

        # 信息面板和消息
        draw_info_panel_shengji(self.screen, self.game, self.player_names)
        draw_messages_shengji(self.screen, self.game.messages, self.player_names)

        # 双方吃到的分牌（出牌阶段）
        if self.game.phase == PHASE_PLAYING:
            draw_captured_cards(self.screen, self.game.captured, self.game.scores)

        # 按钮
        self.draw_buttons()

        # 轮到指示
        self.draw_turn_indicator()

        # 叫主阶段：自动定主倒计时提示（有人亮主后自然消失）
        if self.game.phase == PHASE_BIDDING and not self.game.bid_history:
            remaining = max(0, (self.bid_auto_timer - pygame.time.get_ticks()) // 1000)
            hint_font = get_font(FONT_SIZE_SMALL)
            hint = hint_font.render(f"{remaining}秒后自动确定主花色", True, COLOR_TEXT_YELLOW)
            self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 450))

        # 扣底阶段：实时显示选牌进度
        if self.game.phase == PHASE_DISCARD and self.game.dealer == 0:
            selected_count = len(self.human.selected_indices)
            font = get_font(FONT_SIZE_MEDIUM)
            if selected_count == 8:
                tip = "请扣 8 张底牌（已选 8/8），可以扣底了"
                color = (80, 255, 80)
            else:
                tip = f"请扣 8 张底牌（已选 {selected_count}/8）"
                color = COLOR_TEXT_YELLOW
            tip_surf = font.render(tip, True, color)
            tip_rect = tip_surf.get_rect(center=(SCREEN_WIDTH // 2, 505))
            self.screen.blit(tip_surf, tip_rect)

        # 状态提示
        if self.status_text:
            font = get_font(FONT_SIZE_MEDIUM)
            surf = font.render(self.status_text, True, (255, 0, 0))
            rect = surf.get_rect(center=(SCREEN_WIDTH // 2, 345))
            bg = pygame.Rect(rect.x - 10, rect.y - 5, rect.width + 20, rect.height + 10)
            s = pygame.Surface((bg.width, bg.height), pygame.SRCALPHA)
            s.fill((0, 0, 0, 180))
            self.screen.blit(s, bg.topleft)
            self.screen.blit(surf, rect)

        present()
        pygame.display.flip()

    def draw_buttons(self):
        mouse_pos = pygame.mouse.get_pos()
        self.action_buttons = {}

        # 语音开关
        voice_w, voice_h = 120, 50
        voice_x = SCREEN_WIDTH - voice_w - 20
        voice_y = SCREEN_HEIGHT - voice_h - 15
        voice_rect = pygame.Rect(voice_x, voice_y, voice_w, voice_h)
        voice_text = "语音:开" if is_voice_enabled() else "语音:关"
        draw_button(self.screen, voice_text, voice_x, voice_y, voice_w, voice_h,
                   hover=voice_rect.collidepoint(mouse_pos))
        self.action_buttons["voice"] = voice_rect

        # 返回大厅
        menu_w, menu_h = 120, 50
        menu_x = 20
        menu_y = SCREEN_HEIGHT - menu_h - 15
        menu_rect = pygame.Rect(menu_x, menu_y, menu_w, menu_h)
        draw_button(self.screen, "返回", menu_x, menu_y, menu_w, menu_h,
                   hover=menu_rect.collidepoint(mouse_pos))
        self.action_buttons["menu"] = menu_rect

        if self.game.phase == PHASE_BIDDING and self.game.current_player == 0:
            bw, bh = 120, 55
            gap = 30
            labels = [("亮主", "bid"), ("不亮", "pass_bid")]
            total_w = len(labels) * bw + (len(labels) - 1) * gap
            start_x = (SCREEN_WIDTH - total_w) // 2
            y = 545
            for i, (text, key) in enumerate(labels):
                x = start_x + i * (bw + gap)
                rect = pygame.Rect(x, y, bw, bh)
                draw_button(self.screen, text, x, y, bw, bh, hover=rect.collidepoint(mouse_pos))
                self.action_buttons[key] = rect

        elif self.game.phase == PHASE_DISCARD and self.game.dealer == 0:
            bw, bh = 140, 55
            x = SCREEN_WIDTH // 2 - bw // 2
            y = 545
            rect = pygame.Rect(x, y, bw, bh)
            draw_button(self.screen, "扣底", x, y, bw, bh, hover=rect.collidepoint(mouse_pos))
            self.action_buttons["discard"] = rect

        elif self.game.phase == PHASE_PLAYING and self.game.current_player == 0:
            bw, bh = 100, 50
            gap = 15
            labels = [("出牌", "play"), ("不要", "pass"), ("提示", "hint"), ("整理", "sort")]
            total_w = len(labels) * bw + (len(labels) - 1) * gap
            start_x = (SCREEN_WIDTH - total_w) // 2
            y = 545
            for i, (text, key) in enumerate(labels):
                x = start_x + i * (bw + gap)
                rect = pygame.Rect(x, y, bw, bh)
                draw_button(self.screen, text, x, y, bw, bh, hover=rect.collidepoint(mouse_pos))
                self.action_buttons[key] = rect

        elif self.game.phase == PHASE_ENDED:
            bw, bh = 200, 65
            x = SCREEN_WIDTH // 2 - bw // 2
            y = 545
            rect = pygame.Rect(x, y, bw, bh)
            draw_button(self.screen, "再来一局", x, y, bw, bh, hover=rect.collidepoint(mouse_pos))
            self.action_buttons["restart"] = rect

    def draw_turn_indicator(self):
        if self.game.phase not in (PHASE_BIDDING, PHASE_PLAYING):
            return
        cp = self.game.current_player
        positions = [
            (SCREEN_WIDTH // 2, 505),       # 底部（在按钮上方约1/4按钮高度）
            (80, 400),                       # 左侧
            (890, 82),                       # 上方（顶部牌背行右侧，与牌背垂直居中）
            (SCREEN_WIDTH - 80, 400),        # 右侧
        ]
        if 0 <= cp < 4:
            x, y = positions[cp]
            self._draw_clock(x, y)
            # 人类出牌倒计时：在闹钟右侧显示剩余秒数
            if (self.game.phase == PHASE_PLAYING and cp == 0
                    and self.human_deadline is not None):
                remaining = max(0, -(-(self.human_deadline - pygame.time.get_ticks()) // 1000))
                color = (255, 60, 60) if remaining <= 10 else COLOR_TEXT_YELLOW
                font = get_font(FONT_SIZE_MEDIUM)
                surf = font.render(f"{remaining}秒", True, color)
                rect = surf.get_rect(midleft=(x + 36, y))
                self.screen.blit(surf, rect)

    def _draw_clock(self, x, y, radius=24):
        pygame.draw.circle(self.screen, (255, 215, 0), (x, y), radius)
        pygame.draw.circle(self.screen, (80, 50, 0), (x, y), radius, 3)
        pygame.draw.line(self.screen, (80, 50, 0), (x, y), (x, y - radius + 8), 3)
        pygame.draw.line(self.screen, (80, 50, 0), (x, y), (x + radius // 2 - 3, y), 3)
        pygame.draw.circle(self.screen, (80, 50, 0), (x - 10, y - radius + 5), 4)
        pygame.draw.circle(self.screen, (80, 50, 0), (x + 10, y - radius + 5), 4)


if __name__ == "__main__":
    pygame.init()
    screen = setup_display("四副牌升级 - 老人专用大字版")
    clock = pygame.time.Clock()
    app = ShengjiApp(screen, clock)
    app.run()
    pygame.quit()
