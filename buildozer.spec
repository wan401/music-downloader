[app]
title = 音乐下载工具
package.name = musicdownloader
package.domain = org.purebattle

source.dir = .
source.include_exts = py,html,txt,md

version = 1.1

# 依赖：kivy做WebView壳 + flask后端 + 网络库
requirements = python3,kivy,pyjnius,flask,requests,yt-dlp

# 安卓权限
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,ACCESS_NETWORK_STATE

# 目标安卓版本
android.api = 33
android.minapi = 24
android.ndk = 25b

# 屏幕方向
orientation = portrait

# 全屏
fullscreen = 0

# 启动入口
#source.include_exts = py,html
#main.py 已经是入口

[buildozer]
log_level = 2
warn_on_root = 1
