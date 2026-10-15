"""
Секретка HEARTBEAT: если держать 14+ кликов в секунду 10 секунд подряд,
открывается особый биом "Сердечный" и аура HEARTBEAT, а после третьего
такого раза — разовый god-event (экран "Infarct :(").

Mellantid — редкий исход той же секретки, а не отдельный триггер: если
момент срабатывания HEARTBEAT совпал с окном стыка игровой Ночи и Утра
(см. game_clock.is_mellantid_window), вместо HEARTBEAT выдаётся Mellantid.
Так поймать её сложнее, чем просто подгадать окно — сначала нужно удержать
сам спам 10 секунд, и только потом его ещё и нужно попасть в окно.

Оформлено как миксин, подмешиваемый в GameScreen — методы используют
self.* напрямую (click_history, biome_label, bg_window_color,
character_row, label и т.д.), а не принимают их параметрами, так как
логика тут неотделима от состояния самого экрана.
"""

import time

from kivy.clock import Clock

from auras import HEARTBEAT_AURA, MELLANTID_AURA

from .game_clock import is_mellantid_window

# Сколько кликов в секунду нужно держать и сколько секунд подряд.
# Пока держишь — визуально ничего не меняется, идёт только отсчёт времени.
HEARTBEAT_CPS_THRESHOLD = 14
HEARTBEAT_CPS_HOLD_SECONDS = 10


class HeartbeatMixin:
    def check_cps_logic(self, dt):
        if self.is_cutscene:
            return
        now = time.time()
        self.click_history = [t for t in self.click_history if now - t <= 1.0]
        cps = len(self.click_history)
        if cps >= HEARTBEAT_CPS_THRESHOLD:
            if self.high_cps_start_time is None:
                self.high_cps_start_time = now
            elapsed = now - self.high_cps_start_time
            if elapsed >= HEARTBEAT_CPS_HOLD_SECONDS:
                self.trigger_heartbeat_secret()
        else:
            self.high_cps_start_time = None

    def trigger_heartbeat_secret(self):
        self.high_cps_start_time = None
        self.click_history = []
        self.heartbeat_count += 1
        self.current_biome = "Сердечный"
        self.biome_label.text = "БИОМ: СЕРДЕЧНЫЙ"
        self.bg_window_color.rgb = (0.3, 0.0, 0.0)
        self._sync_biome_visuals()
        if self.heartbeat_count >= 3 and not self.god_saved:
            self.start_god_event()
        else:
            if is_mellantid_window():
                aura = MELLANTID_AURA
            else:
                aura = HEARTBEAT_AURA
                self.unlock_achievement("validol")
            self.last_rolled_aura = aura
            self.start_cutscene(aura)
            Clock.schedule_once(self.change_biome, 30)

    def start_god_event(self):
        self.is_cutscene = True
        self.character_row.opacity = 0
        self.biome_bg_image.opacity = 0
        self.particle_layer.set_mode(None)
        self.bg_window_color.rgb = (0, 0, 0)
        self.label.text = "[color=ff0000][b]Infarct :([/b][/color]"

        def end(dt):
            self.is_cutscene = False
            self.god_saved = True
            self.character_row.opacity = 1
            self.bg_window_color.rgb = (0.15, 0.15, 0.15)
            self.label.text = "Выживай..."
            self.change_biome()

        Clock.schedule_once(lambda dt: setattr(self.label, 'text', "[color=ffffff]but there is a god[/color]"), 2)
        Clock.schedule_once(end, 5)
