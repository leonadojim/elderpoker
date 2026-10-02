"""
通用工具函数。
"""
import random


def pick_nicknames(n=2, pool=None):
    """从昵称池中随机抽取n个不重复昵称"""
    if pool is None:
        from .constants import AI_NICKNAMES as pool
    return random.sample(pool, min(n, len(pool)))
