[app]

title = AuraDex
package.name = auradex
package.domain = org.resolik

source.dir = .
source.include_exts = py,png,jpg,jpeg,wav,mp3,ttf,json

version = 1.1

requirements = python3,kivy

icon.filename = %(source.dir)s/assets/images/app_icon.png

orientation = portrait
fullscreen = 0

# Разрешения на внешнее хранилище НЕ нужны — сейвы хранятся в
# self.user_data_dir (приватная папка приложения), доступной без permissions.
android.permissions =

android.minapi = 21
android.api = 33
android.archs = arm64-v8a, armeabi-v7a

p4a.branch = master

[buildozer]

log_level = 2
warn_on_root = 1
