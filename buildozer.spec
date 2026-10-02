[app]

# 应用名称（显示在平板桌面）
title = 长者扑克

package.name = elderpoker
package.domain = org.elderpoker

source.dir = .
source.include_exts = py,png,otf,ttf,md
source.exclude_patterns = 斗地主/*,*.zip,bin/*,.github/*

version = 1.0.0

requirements = python3,pygame,pyjnius

orientation = landscape
fullscreen = 1

# 平板主流架构
android.archs = arm64-v8a, armeabi-v7a

# 无敏感权限需求
android.permissions =

[buildozer]

log_level = 2
warn_on_root = 1
