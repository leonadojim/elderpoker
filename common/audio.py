"""
语音播报模块，共用。
Windows 用系统 SAPI（PowerShell），安卓用系统 TTS（pyjnius），其他平台静音。
"""
import os
import threading
import subprocess
import platform
import queue
import time
from .constants import *

_is_windows = platform.system() == "Windows"
_is_android = "ANDROID_ARGUMENT" in os.environ or "ANDROID_PRIVATE" in os.environ
_voice_enabled = True
_speak_queue = queue.Queue()
_speak_thread = None
_android_tts = None


def set_voice_enabled(enabled):
    global _voice_enabled
    _voice_enabled = enabled


def is_voice_enabled():
    return _voice_enabled


def _do_speak(text):
    """实际执行语音播报（同步阻塞）"""
    if _is_android:
        _do_speak_android(text)
    else:
        _do_speak_windows(text)


def _do_speak_android(text):
    """安卓：调用系统 TTS（需平板安装中文语音数据）"""
    global _android_tts
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
        pass


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
    """语音队列消费线程"""
    while True:
        try:
            text = _speak_queue.get(timeout=1)
            if text is None:
                break
            _do_speak(text)
            time.sleep(0.2)
        except queue.Empty:
            continue


def _ensure_worker():
    global _speak_thread
    if _speak_thread is None or not _speak_thread.is_alive():
        _speak_thread = threading.Thread(target=_speak_worker, daemon=True)
        _speak_thread.start()


def speak(text):
    """语音播报（入队，排队播放）"""
    if not _voice_enabled or not text:
        return
    if not (_is_windows or _is_android):
        return
    _ensure_worker()
    _speak_queue.put(text)


def speak_cards(cards):
    """播报一组牌（通用）"""
    from .cards import format_card_text
    if not _voice_enabled or not cards:
        return
    texts = [format_card_text(c) for c in cards]
    speak("，".join(texts))
