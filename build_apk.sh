#!/bin/bash
# 在 WSL Ubuntu 里编译长者扑克 APK。
# 用法：重启电脑后，在本项目目录执行（Git Bash）：
#   wsl -d Ubuntu -u root bash /mnt/c/Users/Bill/Desktop/长者扑克/build_apk.sh
set -e

SUDO=""
[ "$(id -u)" -ne 0 ] && SUDO="sudo"

echo "==> 安装编译依赖"
$SUDO apt-get update
$SUDO apt-get install -y git zip unzip openjdk-17-jdk python3-pip python3-venv \
    autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev \
    cmake libffi-dev libssl-dev automake gettext

echo "==> 准备 buildozer 虚拟环境"
python3 -m venv ~/buildozer-env
source ~/buildozer-env/bin/activate
pip install --upgrade pip
pip install buildozer cython

echo "==> 拷贝工程到 WSL 本地磁盘（/mnt/c 上编译会非常慢）"
rm -rf ~/elderpoker
cp -r "/mnt/c/Users/Bill/Desktop/长者扑克" ~/elderpoker
cd ~/elderpoker
rm -rf .buildozer bin __pycache__ */__pycache__

echo "==> 开始编译 APK（首次约 30-60 分钟）"
buildozer android debug

echo "==> 拷贝 APK 回 Windows 项目目录"
mkdir -p "/mnt/c/Users/Bill/Desktop/长者扑克/bin"
cp bin/*.apk "/mnt/c/Users/Bill/Desktop/长者扑克/bin/"
ls -la "/mnt/c/Users/Bill/Desktop/长者扑克/bin/"
echo "==> 完成！APK 在 Windows 桌面 长者扑克/bin/ 目录下"
