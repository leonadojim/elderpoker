"""
离线语音包生成脚本：用 edge-tts（微软在线 TTS，免费）把 common.audio 定义的
全部播报片段合成为 mp3，输出到 assets/voice/，并写 manifest.json（文本 -> 文件名）。

用法（需联网）：
    python tools/gen_voice.py            # 增量生成（已存在的文件跳过）
    python tools/gen_voice.py --rebuild  # 全部重新生成

文件名取 声音+语速+文本 的 md5 前缀（v_<hash>.mp3），避免中文文件名在安卓打包/
文件系统上的兼容问题，也保证片段文本不变时重跑可复用已有文件。
"""
import asyncio
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import edge_tts

from common.audio import all_segment_texts

VOICE = "zh-CN-XiaoxiaoNeural"   # 自然中文女声，适合老年人
RATE = "-10%"                    # 语速放慢 10%
CONCURRENCY = 4                  # 并发数，避免被限流
RETRY = 3

VOICE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "assets", "voice")


def _filename(text):
    key = f"{VOICE}|{RATE}|{text}"
    return "v_" + hashlib.md5(key.encode("utf-8")).hexdigest()[:12] + ".mp3"


async def _gen_one(sem, text, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return True
    async with sem:
        for attempt in range(1, RETRY + 1):
            try:
                communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
                await communicate.save(path)
                if os.path.getsize(path) > 0:
                    return True
            except Exception as e:
                print(f"  重试 {attempt}/{RETRY} [{text}]: {e}")
                await asyncio.sleep(2 * attempt)
        print(f"  失败: {text}")
        return False


async def _generate(texts):
    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [_gen_one(sem, t, os.path.join(VOICE_DIR, _filename(t))) for t in texts]
    results = await asyncio.gather(*tasks)
    return all(results)


def main():
    rebuild = "--rebuild" in sys.argv
    os.makedirs(VOICE_DIR, exist_ok=True)
    texts = all_segment_texts()
    print(f"共 {len(texts)} 个片段，声音 {VOICE}，语速 {RATE}")

    if rebuild:
        for name in os.listdir(VOICE_DIR):
            if name.endswith(".mp3"):
                os.remove(os.path.join(VOICE_DIR, name))

    ok = asyncio.run(_generate(texts))

    manifest = {t: _filename(t) for t in texts}
    manifest_path = os.path.join(VOICE_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"voice": VOICE, "rate": RATE, "segments": manifest},
                  f, ensure_ascii=False, indent=1)

    # 清理不再使用的旧文件
    keep = set(manifest.values()) | {"manifest.json"}
    removed = 0
    for name in os.listdir(VOICE_DIR):
        if name not in keep:
            os.remove(os.path.join(VOICE_DIR, name))
            removed += 1

    total = sum(os.path.getsize(os.path.join(VOICE_DIR, n)) for n in keep
                if os.path.exists(os.path.join(VOICE_DIR, n)))
    print(f"manifest: {len(manifest)} 条，清理旧文件 {removed} 个")
    print(f"语音包总大小: {total / 1024 / 1024:.2f} MB")
    if not ok:
        print("有片段生成失败，请重跑脚本（增量补齐）")
        sys.exit(1)
    print("完成")


if __name__ == "__main__":
    main()
