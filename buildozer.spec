[app]
title = NoteYello
package.name = dev
package.domain = com.noteyello

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ico,ttf
source.include_patterns = image/*,icons/*

version = 1.01
requirements = hostpython3==3.11.9,python3==3.11.9,kivy==2.3.0,pillow,pyjnius,android

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/image/icon.png
presplash.filename = %(source.dir)s/image/icmd.png
presplash.color = #000000

android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES

android.api = 33
android.minapi = 21
android.sdk = 33
android.build_tools_version = 33.0.2
android.ndk = 25b
android.accept_sdk_license_agreements = True
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.request_legacy_external_storage = True

p4a.branch = v2024.01.21
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1