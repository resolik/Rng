import os

from kivy.uix.image import Image
from kivy.uix.label import Label

# Ресурсы
FONT_PATH = 'assets/fonts/Neucha.ttf'
SOUND_ROLL = 'assets/sounds/roll.wav'
SOUND_EPIC = 'assets/sounds/epic.wav'
SOUND_ACHIEVEMENT = 'assets/sounds/achivement.mp3'
SOUND_CUTSCENE = 'assets/sounds/cutscene.wav'

ICON_ACHIEVEMENTS = 'assets/images/icons/achievements_icon.png'
ICON_SETTINGS = 'assets/images/icons/settings_icon.png'


def get_font():
    return FONT_PATH if os.path.exists(FONT_PATH) else None


def create_label(**kwargs):
    if 'font_name' not in kwargs:
        kwargs['font_name'] = get_font()
    return Label(**kwargs)


class AchievementBannerImage(Image):
    """
    Картинка баннера ачивки, которая всегда точно занимает всю ширину,
    выданную ей через size_hint_x/width, а высоту пересчитывает из
    РЕАЛЬНОГО соотношения сторон загруженной текстуры — без letterbox-полос
    по бокам и без рассинхрона с шириной окна/фона под ней.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault('allow_stretch', True)
        kwargs.setdefault('keep_ratio', False)
        kwargs.setdefault('size_hint_y', None)
        super().__init__(**kwargs)
        self.bind(width=self._update_height, texture=self._update_height)
        self._update_height()

    def _update_height(self, *args):
        tex_w, tex_h = self.texture_size
        if self.width > 0 and tex_w > 0:
            self.height = self.width * (tex_h / tex_w)
