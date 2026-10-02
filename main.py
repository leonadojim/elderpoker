"""
老年游戏中心 - 主入口
"""
import pygame
import sys
import os

# 确保能找到模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.constants import *
from common.audio import speak, set_voice_enabled, is_voice_enabled
from common.renderer_base import draw_table, draw_button, get_font
from common.platform_compat import setup_display, present, map_pos


class GameCenter:
    def __init__(self):
        pygame.init()
        self.screen = setup_display("老年游戏中心 - 老人专用大字版")
        self.clock = pygame.time.Clock()
        self.running = True

    def run(self):
        speak("欢迎来到老年游戏中心")
        while self.running:
            dt = self.clock.tick(FPS)
            self.handle_events()
            self.draw()
        pygame.quit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.handle_click(map_pos(event.pos))

    def handle_click(self, pos):
        mx, my = pos

        # 斗地主
        if self.btn_doudizhu.collidepoint(mx, my):
            speak("进入斗地主")
            self.launch_doudizhu()
            return

        # 四副牌升级
        if self.btn_shengji.collidepoint(mx, my):
            speak("进入四副牌升级")
            self.launch_shengji()
            return

        # 语音开关
        if self.btn_voice.collidepoint(mx, my):
            set_voice_enabled(not is_voice_enabled())
            return

    def launch_doudizhu(self):
        from doudizhu.main import DoudizhuApp
        app = DoudizhuApp(self.screen, self.clock)
        app.run()
        # 返回后重新初始化显示
        self.screen = setup_display("老年游戏中心 - 老人专用大字版")
        speak("返回游戏大厅")

    def launch_shengji(self):
        from shengji.main import ShengjiApp
        app = ShengjiApp(self.screen, self.clock)
        app.run()
        self.screen = setup_display("老年游戏中心 - 老人专用大字版")
        speak("返回游戏大厅")

    def draw(self):
        draw_table(self.screen)

        mouse_pos = pygame.mouse.get_pos()

        # 大标题
        title_font = get_font(64)
        title = title_font.render("老年游戏中心", True, COLOR_TEXT_YELLOW)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))

        # 副标题
        sub_font = get_font(FONT_SIZE_MEDIUM)
        sub = sub_font.render("请选择游戏", True, COLOR_TEXT)
        self.screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 200))

        # 游戏按钮（大按钮，老人友好）
        bw, bh = 320, 100
        gap = 60
        start_y = 320
        x = SCREEN_WIDTH // 2 - bw // 2

        # 斗地主按钮
        self.btn_doudizhu = pygame.Rect(x, start_y, bw, bh)
        hover1 = self.btn_doudizhu.collidepoint(mouse_pos)
        draw_button(self.screen, "斗地主", x, start_y, bw, bh, hover=hover1)

        # 四副牌升级按钮
        self.btn_shengji = pygame.Rect(x, start_y + bh + gap, bw, bh)
        hover2 = self.btn_shengji.collidepoint(mouse_pos)
        draw_button(self.screen, "四副牌升级", x, start_y + bh + gap, bw, bh, hover=hover2)

        # 说明文字
        hint_font = get_font(FONT_SIZE_SMALL)
        hint1 = hint_font.render("三人游戏，经典玩法", True, COLOR_TEXT)
        self.screen.blit(hint1, (SCREEN_WIDTH // 2 - hint1.get_width() // 2, start_y + bh + 10))

        hint2 = hint_font.render("四人游戏，四副牌", True, COLOR_TEXT)
        self.screen.blit(hint2, (SCREEN_WIDTH // 2 - hint2.get_width() // 2, start_y + bh * 2 + gap + 10))

        # 底部信息
        info_font = get_font(FONT_SIZE_SMALL)
        info = info_font.render("点击大按钮进入游戏 | 语音辅助报牌", True, COLOR_TEXT)
        self.screen.blit(info, (SCREEN_WIDTH // 2 - info.get_width() // 2, SCREEN_HEIGHT - 120))

        # 语音开关（右下角）
        voice_w, voice_h = 140, 55
        voice_x = SCREEN_WIDTH - voice_w - 30
        voice_y = SCREEN_HEIGHT - voice_h - 30
        self.btn_voice = pygame.Rect(voice_x, voice_y, voice_w, voice_h)
        voice_text = "语音:开" if is_voice_enabled() else "语音:关"
        draw_button(self.screen, voice_text, voice_x, voice_y, voice_w, voice_h,
                   hover=self.btn_voice.collidepoint(mouse_pos))

        present()
        pygame.display.flip()


def _show_crash_screen(error_text):
    """启动失败：把错误写到文件并显示在屏幕上（便于平板拍照反馈）"""
    try:
        log_path = os.path.join(os.environ.get("ANDROID_PRIVATE", "."), "crash.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(error_text)
    except Exception:
        pass
    try:
        pygame.init()
        screen = pygame.display.set_mode((1280, 720))
        pygame.display.set_caption("启动错误")
        font = pygame.font.Font(None, 26)
        lines = []
        for raw in error_text.splitlines():
            while len(raw) > 90:
                lines.append(raw[:90])
                raw = raw[90:]
            lines.append(raw)
        clock = pygame.time.Clock()
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type in (pygame.QUIT, pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                    waiting = False
            screen.fill((60, 0, 0))
            y = 20
            for line in lines[-22:]:
                surf = font.render(line, True, (255, 255, 120))
                screen.blit(surf, (10, y))
                y += 30
            hint = font.render("App failed to start. Photo this screen and report. Tap to exit.",
                               True, (255, 255, 255))
            screen.blit(hint, (10, 686))
            pygame.display.flip()
            clock.tick(15)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        app = GameCenter()
        app.run()
    except Exception:
        import traceback
        _show_crash_screen(traceback.format_exc())
        raise
