"""
平台兼容层：安卓平板上以虚拟 1600x900 分辨率渲染，
再缩放贴到真实屏幕（letterbox 黑边居中），触摸坐标反向映射。
桌面端一切为直通，行为不变。
"""
import os
import pygame
from .constants import SCREEN_WIDTH, SCREEN_HEIGHT

IS_ANDROID = "ANDROID_ARGUMENT" in os.environ or "ANDROID_PRIVATE" in os.environ

_real_screen = None
_virtual_screen = None
_scale = 1.0
_offset_x = 0
_offset_y = 0


def setup_display(caption=None):
    """创建显示，返回可绘制的 Surface（安卓下是虚拟表面）。"""
    global _real_screen, _virtual_screen, _scale, _offset_x, _offset_y
    if IS_ANDROID:
        _real_screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        rw, rh = _real_screen.get_size()
        _scale = min(rw / SCREEN_WIDTH, rh / SCREEN_HEIGHT)
        _offset_x = int((rw - SCREEN_WIDTH * _scale) // 2)
        _offset_y = int((rh - SCREEN_HEIGHT * _scale) // 2)
        _virtual_screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    else:
        _real_screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        _virtual_screen = _real_screen
    if caption:
        pygame.display.set_caption(caption)
    return _virtual_screen


def present():
    """安卓下把虚拟表面缩放贴到真实屏幕（需在 display.flip 前调用）。"""
    if not IS_ANDROID or _real_screen is None:
        return
    _real_screen.fill((0, 0, 0))
    w = int(SCREEN_WIDTH * _scale)
    h = int(SCREEN_HEIGHT * _scale)
    scaled = pygame.transform.smoothscale(_virtual_screen, (w, h))
    _real_screen.blit(scaled, (_offset_x, _offset_y))


def map_pos(pos):
    """把真实触摸/鼠标坐标映射回虚拟 1600x900 坐标。"""
    if not IS_ANDROID:
        return pos
    x = (pos[0] - _offset_x) / _scale
    y = (pos[1] - _offset_y) / _scale
    return (int(x), int(y))
