[app]
title = CompásZero
package.name = compaszero
package.domain = com.compaszero
source.dir = src
source.include_exts = py,kv,png,jpg,zip,ttf,tsv,wav
version = 0.8.0
requirements = python3,kivy==2.3.1,pyjnius,plyer,android
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/assets/icon.png
android.presplash_color = #000000
android.api = 35
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.permissions = INTERNET, RECORD_AUDIO, READ_MEDIA_AUDIO, READ_EXTERNAL_STORAGE
# Android 11+: declarar que usamos el servicio de reconocimiento de voz
android.extra_manifest_xml = ./android/extra_manifest.xml

[buildozer]
log_level = 2
warn_on_root = 1
