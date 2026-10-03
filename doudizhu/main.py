"""
斗地主游戏主程序。
"""
import pygame
import sys
import random
import os

# 确保能导入 common
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.constants import *
from common.audio import speak, set_voice_enabled, is_voice_enabled
from common.renderer_base import draw_table, draw_button, get_font
from common.platform_compat import setup_display, present, map_pos
from doudizhu.engine import DoudizhuGame, get_hand_type, PHASE_DEALING, PHASE_BIDDING, PHASE_PLAYING, PHASE_ENDED
from doudizhu.ai import AIPlayer
from doudizhu.renderer import draw_player_area, draw_play_area, draw_info_panel, draw_messages, draw_card_panel
from doudizhu.player import HumanPlayer


class DoudizhuApp:
    DIFFICULTY_LABELS = {
        DIFFICULTY_EASY: "简单",
        DIFFICULTY_NORMAL: "普通",
        DIFFICULTY_HARD: "困难",
    }

    def __init__(self, screen, clock):
        self.screen = screen
        self.clock = clock
        self.game = DoudizhuGame()
        self.human = HumanPlayer()
        self.ai1 = None
        self.ai2 = None
        self.card_positions = []
        self.next_ai_time = 0
        self.running = True
        self.status_text = ""
        self.status_timer = 0
        self.difficulty = None
        self.difficulty_buttons = {}
        self.pass_display = None
        self.initial_cards = [[], [], []]
        self.show_history = False
        self.player_names = ["你", "玩家A", "玩家B"]
        self.back_to_menu = False
        self.human_deadline = None  # 人类出牌倒计时截止时刻（get_ticks），None表示未启用
        self._last_cp = -1       # 上一帧的当前玩家（用于AI倒计时起点）
        self._ai_turn_start = 0  # 当前回合开始时刻
        self._pick_nicknames()

    def set_status(self, text):
        self.status_text = text
        self.status_timer = 120

    def run(self):
        self.back_to_menu = False
        while self.running and not self.back_to_menu:
            dt = self.clock.tick(FPS)
            self.handle_events()
            self.update(dt)
            self.draw()
        return self.back_to_menu

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

    def _pick_nicknames(self):
        picks = random.sample(AI_NICKNAMES, 2)
        self.player_names = ["你", picks[0], picks[1]]
        self.game.player_names = self.player_names

    def set_difficulty(self, diff):
        self.difficulty = diff
        self.ai1 = AIPlayer(1, diff)
        self.ai2 = AIPlayer(2, diff)
        self.game.deal()
        self._pick_nicknames()
        self.initial_cards = [c[:] for c in self.game.player_cards]
        self.show_history = False
        speak(f"当前难度：{self.DIFFICULTY_LABELS[diff]}")

    def handle_click(self, pos):
        mx, my = pos

        if self.difficulty is None:
            for diff, rect in self.difficulty_buttons.items():
                if rect.collidepoint(mx, my):
                    self.set_difficulty(diff)
                    return
            return

        if self.game.phase == PHASE_BIDDING and self.game.current_player == 0:
            for score, rect in self.bid_buttons.items():
                if rect.collidepoint(mx, my):
                    self.do_human_bid(score)
                    return
            return

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

        if self.game.phase == PHASE_ENDED:
            if "restart" in self.action_buttons and self.action_buttons["restart"].collidepoint(mx, my):
                self.restart()
                return
            if "change_diff" in self.action_buttons and self.action_buttons["change_diff"].collidepoint(mx, my):
                self.change_difficulty()
                return
            if "history_cards" in self.action_buttons and self.action_buttons["history_cards"].collidepoint(mx, my):
                self.show_history = not self.show_history
                return

        if "voice" in self.action_buttons and self.action_buttons["voice"].collidepoint(mx, my):
            set_voice_enabled(not is_voice_enabled())
            return

        if "menu" in self.action_buttons and self.action_buttons["menu"].collidepoint(mx, my):
            self.back_to_menu = True
            return

        if self.game.phase in (PHASE_BIDDING, PHASE_PLAYING) and self.card_positions:
            clicked = self.human.handle_click(pos, self.card_positions)
            if clicked:
                return

    def do_human_bid(self, score):
        if score == 0:
            speak("不叫")
        else:
            speak(f"叫 {score} 分")
        finished, landlord = self.game.bid(0, score)
        if finished:
            speak(f"{self.player_names[self.game.landlord]} 成为地主")
            self.game.current_player = self.game.landlord
            self.next_ai_time = pygame.time.get_ticks() + 3000
        else:
            self.game.current_player = 1
            self.next_ai_time = pygame.time.get_ticks() + 3000

    def do_play(self):
        cards = self.human.get_selected_cards(self.game.player_cards[0])
        if not cards:
            self.set_status("请先选牌！")
            return
        success, msg = self.game.play(0, cards)
        if success:
            self.human_deadline = None
            hand = get_hand_type(cards)
            self._speak_hand(hand, cards)
            self.human.clear_selection()
            if msg == "win":
                self.set_status("你赢了！")
                speak("你赢了")
                self.game.phase = PHASE_ENDED
                return
            self.next_ai_time = pygame.time.get_ticks() + 3000
        else:
            self.set_status(msg)

    def _speak_hand(self, hand, cards):
        """播报出牌"""
        from doudizhu.engine import HAND_ROCKET, HAND_BOMB, HAND_SINGLE, HAND_PAIR, HAND_TRIPLE, HAND_TRIPLE_SINGLE, HAND_TRIPLE_PAIR, HAND_STRAIGHT, HAND_DOUBLE_STRAIGHT, HAND_PLAIN, HAND_PLAIN_WING_SINGLE, HAND_PLAIN_WING_PAIR, HAND_FOUR_TWO, HAND_FOUR_TWO_PAIRS
        ht = hand[0]
        if ht == HAND_ROCKET:
            speak("王炸")
        elif ht == HAND_BOMB:
            speak(f"炸弹，{cards[0][0]}")
        elif ht == HAND_SINGLE:
            speak(f"{cards[0][0]}")
        elif ht == HAND_PAIR:
            speak(f"对{cards[0][0]}")
        elif ht == HAND_TRIPLE:
            speak(f"三个{cards[0][0]}")
        elif ht == HAND_TRIPLE_SINGLE:
            speak("三带一")
        elif ht == HAND_TRIPLE_PAIR:
            speak("三带二")
        elif ht == HAND_STRAIGHT:
            speak("顺子")
        elif ht == HAND_DOUBLE_STRAIGHT:
            speak("连对")
        elif ht == HAND_PLAIN:
            speak("飞机")
        elif ht == HAND_PLAIN_WING_SINGLE:
            speak("飞机带翅膀")
        elif ht == HAND_PLAIN_WING_PAIR:
            speak("飞机带对")
        elif ht == HAND_FOUR_TWO:
            speak("四带二")
        elif ht == HAND_FOUR_TWO_PAIRS:
            speak("四带两对")
        else:
            speak("出牌")

    def auto_play_human(self):
        """倒计时超时：自动打出提示的牌；打不过则自动不要"""
        speak("时间到，自动出牌")
        ok, indices = self.human.find_hint(self.game)
        if ok:
            self.human.select_cards(indices)
            self.do_play()
        if self.game.phase == PHASE_PLAYING and self.game.current_player == 0:
            # 没有能大过的牌（或出牌未成功）：自动不要；首出时do_play必成功不会到这
            self.do_pass()
            if self.game.current_player == 0:
                # 兜底防死循环：仍然轮到自己就直接推进
                self.next_ai_time = pygame.time.get_ticks() + 1500
        self.human.clear_selection()

    def do_pass(self):
        success, msg = self.game.pass_turn(0)
        if success:
            self.human.clear_selection()
            self.next_ai_time = pygame.time.get_ticks() + 1500
        else:
            self.set_status(msg)

    def do_hint(self):
        ok, indices = self.human.find_hint(self.game)
        if ok:
            self.human.select_cards(indices)
        else:
            if self.game.last_play and self.game.consecutive_pass < 2:
                self.set_status("没有能大过的牌，点击'不要'")
            else:
                self.set_status("无法提示")

    def restart(self):
        self.game.reset()
        self.human.clear_selection()
        self.game.deal()
        self._pick_nicknames()
        self.next_ai_time = 0
        self.status_text = ""
        self.initial_cards = [c[:] for c in self.game.player_cards]
        self.show_history = False
        speak("新的一局")

    def change_difficulty(self):
        self.difficulty = None
        self.game.reset()
        self.human.clear_selection()
        self.next_ai_time = 0
        self.status_text = ""
        self.initial_cards = [[], [], []]
        self.show_history = False

    def update(self, dt):
        now = pygame.time.get_ticks()

        cp_now = self.game.current_player
        if cp_now != self._last_cp:
            self._last_cp = cp_now
            self._ai_turn_start = now

        if self.status_timer > 0:
            self.status_timer -= 1
        else:
            self.status_text = ""

        if self.pass_display:
            self.pass_display["timer"] -= 1
            if self.pass_display["timer"] <= 0:
                self.pass_display = None

        if self.game.phase == PHASE_ENDED:
            self.human_deadline = None
            return

        # 人类出牌30秒倒计时（放在AI逻辑之前，不受next_ai_time阻塞）
        if self.game.phase == PHASE_PLAYING and self.game.current_player == 0:
            if self.human_deadline is None:
                self.human_deadline = now + 30000
            elif now >= self.human_deadline:
                self.human_deadline = None
                self.auto_play_human()
        else:
            self.human_deadline = None

        if now < self.next_ai_time:
            return

        if self.game.phase == PHASE_BIDDING:
            cp = self.game.current_player
            if cp == 1:
                score = self.ai1.decide_bid(self.game)
                if score == 0:
                    speak("不叫")
                else:
                    speak(f"叫 {score} 分")
                finished, landlord = self.game.bid(cp, score)
                if finished:
                    speak(f"{self.player_names[self.game.landlord]} 成为地主")
                    self.game.current_player = self.game.landlord
                    self.next_ai_time = now + 3000
                else:
                    self.game.current_player = 2
                    self.next_ai_time = now + 3000
            elif cp == 2:
                score = self.ai2.decide_bid(self.game)
                if score == 0:
                    speak("不叫")
                else:
                    speak(f"叫 {score} 分")
                finished, landlord = self.game.bid(cp, score)
                if finished:
                    speak(f"{self.player_names[self.game.landlord]} 成为地主")
                    self.game.current_player = self.game.landlord
                    self.next_ai_time = now + 3000
                else:
                    self.game.current_player = 0
                    self.next_ai_time = now + 3000
            return

        if self.game.phase == PHASE_PLAYING:
            cp = self.game.current_player
            if cp == 0:
                return
            ai = self.ai1 if cp == 1 else self.ai2
            action, cards = ai.decide_play(self.game)
            if action == "play":
                self.pass_display = None
                hand = get_hand_type(cards)
                self._speak_hand(hand, cards)
                success, msg = self.game.play(cp, cards)
                if msg == "win":
                    speak(f"{self.player_names[cp]} 赢了")
                    self.game.phase = PHASE_ENDED
                    return
                self.next_ai_time = now + 3000
            else:
                speak("不要")
                self.game.pass_turn(cp)
                self.pass_display = {"player": cp, "timer": 45}
                self.next_ai_time = now + 1500

    def draw(self):
        draw_table(self.screen)

        if self.difficulty is None:
            self.draw_difficulty_select()
            present()
            pygame.display.flip()
            return

        if self.game.phase != PHASE_DEALING:
            landlord = getattr(self.game, 'landlord', -1)
            if self.game.phase != PHASE_ENDED:
                self.card_positions = draw_player_area(
                    self.screen, self.game, 0, self.human.selected_indices, self.player_names, landlord
                )
                draw_player_area(self.screen, self.game, 1, names=self.player_names, landlord=landlord)
                draw_player_area(self.screen, self.game, 2, names=self.player_names, landlord=landlord)
                draw_play_area(self.screen, self.game)
            draw_info_panel(self.screen, self.game, self.DIFFICULTY_LABELS.get(self.difficulty, "简单"), names=self.player_names)
            draw_messages(self.screen, self.game)

        if self.pass_display:
            pd = self.pass_display
            font = get_font(FONT_SIZE_MEDIUM)
            text = font.render(self.player_names[pd["player"]] + " 不要", True, COLOR_TEXT_YELLOW)
            if pd["player"] == 1:
                x = 10 + CARD_WIDTH + 15
                y = 220 + 80
            else:
                x = SCREEN_WIDTH - CARD_WIDTH - 10 - text.get_width() - 15
                y = 220 + 80
            self.screen.blit(text, (x, y))

        if self.game.phase == PHASE_ENDED:
            landlord = getattr(self.game, 'landlord', -1)
            if self.show_history:
                draw_card_panel(self.screen, self.initial_cards, "历史初始手牌", landlord=landlord, names=self.player_names)
            else:
                draw_card_panel(self.screen, self.game.player_cards, "本局剩余手牌", landlord=landlord, names=self.player_names)

        self.draw_buttons()
        self.draw_turn_indicator(self.screen)

        if self.status_text:
            font = get_font(FONT_SIZE_MEDIUM)
            surf = font.render(self.status_text, True, (255, 0, 0))
            rect = surf.get_rect(center=(SCREEN_WIDTH // 2, 280))
            bg = pygame.Rect(rect.x - 10, rect.y - 5, rect.width + 20, rect.height + 10)
            s = pygame.Surface((bg.width, bg.height), pygame.SRCALPHA)
            s.fill((0, 0, 0, 180))
            self.screen.blit(s, bg.topleft)
            self.screen.blit(surf, rect)

        present()
        pygame.display.flip()

    def draw_buttons(self):
        mouse_pos = pygame.mouse.get_pos()
        self.bid_buttons = {}
        self.action_buttons = {}

        # 语音开关
        voice_w, voice_h = 120, 50
        voice_x = SCREEN_WIDTH - voice_w - 20
        voice_y = SCREEN_HEIGHT - voice_h - 15
        voice_rect = pygame.Rect(voice_x, voice_y, voice_w, voice_h)
        voice_text = "语音:开" if is_voice_enabled() else "语音:关"
        voice_hover = voice_rect.collidepoint(mouse_pos)
        draw_button(self.screen, voice_text, voice_x, voice_y, voice_w, voice_h, hover=voice_hover)
        self.action_buttons["voice"] = voice_rect

        # 返回大厅按钮
        menu_w, menu_h = 120, 50
        menu_x = 20
        menu_y = SCREEN_HEIGHT - menu_h - 15
        menu_rect = pygame.Rect(menu_x, menu_y, menu_w, menu_h)
        menu_hover = menu_rect.collidepoint(mouse_pos)
        draw_button(self.screen, "返回", menu_x, menu_y, menu_w, menu_h, hover=menu_hover)
        self.action_buttons["menu"] = menu_rect

        if self.game.phase == PHASE_BIDDING and self.game.current_player == 0:
            labels = [("1分", 1), ("2分", 2), ("3分", 3), ("不叫", 0)]
            bw, bh = 100, 50
            gap = 20
            total_w = len(labels) * bw + (len(labels) - 1) * gap
            start_x = (SCREEN_WIDTH - total_w) // 2
            y = 560
            for i, (text, score) in enumerate(labels):
                x = start_x + i * (bw + gap)
                rect = pygame.Rect(x, y, bw, bh)
                hover = rect.collidepoint(mouse_pos)
                draw_button(self.screen, text, x, y, bw, bh, hover=hover)
                self.bid_buttons[score] = rect

        elif self.game.phase == PHASE_PLAYING and self.game.current_player == 0:
            bw, bh = 100, 50
            gap = 20
            labels = [("出牌", "play"), ("不要", "pass"), ("提示", "hint")]
            total_w = len(labels) * bw + (len(labels) - 1) * gap
            start_x = (SCREEN_WIDTH - total_w) // 2
            y = 560
            for i, (text, key) in enumerate(labels):
                x = start_x + i * (bw + gap)
                rect = pygame.Rect(x, y, bw, bh)
                hover = rect.collidepoint(mouse_pos)
                draw_button(self.screen, text, x, y, bw, bh, hover=hover)
                self.action_buttons[key] = rect

        elif self.game.phase == PHASE_ENDED:
            bw, bh = 160, 60
            gap = 30
            total_w = bw * 3 + gap * 2
            start_x = (SCREEN_WIDTH - total_w) // 2
            y = 760

            rect1 = pygame.Rect(start_x, y, bw, bh)
            hover1 = rect1.collidepoint(mouse_pos)
            draw_button(self.screen, "再来一局", start_x, y, bw, bh, hover=hover1)
            self.action_buttons["restart"] = rect1

            rect2 = pygame.Rect(start_x + bw + gap, y, bw, bh)
            hover2 = rect2.collidepoint(mouse_pos)
            draw_button(self.screen, "换难度", start_x + bw + gap, y, bw, bh, hover=hover2)
            self.action_buttons["change_diff"] = rect2

            rect3 = pygame.Rect(start_x + (bw + gap) * 2, y, bw, bh)
            hover3 = rect3.collidepoint(mouse_pos)
            label = "关闭历史" if self.show_history else "历史手牌"
            draw_button(self.screen, label, start_x + (bw + gap) * 2, y, bw, bh, hover=hover3)
            self.action_buttons["history_cards"] = rect3

    def draw_alarm_clock(self, surface, x, y, radius=28):
        pygame.draw.circle(surface, (255, 215, 0), (x, y), radius)
        pygame.draw.circle(surface, (80, 50, 0), (x, y), radius, 4)
        pygame.draw.line(surface, (80, 50, 0), (x, y), (x, y - radius + 10), 4)
        pygame.draw.line(surface, (80, 50, 0), (x, y), (x + radius // 2 - 4, y), 4)
        pygame.draw.circle(surface, (80, 50, 0), (x - 12, y - radius + 6), 5)
        pygame.draw.circle(surface, (80, 50, 0), (x + 12, y - radius + 6), 5)

    def draw_turn_indicator(self, surface):
        if self.game.phase not in (PHASE_BIDDING, PHASE_PLAYING):
            return
        cp = self.game.current_player
        if cp == 0:
            # 人类闹钟挪到按钮行左侧（按钮行 y=560 起，start_x=570/630）
            x = 530 if self.game.phase == PHASE_BIDDING else 595
            y = 573
        elif cp == 1:
            x = 150 + CARD_WIDTH // 2
            y = 310
        else:
            x = SCREEN_WIDTH - 150 - CARD_WIDTH // 2
            y = 310
        self.draw_alarm_clock(surface, x, y)

        now = pygame.time.get_ticks()
        font = get_font(FONT_SIZE_MEDIUM)
        # 人类出牌倒计时显示（按钮左缘在 630，秒数放闹钟左侧避免压按钮）
        if (cp == 0 and self.game.phase == PHASE_PLAYING and self.human_deadline):
            remaining = max(0, (self.human_deadline - now + 999) // 1000)
            color = COLOR_TEXT_YELLOW if remaining > 10 else (255, 60, 60)
            text = font.render(f"{remaining}秒", True, color)
            surface.blit(text, text.get_rect(midright=(x - 40, y)))
        # AI 思考倒计时：从30秒开始倒数，轮到即消失（看起来像真人在想牌）
        elif cp != 0 and self.next_ai_time > now:
            remaining = max(0, 30 - (now - self._ai_turn_start) // 1000)
            if remaining > 0:
                text = font.render(f"{remaining}秒", True, COLOR_TEXT_YELLOW)
                if cp == 1:
                    rect = text.get_rect(midleft=(x + 40, y))
                else:
                    rect = text.get_rect(midright=(x - 40, y))
                surface.blit(text, rect)

    def draw_difficulty_select(self):
        mouse_pos = pygame.mouse.get_pos()
        self.difficulty_buttons = {}

        font_large = get_font(56)
        title = font_large.render("斗地主 - 请选择游戏难度", True, COLOR_TEXT_YELLOW)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 140))

        hints = {
            DIFFICULTY_EASY: "对手会手下留情，适合休闲",
            DIFFICULTY_NORMAL: "正常水平，有来有回",
            DIFFICULTY_HARD: "对手很强，要小心",
        }

        labels = [("简单", DIFFICULTY_EASY), ("普通", DIFFICULTY_NORMAL), ("困难", DIFFICULTY_HARD)]
        bw, bh = 200, 70
        line_gap = 90
        y = 280
        x = SCREEN_WIDTH // 2 - bw // 2

        font_hint = get_font(FONT_SIZE_SMALL)
        for text, diff in labels:
            rect = pygame.Rect(x, y, bw, bh)
            hover = rect.collidepoint(mouse_pos)
            draw_button(self.screen, text, x, y, bw, bh, hover=hover)
            self.difficulty_buttons[diff] = rect

            hint = font_hint.render(hints[diff], True, COLOR_TEXT)
            self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, y + bh + 12))
            y += bh + line_gap


if __name__ == "__main__":
    pygame.init()
    screen = setup_display("斗地主 - 老人专用大字版")
    clock = pygame.time.Clock()
    app = DoudizhuApp(screen, clock)
    app.run()
    pygame.quit()
