# Elder Poker（老友扑克）

> [中文 README](README.md)

**A card game I built for my grandmother.**

My grandma loved playing "Four-Deck Shengji" (四副牌升级, a four-deck climbing/trump card game) on a regional gaming platform in Ganzhou. She played for years — until the platform tied its points system to real-money top-ups. Then she stopped playing.

So as her grandson, I wrote her a version of her own — no payments, no ads, no points schemes. Just clean card playing, the way it should be. Big fonts, voice announcements, and a patient auto-play timer. It runs on Windows PCs and Android tablets/phones.

## Games

| Game | Description |
|---|---|
| Four-Deck Shengji (四副牌升级) | 4 players, 4 decks (216 cards), partners across the table; full rules including bidding, bottom cards, tractors, and bottom-digging scoring |
| Dou Dizhu (斗地主) | The classic 3-player "Fight the Landlord", three difficulty levels |

## Designed for the elderly

- **Big fonts, big cards**: crisp vector-rendered card faces with extra-large corner indices
- **Offline voice announcements** (Microsoft Xiaoxiao voice, pre-generated audio pack) — no dependency on the phone's flaky system TTS; plays cards, turns, and results aloud
- **30-second turn timer**: when time runs out, the game kindly plays the best card for you; AI opponents show ticking clocks too, so it feels like playing with real people
- **Readability first**: captured score cards displayed in two clean rows, discard progress indicator ("selected X/8"), a 2.5-second pause to see the last trick before the table clears
- **No payments, no points, no ads, no internet required**

## Installation (Android tablet/phone)

1. Download the latest APK from [Releases](https://github.com/leonadojim/elderpoker/releases)
2. Copy to the device and tap to install (allow "unknown sources" when prompted)
3. Requirements: 64-bit device (anything from ~2017 onwards), landscape orientation

On PC: install Python and pygame, then run `python main.py`.

## Tech stack

- Python + pygame 2.6.1
- Android packaging via python-for-android / buildozer, built in the cloud with GitHub Actions
- Every push auto-builds the APK and boots it in a cloud Android emulator — with screenshots and logcat — to prove it doesn't crash before it ever reaches a real device
- Hard-won lessons from ~20 failed build iterations are documented in [docs/安卓APK打包排错手册.md](docs/安卓APK打包排错手册.md) (Chinese) — SDK licenses, broken recipes, pip corruption on overlayfs, HWUI mutex crashes, the works

## Screenshots

| Lobby | Four-Deck Shengji in play |
|---|---|
| ![lobby](docs/screenshots/lobby.png) | ![shengji](docs/screenshots/shengji.png) |

## License

Code: MIT License. Card faces from [SVGCards](https://github.com/saulspatz/SVGCards) (public domain). Voice generated with Microsoft edge-tts. Chinese font: Noto Sans CJK (OFL).

---

*For Grandma: take your time, no hurry. If you're stuck, there's always a hint.*
