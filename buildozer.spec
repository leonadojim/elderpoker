[app]

# 应用名称（显示在平板桌面）
title = 老友扑克

package.name = eldercards
package.domain = org.elderpoker

source.dir = .
source.include_exts = py,png,otf,ttf,md
source.exclude_patterns = 斗地主/*,*.zip,bin/*,.github/*

version = 1.0.0

requirements = python3==3.13.7,hostpython3==3.13.7,pygame==2.6.1,pyjnius==1.8.0

# 本地覆盖配方（p4a 内置 pygame 配方版本过旧）
p4a.local_recipes = ./p4a-recipes

orientation = landscape
fullscreen = 1

# 平板主流架构（仅64位；32位会触发pyjnius源码构建导致pip环境损坏）
android.archs = arm64-v8a

# 无敏感权限需求
android.permissions =

# 锁定编译目标API（默认36当日谷歌仓库不稳）
android.api = 33
android.minapi = 24

# 使用CI runner预装的SDK（容器内挂载到/opt/android-sdk），
# 绕开buildozer自带sdkmanager与谷歌仓库不兼容的问题
android.sdk_path = /opt/android-sdk

# CI 无人值守编译：自动接受 Android SDK 许可协议
android.accept_sdk_license = True

[buildozer]

log_level = 2
warn_on_root = 1
