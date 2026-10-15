import os
import json

# Фикс известного краша Kivy под Pydroid на Android: провайдер ввода mtdev
# требует library libmtdev.so.1, которой в Pydroid нет (и не нужна — на
# Android тачи и так обрабатываются через сам SDL2). Без этой правки
# попытка её подключить валит создание окна ещё до отрисовки чего-либо.
# Должно идти до любого импорта, который может тронуть kivy.core.window.
from kivy.config import Config
Config.remove_section('input')
Config.add_section('input')

from kivy.app import App
from kivy.core.audio import SoundLoader
from kivy.uix.screenmanager import ScreenManager, NoTransition

from ui_helpers import SOUND_EPIC, SOUND_ROLL, SOUND_ACHIEVEMENT, SOUND_CUTSCENE
from screens.game_screen import GameScreen
from screens.inventory_screen import InventoryScreen
from screens.secret_screens import BlackoutScreen, SmartCheckScreen

PLAYERDATA_DIR_NAME = 'playerdata'


class RngGameApp(App):
    title = "AuraDex"

    def build(self):
        self.inventory_data = self.load_data()
        self.achievements_unlocked = self.load_achievements()
        self.stats = self.load_stats()
        self.settings = self.load_settings()

        # Звуки теперь живут на уровне App (не внутри GameScreen), чтобы
        # окно настроек могло менять громкость в реальном времени из любого
        # места, а не только там, где звук изначально загружен.
        self.bg_music = SoundLoader.load(SOUND_EPIC)
        self.roll_sound = SoundLoader.load(SOUND_ROLL)
        self.achievement_sound = SoundLoader.load(SOUND_ACHIEVEMENT)
        self.cutscene_sound = SoundLoader.load(SOUND_CUTSCENE)

        if self.bg_music:
            self.bg_music.loop = True
            self.bg_music.volume = self.settings['music_volume']
            self.bg_music.play()
        if self.roll_sound:
            self.roll_sound.volume = self.settings['roll_volume']
        if self.achievement_sound:
            self.achievement_sound.volume = self.settings['achievement_volume']
        if self.cutscene_sound:
            self.cutscene_sound.volume = self.settings['cutscene_volume']

        sm = ScreenManager(transition=NoTransition())
        sm.add_widget(GameScreen(name='game'))
        sm.add_widget(InventoryScreen(name='inventory'))
        sm.add_widget(BlackoutScreen(name='blackout'))
        sm.add_widget(SmartCheckScreen(name='smart_check'))
        return sm

    # --- общая папка сохранений ---

    def _playerdata_dir(self):
        # Принудительно задаем путь в созданную тобой папку
        base = '/storage/emulated/0/RNG_Game'

        # Если такого пути нет (например, запуск на ПК), откатываемся на текущую папку
        if not os.path.exists(base):
            base = '.'

        path = os.path.join(base, PLAYERDATA_DIR_NAME)
        try:
            os.makedirs(path, exist_ok=True)
        except OSError:
            pass
        return path

    def _playerdata_path(self, filename):
        return os.path.join(self._playerdata_dir(), filename)

    @staticmethod
    def _read_json(path, default):
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                return default
        return default

    @staticmethod
    def _write_json(path, data):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except OSError as e:
            print(f"[playerdata] Не удалось записать {path}: {e}")

    # --- инвентарь аур ---

    def get_save_path(self):
        return self._playerdata_path('savegame.json')

    def save_data(self):
        self._write_json(self.get_save_path(), self.inventory_data)

    def load_data(self):
        return self._read_json(self.get_save_path(), {})

    def remove_from_inventory(self, name, amount):
        """Удаляет до `amount` штук ауры `name`. Если аур меньше — удаляются
        все имеющиеся. Возвращает остаток (0, если аура пропала из инвентаря)."""
        current = self.inventory_data.get(name, 0)
        removed = min(current, max(amount, 0))
        remaining = current - removed
        if remaining > 0:
            self.inventory_data[name] = remaining
        else:
            self.inventory_data.pop(name, None)
        self.save_data()
        return remaining

    # --- ачивки ---

    def get_achievements_path(self):
        return self._playerdata_path('achievements.json')

    def save_achievements(self):
        self._write_json(self.get_achievements_path(), list(self.achievements_unlocked))

    def load_achievements(self):
        return set(self._read_json(self.get_achievements_path(), []))

    # --- статистика ---

    def get_stats_path(self):
        return self._playerdata_path('stats.json')

    def save_stats(self):
        self._write_json(self.get_stats_path(), self.stats)

    def load_stats(self):
        data = self._read_json(self.get_stats_path(), {})
        return {
            'total_rolls': data.get('total_rolls', 0),
            'rare_auras_caught': data.get('rare_auras_caught', 0),
        }

    # --- настройки (громкости) ---

    def get_settings_path(self):
        return self._playerdata_path('settings.json')

    def save_settings(self):
        self._write_json(self.get_settings_path(), self.settings)

    def load_settings(self):
        data = self._read_json(self.get_settings_path(), {})
        return {
            'roll_volume': data.get('roll_volume', 1.0),
            'cutscene_volume': data.get('cutscene_volume', 1.0),
            'music_volume': data.get('music_volume', 0.5),
            'achievement_volume': data.get('achievement_volume', 1.0),
        }

    def set_roll_volume(self, value):
        self.settings['roll_volume'] = value
        if self.roll_sound:
            self.roll_sound.volume = value
        self.save_settings()

    def set_music_volume(self, value):
        self.settings['music_volume'] = value
        if self.bg_music:
            self.bg_music.volume = value
        self.save_settings()

    def set_achievement_volume(self, value):
        self.settings['achievement_volume'] = value
        if self.achievement_sound:
            self.achievement_sound.volume = value

    def set_cutscene_volume(self, value):
        self.settings['cutscene_volume'] = value
        if self.cutscene_sound:
            self.cutscene_sound.volume = value
        self.save_settings()

    # --- сброс прогресса ---

    def reset_progress(self):
        self.inventory_data = {}
        self.achievements_unlocked = set()
        self.stats = {'total_rolls': 0, 'rare_auras_caught': 0}
        self.save_data()
        self.save_achievements()
        self.save_stats()


if __name__ == '__main__':
    RngGameApp().run()
