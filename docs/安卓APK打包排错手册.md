# 安卓 APK 打包排错手册（pygame / python-for-android / buildozer）

> 本项目（老友扑克：pygame 斗地主+四副牌升级）2026 年 10 月实战记录。
> 环境：Windows 11 无 WSL/Docker 本机，最终方案 = **GitHub Actions + kivy/buildozer 官方 Docker 镜像 + 云端安卓模拟器自动验证**。
> 经过约 20 轮失败迭代，所有坑均已解决。本文档按"环境搭建 → 编译期错误 → 应用层设计错误 → 验证手段"组织。

---

## 一、总体方案选择

| 方案 | 结论 |
|---|---|
| WSL 本地编译 | 需要重启、装一堆依赖，远程操作的机器不适用 |
| GitHub Actions 裸机 ubuntu + pip 装 buildozer | ❌ 不可靠：p4a master 与最新 pip 不兼容（见错误 6） |
| **GitHub Actions + kivy/buildozer Docker 镜像** | ✅ 最终方案，环境官方预装预测试 |

关键点：Docker 镜像里 p4a/buildozer/JDK 版本是配套的，别在裸机上自己 pip 拼环境。

---

## 二、编译期常见错误与解法（按踩坑顺序）

### 1. `Aidl not found` / SDK 许可协议无人确认
```
Accept? (y/N): Skipping following packages as the license is not accepted
build-tools folder not found → Aidl not found
```
**解法**：buildozer.spec 加 `android.accept_sdk_license = True`（CI 无人值守必须）。

### 2. libffi 编译失败：`possibly undefined macro: LT_SYS_SYMBOL_USCORE`
**解法**：GitHub runner 需补装 `libltdl-dev`（`sudo apt-get install libltdl-dev`）。
注意：加包后必须**清缓存重建**（`buildozer appclean` 或删缓存），否则错误残留。

### 3. pygame 老配方与新 Python 不兼容：`fatal error: 'longintrepr.h' file not found`
p4a 内置 pygame 配方版本停留在 2.1.0（2021 年），其预生成 C 文件是老 Cython 产物，Python 3.12+ 移除了 `longintrepr.h`。
**解法**：版本锁定到现代组合（写进 requirements 会覆盖配方版本）：
```ini
requirements = python3==3.13.7,hostpython3==3.13.7,pygame==2.6.1,pyjnius==1.8.0
```

### 4. `python3 should have same version as hostpython3`
锁 `python3` 必须**成对**锁 `hostpython3==同一版本`。

### 5. `No matching distribution found for pyjnius==1.7.0`
pyjnius 旧版本被 PyPI 下架。**1.8.0 起官方发布安卓 wheel**（`android_24_arm64_v8a` / `android_24_x86_64`），锁 1.8.0 后 p4a 直接装 wheel，不用源码编译，又快又稳。
**推论**：`armeabi-v7a`（32 位）**没有** wheel → 会退回源码编译 → 触发错误 6。2017 年后的设备全是 64 位，直接 `android.archs = arm64-v8a`（测试需要可加 x86_64，有 wheel）。

### 6. venv 里 pip 损坏：`cannot import name 'BuildDependencyInstallError' from pip._internal.exceptions`
现象：构建虚拟环境里的 pip 文件新旧混杂（installer.py 是 26.x、exceptions.py 是 25.2）。
根因：p4a 会执行 `pip install ... pip ... --upgrade` 把 venv 里的 pip 升到最新版，**在 Docker overlayfs 上 pip 自升级会写出混杂文件**（已验证 pip 26.2.1 本身在 GitHub 上是自洽的，是升级过程损坏）。
**解法**：用 pip 约束全局锁死版本，禁止升级：
```yaml
# workflow docker run 加：
-e PIP_CONSTRAINT=/home/user/hostcwd/ci-constraints.txt
```
```
# ci-constraints.txt
pip==25.2
Cython>=3.0.11,<3.2
```
另外每次编译前删除缓存里的 venv：`rm -rf .buildozer/android/platform/*/build/venv`（失败 run 的残留会经 actions/cache 传给下一轮）。

### 7. pygame 2.6.1 源码包不含预生成 C 文件：`You need cython`
**解法**：本地配方覆盖（`p4a.local_recipes = ./p4a-recipes`），在配方里声明：
```python
hostpython_prerequisites = ["setuptools", "Cython>=3.0.11,<3.2"]
```
⚠️ 坑：`hostpython_prerequisites` 会**覆盖**默认值 `["setuptools"]`，必须两个都写上，否则下一步报 `No module named 'setuptools'`。

### 8. `Requested API target XX is not available`
现象：SDK cmdline-tools 能下载，但 sdkmanager 装 platform 失败（buildozer 内置的旧版 sdkmanager 6514223 与谷歌当前仓库格式不兼容，2026-10 起确定性失败）。
**解法**：弃用 buildozer 的 SDK 下载，直接用 runner 预装 SDK：
```ini
# buildozer.spec
android.api = 33
android.sdk_path = /opt/android-sdk
```
```yaml
# workflow：runner 的 SDK 挂进容器
docker run --rm \
  -v "$GITHUB_WORKSPACE:/home/user/hostcwd" \
  -v "$ANDROID_HOME:/opt/android-sdk" \
  -e ANDROIDSDK=/opt/android-sdk \
  -e ANDROID_HOME=/opt/android-sdk \
  kivy/buildozer:latest android debug
```
⚠️ 坑 1：环境变量 `ANDROIDSDK` 会被 buildozer 覆盖，**必须**用 spec 里的 `android.sdk_path`。
⚠️ 坑 2：buildozer 只认老式路径 `tools/bin/sdkmanager`，现代 SDK 是 `cmdline-tools/latest/bin/`。在 runner 上做**相对**软链（绝对路径在容器内会指到挂载点外！）：
```bash
sudo ln -sfn cmdline-tools/latest "$ANDROID_HOME/tools"
```

### 9. 编译步骤"人间蒸发"（日志戛然而止、无错误行）
runner 磁盘被撑爆（双架构 .buildozer + 2.6GB NDK + Docker 镜像）。
**解法**：build job 开头加 `jlumbroso/free-disk-space@main`（`android: false` 保住 SDK），可清出 ~30GB。

### 10. 缓存导致改了配方不生效
p4a 对已安装的包会跳过重建。actions/cache 的 key 必须包含配方目录：
```yaml
key: ${{ runner.os }}-buildozer-${{ hashFiles('buildozer.spec', 'p4a-recipes/**') }}
```
配方变更时还要在编译前删旧产物：
```bash
rm -rf .buildozer/android/platform/*/build/other_builds/pygame
rm -rf .buildozer/android/platform/*/build/python-installs/*/*/pygame
rm -rf .buildozer/android/platform/*/dists
```

---

## 三、应用层（APK 设计）错误—— pygame 项目特别容易踩

### 1. 相对路径加载资源 = 真机闪退 ★最隐蔽
`os.path.exists()` 返回 True（文件已解包到 files/app/），但 `pygame.image.load('assets/cards/x.png')` 仍报 `FileNotFoundError`——**SDL 在安卓上对相对路径会去 APK 压缩包的 assets 里找**，而 p4a 把资源打在 `assets/private.tar` 里。
**解法**：所有资源路径一律用 `__file__` 锚定的**绝对路径**：
```python
ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "cards")
```
排查技巧：这种问题真机上 os.path.exists 是 True，极具迷惑性。我们的卡牌和 logo 各踩了一次。

### 2. 中文全部变方块
安卓没有 simhei/微软雅黑，`pygame.font.SysFont` 找不到字体时**不报错静默回退**，中文变方块。
**解法**：打包开源中文字体（思源黑体 NotoSansCJKsc，OFL 许可，~16MB otf），`pygame.font.Font(绝对路径, size)` 优先；`match_font` 逐个候选兜底。记得 `source.include_exts` 加 `otf`。

### 3. 启动闪退：HWUI 线程互斥量崩溃 ★最难
logcat 特征：`FORTIFY: pthread_mutex_lock called on a destroyed mutex` in `hwuiTask0`，启动约 10 秒时（Python/pygame 加载中）SIGABRT，Android 14/15+ 必现。
根因：SDL2 线程模型与 Android 14+ HWUI 渲染线程竞争（p4a 清单模板硬编码 `android:hardwareAccelerated="true"`）。
**解法**：fork python-for-android，把 `bootstraps/_sdl_common/build/templates/AndroidManifest.tmpl.xml` 里改为 `"false"`，spec 里指向自己的分支：
```ini
p4a.fork = 你的用户名
p4a.branch = hwui-fix
```
⚠️ 不能用 `android.extra_manifest_application_arguments` 追加同名属性——XML 属性重复会导致 ManifestMerger 直接报错（且该选项在部分 buildozer 版本里被当成文件路径读取，行为不一）。

### 4. pygame 2.6.1 安卓模板漏编 SIMD 源文件
表现：`dlopen failed: cannot locate symbol "alphablit_alpha_sse2_argb_surf_alpha" referenced by surface.so`，display/image/draw 等模块全部不可用。
根因：pygame 2.6 把 SIMD 代码拆到 `simd_blitters_sse2.c`/`simd_blitters_avx2.c`，但 `buildconfig/Setup.Android.SDL2.in` 模板没跟上（桌面模板有，安卓模板漏了）。链接期不报错（未加 `--no-undefined`），运行时才炸。
**解法**：本地配方生成 Setup 时替换：
```python
setup_file = setup_file.replace(
    "surface src_c/surface.c",
    "surface src_c/simd_blitters_sse2.c src_c/simd_blitters_avx2.c src_c/surface.c")
```

### 5. 系统 TTS 不可靠
国产手机（小米等）系统 TTS 经常没装中文语音包/引擎被阉割，`pyjnius` 调 `TextToSpeech` 不出声。
**解法**：离线语音包——用 edge-tts 在开发机预生成全部播报 mp3（牌名/短语是有限集合），`pygame.mixer` 顺序播放；系统 TTS 仅作兜底。另注意 pyjnius 的 TTS 初始化要放主线程（部分机型在无 Looper 的后台线程直接崩）。`include_exts` 记得加 `mp3,json`。

### 6. 分辨率硬编码
所有 UI 坐标按 1600×900 写死，平板分辨率五花八门。
**解法**：虚拟分辨率 + letterbox：绘制到 1600×900 Surface，每帧 smoothscale 到真实屏幕居中；触摸坐标反向映射。安卓检测用 `ANDROID_ARGUMENT`/`ANDROID_PRIVATE` 环境变量。

### 7. 崩溃诊断手段要前置设计
真机闪退看不到任何信息等于抓瞎。必备三件套：
- main.py 第一行起把 stdout/stderr 重定向到 `files/app.log`（可经 `adb shell run-as 包名 cat files/app.log` 读取，debug 包可用）；
- 全局 try/except + pygame 红屏显示 traceback（用户拍照即可反馈）+ 同时 `print(file=sys.__stderr__)` 打到 logcat；
- CI 里挂模拟器自动启动验证（见下节）。

---

## 四、云端模拟器自动验证（CI 最后一段）

编译成功≠能跑。流水线最后加 `test-on-emulator` job：装包 → 启动 → 等待 → 检查进程存活 → 截图 → 抓 logcat/app.log。

关键配置（全是坑换来的）：
```yaml
- uses: jlumbroso/free-disk-space@main   # 先清盘（AVD要7GB+），android: false
  with: { tool-cache: true, android: false, dotnet: true, haskell: true,
          large-packages: true, docker-images: true, swap-storage: true }
- uses: reactivecircus/android-emulator-runner@v2
  with:
    api-level: 35
    arch: x86_64            # 比 arm64 翻译快得多（arm64镜像纯翻译启动>10分钟会超时）
    target: google_apis     # default target 在 Apple Silicon 上没有 arm64 镜像
    emulator-boot-timeout: 1800
```

要点：
- **别用 macos + arm64 镜像**：adb daemon 僵死/启动超时反复出现；ubuntu + x86_64 + KVM 最稳。双架构 APK（arm64-v8a, x86_64）正好让模拟器原生跑 x86_64。
- APK 文件名：多架构时**没有 arch 后缀**，脚本里用通配符 `adb install -r eldercards-*-debug.apk`。
- 全屏 App 首次启动会弹系统"正在全屏显示"提示框，自动化点击前先点掉它（Got it 按钮位置）。
- 模拟点击坐标要按 letterbox 缩放映射换算（虚拟 1600×900 → 实际屏幕）。
- 截图验证： `adb shell screencap` + `adb pull` + upload-artifact，AI 目检截图比纯日志可靠得多。

---

## 五、参考文件（本仓库内）

- `buildozer.spec` — 全部版本锁定与打包参数（含注释说明每项为何存在）
- `.github/workflows/build-apk.yml` — 完整流水线：清盘 → 缓存 → SDK 处理 → Docker 编译（失败重试+pip修复）→ 上传 APK → 模拟器验证
- `p4a-recipes/pygame/__init__.py` — pygame 2.6.1 配方覆盖（Cython 依赖 + SIMD 补丁）
- `ci-constraints.txt` — pip/Cython 版本约束
- `p4a 分支`：leonadojim/python-for-android 的 `hwui-fix` 分支（禁硬件加速）——**勿删**
- `tools/gen_voice.py` — 离线语音包生成脚本（改动播报文本后重跑）

## 六、一句话心法

1. 版本全部锁定，别追 latest（除了 SDL 这类随系统修 bug 的）；
2. 缓存是双刃剑：配方/环境变了就要敢于清缓存重建；
3. 每个资源加载都问一句"这在安卓上还是相对路径吗"；
4. 编译成功只是中场休息，模拟器跑起来才算数；
5. 日志设施先于功能上线——没有 logcat/app.log/崩溃画面，真机问题等于无解。
