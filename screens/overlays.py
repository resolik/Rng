"""
Переиспользуемые всплывающие элементы: модальное окно с затемнением фона
(закрывается тапом мимо себя) и содержимое для окон настроек/ачивок.
"""

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.widget import Widget

from achievements import ACHIEVEMENT_IDS, achievement_image_path
from ui_helpers import AchievementBannerImage, create_label

# Тот же тёмно-коричневый, что и фон на баннерах ачивок
ACHIEVEMENTS_BG_COLOR = (0.08, 0.06, 0.04, 1)

# Фон окна настроек
SETTINGS_BG_COLOR = (0.05, 0.05, 0.05, 1)

# Сколько секунд кнопка сброса ждёт повторного нажатия, прежде чем
# "остыть" обратно в исходное состояние
RESET_CONFIRM_WINDOW_SECONDS = 3

# Цвет текста статистики в настройках (не белый, чтобы отличался от лейблов
# громкости)
STATS_TEXT_COLOR = (1, 0.84, 0.2, 1)


class ModalOverlay(FloatLayout):
    """
    Полноэкранная затемнённая подложка с окном по центру.
    Тап в любое место мимо окна закрывает его (убирает себя из родителя).
    """

    def __init__(self, content_widget, window_size_hint=(0.85, 0.75), **kwargs):
        super().__init__(size_hint=(1, 1), **kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 0.65)
            self.backdrop_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_backdrop, size=self._update_backdrop)

        self.window = BoxLayout(size_hint=window_size_hint, pos_hint={'center_x': 0.5, 'center_y': 0.5})
        self.window.add_widget(content_widget)
        self.add_widget(self.window)

    def _update_backdrop(self, *args):
        self.backdrop_rect.pos = self.pos
        self.backdrop_rect.size = self.size

    def on_touch_down(self, touch):
        if self.window.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        if self.parent:
            self.parent.remove_widget(self)
        return True


class _VolumeRow(BoxLayout):
    """Подпись + ползунок громкости на одну звуковую дорожку."""

    def __init__(self, label_text, initial_value, on_change, **kwargs):
        super().__init__(orientation='vertical', size_hint=(1, None), height=70, spacing=4, **kwargs)
        self.add_widget(create_label(text=label_text, font_size='16sp', size_hint=(1, None), height=24))
        slider = Slider(min=0, max=1, value=initial_value, size_hint=(1, None), height=36)
        slider.bind(value=lambda instance, value: on_change(value))
        self.add_widget(slider)


class SettingsContent(BoxLayout):
    """
    Содержимое окна настроек: громкость кликов/музыки/ачивок и сброс
    прогресса (кнопка требует повторного нажатия для подтверждения).
    """

    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=20, spacing=16, **kwargs)
        with self.canvas.before:
            Color(*SETTINGS_BG_COLOR)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        app = App.get_running_app()
        self._reset_armed = False

        self.add_widget(_VolumeRow("ЗВУК РОЛЛОВ", app.settings['roll_volume'], app.set_roll_volume))
        self.add_widget(_VolumeRow("МУЗЫКА", app.settings['music_volume'], app.set_music_volume))
        self.add_widget(_VolumeRow("ЗВУК АЧИВОК", app.settings['achievement_volume'], app.set_achievement_volume))
        self.add_widget(_VolumeRow("ЗВУК КАТСЦЕН", app.settings['cutscene_volume'], app.set_cutscene_volume))

        self.add_widget(create_label(
            text=f"ВСЕГО РОЛЛОВ: {app.stats['total_rolls']}",
            font_size='16sp', size_hint=(1, None), height=28,
            color=STATS_TEXT_COLOR,
        ))

        self.reset_btn = Button(text="СБРОСИТЬ ПРОГРЕСС", size_hint=(1, None), height=56)
        self.reset_btn.bind(on_release=self._on_reset_press)
        self.add_widget(self.reset_btn)

        # Заполнитель, чтобы контент не растягивался на всё окно
        self.add_widget(Widget())

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def _on_reset_press(self, instance):
        if not self._reset_armed:
            self._reset_armed = True
            self.reset_btn.text = "ТОЧНО? ЖМИ ЕЩЁ РАЗ"
            Clock.schedule_once(self._disarm_reset, RESET_CONFIRM_WINDOW_SECONDS)
            return

        App.get_running_app().reset_progress()
        self._reset_armed = False
        self.reset_btn.text = "СБРОШЕНО"

    def _disarm_reset(self, dt):
        if self._reset_armed:
            self._reset_armed = False
            self.reset_btn.text = "СБРОСИТЬ ПРОГРЕСС"


class AchievementsContent(BoxLayout):
    """
    Содержимое окна ачивок: тот же тёмный фон, что и у баннеров,
    со списком ачивок (прокручиваемый — на будущее, когда их станет больше).
    """

    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        with self.canvas.before:
            Color(*ACHIEVEMENTS_BG_COLOR)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        app = App.get_running_app()
        scroll = ScrollView(size_hint=(1, 1))
        items = BoxLayout(orientation='vertical', size_hint=(1, None), spacing=10, padding=10)
        items.bind(minimum_height=items.setter('height'))

        for achievement_id in ACHIEVEMENT_IDS:
            unlocked = achievement_id in app.achievements_unlocked
            img = AchievementBannerImage(
                source=achievement_image_path(achievement_id, unlocked),
                size_hint_x=1,
            )
            items.add_widget(img)

        scroll.add_widget(items)
        self.add_widget(scroll)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
