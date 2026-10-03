"""
语音播报模块，共用。
优先使用 assets/voice/ 离线语音包（pygame.mixer 播放 mp3，不依赖系统 TTS）；
语音包不可用或文本无法解析时，回退系统 TTS（Windows 用 SAPI，安卓用 pyjnius）。

语音包内容定义（FIXED_PHRASES / SEGMENT_PHRASES / 模板变量域）同时被
tools/gen_voice.py 用来生成音频，改动后需重新运行生成脚本。
"""
import os
import re
import json
import threading
import subprocess
import platform
import queue
import time
from .constants import *
from .cards import format_card_text, SUITS, RANKS, JOKERS

_is_windows = platform.system() == "Windows"
_is_android = "ANDROID_ARGUMENT" in os.environ or "ANDROID_PRIVATE" in os.environ
_voice_enabled = True
_speak_queue = queue.Queue()
_speak_thread = None
_android_tts = None
_android_tts_failed = False

# ==================== 语音包文本定义 ====================

def _build_card_texts():
    """全部 54 种牌名文本（与 format_card_text 规则一致）"""
    texts = []
    for suit in SUITS:
        for rank in RANKS:
            texts.append(format_card_text((rank, suit)))
    texts.extend(JOKERS)
    return texts


CARD_TEXTS = _build_card_texts()          # 54 种牌名："红桃5"..."小王""大王"
RANK_TOKENS = RANKS + JOKERS              # 斗地主报牌用的点数："3"..."2""小王""大王"
NAME_TOKENS = ["你"] + AI_NICKNAMES       # 玩家名："你" + 全部 AI 昵称

# 固定短语（整句预生成）
FIXED_PHRASES = [
    # 大厅
    "欢迎来到老友扑克", "进入斗地主", "进入四副牌升级", "返回游戏大厅",
    # 斗地主
    "不叫", "叫 1 分", "叫 2 分", "叫 3 分",
    "你赢了", "王炸", "三带一", "三带二", "顺子", "连对",
    "飞机", "飞机带翅膀", "飞机带对", "四带二", "四带两对",
    "出牌", "新的一局", "不要",
    "当前难度：简单", "当前难度：普通", "当前难度：困难",
    # 四副牌升级
    "四副牌升级，请亮主", "扣底完成", "对子", "三条", "四条",
    "拖拉机", "三连拖", "四连拖", "三三连拖", "四条连拖",
    "时间到，自动出牌", "已整理", "翻底牌确定主花色", "庄家扣底",
    "亮主无主", "亮主黑桃", "亮主红桃", "亮主方块", "亮主梅花",
    "玩家1 亮主", "玩家2 亮主", "玩家3 亮主",
]

# 模板片段（与变量片段拼接播放）
SEGMENT_PHRASES = [
    "成为地主", "赢了", "炸弹", "对", "三个",
    "亮主需要当前打", "的牌或王（对子、三张更大），请重新选择", "手里没有",
]

_NAME_SET = set(NAME_TOKENS)
_RANK_SET = set(RANK_TOKENS)
_CARD_SET = set(CARD_TEXTS)


def all_segment_texts():
    """语音包需要生成的全部片段文本（去重，顺序稳定）"""
    seen = set()
    result = []
    for t in FIXED_PHRASES + CARD_TEXTS + RANK_TOKENS + NAME_TOKENS + SEGMENT_PHRASES:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


_SEGMENT_SET = set(all_segment_texts())

# 含变量的模板：正则 -> 片段列表（变量不在取值域内时返回 None，交给系统 TTS 兜底）
_VOICE_TEMPLATES = [
    (re.compile(r"^(.+) 成为地主$"),
     lambda m: [m.group(1), "成为地主"] if m.group(1) in _NAME_SET else None),
    (re.compile(r"^(.+) 赢了$"),
     lambda m: [m.group(1), "赢了"] if m.group(1) in _NAME_SET else None),
    (re.compile(r"^亮主需要当前打 (.+) 的牌或王（对子、三张更大），请重新选择$"),
     lambda m: ["亮主需要当前打", m.group(1), "的牌或王（对子、三张更大），请重新选择"]
     if m.group(1) in _RANK_SET else None),
    (re.compile(r"^手里没有 (.+)$"),
     lambda m: ["手里没有", m.group(1)] if m.group(1) in _CARD_SET else None),
    (re.compile(r"^对(.+)$"),
     lambda m: ["对", m.group(1)] if m.group(1) in _RANK_SET else None),
    (re.compile(r"^三个(.+)$"),
     lambda m: ["三个", m.group(1)] if m.group(1) in _RANK_SET else None),
]


def resolve_voice_text(text):
    """把播报文本解析为语音包片段文本列表；无法解析返回 None（走系统 TTS 兜底）"""
    if not text:
        return None
    if text in _SEGMENT_SET:
        return [text]
    # 顿号连接的并列片段（如 speak_cards 的牌序列、"炸弹，5"）
    if "，" in text:
        parts = [p for p in text.split("，") if p]
        if parts and all(p in _SEGMENT_SET for p in parts):
            return parts
    for pattern, builder in _VOICE_TEMPLATES:
        m = pattern.match(text)
        if m:
            segments = builder(m)
            if segments:
                return segments
    return None


# ==================== 语音包播放（pygame.mixer）====================

_VOICE_DIR = os.path.join(os.path.dirname(ASSET_DIR), "voice")
_VOICE_CHANNEL = 7          # 专用频道（游戏内无其他音效，避免复用冲突）
_SEGMENT_GAP = 0.15         # 片段间隔秒数（牌与牌之间 ~150ms）

_manifest = None            # None=未加载 False=不可用 dict=片段文本->文件名
_mixer_ready = None         # None=未尝试 True/False
_sounds = {}                # 文件名 -> pygame.mixer.Sound


def _load_manifest():
    global _manifest
    if _manifest is None:
        try:
            with open(os.path.join(_VOICE_DIR, "manifest.json"), encoding="utf-8") as f:
                _manifest = json.load(f)["segments"]
        except Exception:
            _manifest = False
    return _manifest


def _ensure_mixer():
    """惰性初始化 mixer（需在 pygame.init 之后）；失败则静默降级系统 TTS"""
    global _mixer_ready
    if _mixer_ready is None:
        try:
            import pygame
            if not pygame.get_init():
                raise RuntimeError("pygame not initialized")
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            _mixer_ready = True
        except Exception:
            _mixer_ready = False
    return _mixer_ready


def _voice_pack_ready():
    return _ensure_mixer() and bool(_load_manifest())


def _get_sound(filename):
    if filename not in _sounds:
        import pygame
        _sounds[filename] = pygame.mixer.Sound(os.path.join(_VOICE_DIR, filename))
    return _sounds[filename]


def _play_sound_files(filenames):
    """同步顺序播放一组音频文件，片段间留间隔，不叠音"""
    import pygame
    try:
        channel = pygame.mixer.Channel(_VOICE_CHANNEL)
        for filename in filenames:
            channel.play(_get_sound(filename))
            while channel.get_busy():
                time.sleep(0.03)
            time.sleep(_SEGMENT_GAP)
    except Exception:
        pass


def _queue_voice_pack(texts):
    """把片段文本映射为音频文件并入队；任一片段缺文件返回 False"""
    manifest = _load_manifest()
    filenames = []
    for t in texts:
        filename = manifest.get(t)
        if not filename:
            return False
        filenames.append(filename)
    _ensure_worker()
    _speak_queue.put(("sounds", filenames))
    return True


# ==================== 系统 TTS（兜底）====================

def _do_speak(text):
    """实际执行语音播报（同步阻塞）"""
    if _is_android:
        _do_speak_android(text)
    else:
        _do_speak_windows(text)


def _do_speak_android(text):
    """安卓：调用系统 TTS（需平板安装中文语音数据）。非阻塞，直接入队。"""
    global _android_tts, _android_tts_failed
    if _android_tts_failed:
        return
    try:
        from jnius import autoclass
        if _android_tts is None:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
            Locale = autoclass("java.util.Locale")
            _android_tts = TextToSpeech(PythonActivity.mActivity, None)
            _android_tts.setLanguage(Locale.CHINESE)
        TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
        _android_tts.speak(text, TextToSpeech.QUEUE_ADD, None, "elderpoker")
    except Exception:
        _android_tts_failed = True


def _do_speak_windows(text):
    """Windows：PowerShell 调系统 SAPI"""
    try:
        safe_text = text.replace("'", "''")
        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-WindowStyle", "Hidden",
            "-Command",
            f"Add-Type -AssemblyName System.Speech; "
            f"$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$synth.Speak('{safe_text}'); "
            f"$synth.Dispose()"
        ]
        subprocess.run(cmd, timeout=6, check=False)
    except Exception:
        pass


def _speak_worker():
    """语音队列消费线程：("sounds", 文件列表) 走语音包，("text", 文本) 走系统 TTS"""
    while True:
        try:
            item = _speak_queue.get(timeout=1)
            if item is None:
                break
            kind, payload = item
            if kind == "sounds":
                _play_sound_files(payload)
            else:
                _do_speak(payload)
                time.sleep(0.2)
        except queue.Empty:
            continue


def _ensure_worker():
    global _speak_thread
    if _speak_thread is None or not _speak_thread.is_alive():
        _speak_thread = threading.Thread(target=_speak_worker, daemon=True)
        _speak_thread.start()


def set_voice_enabled(enabled):
    global _voice_enabled
    _voice_enabled = enabled


def is_voice_enabled():
    return _voice_enabled


def speak(text):
    """语音播报：优先离线语音包，无法解析时回退系统 TTS"""
    if not _voice_enabled or not text:
        return
    if _voice_pack_ready():
        segments = resolve_voice_text(text)
        if segments and _queue_voice_pack(segments):
            return
    if _is_android:
        # 安卓 TTS 本身是非阻塞的，直接在调用线程（主线程）执行，
        # 避免部分机型在无线程 Looper 的后台线程里创建 TTS 崩溃
        _do_speak_android(text)
        return
    if not _is_windows:
        return
    _ensure_worker()
    _speak_queue.put(("text", text))


def speak_cards(cards):
    """播报一组牌（通用）：语音包按顺序逐张播放，牌间留 ~150ms 间隔"""
    if not _voice_enabled or not cards:
        return
    texts = [format_card_text(c) for c in cards]
    if _voice_pack_ready() and _queue_voice_pack(texts):
        return
    speak("，".join(texts))
