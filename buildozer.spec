[app]
title = CompásZero
package.name = compaszero
package.domain = com.compaszero
source.dir = src
source.include_exts = py,kv,png,jpg,zip,ttf
version = 0.1.0
requirements = python3,kivy==2.3.1
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/assets/icon.png
android.presplash_color = #000000
android.api = 35
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
