import random
import time

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.screenmanager import Screen

from achievements import achievement_image_path
from auras import RARE_TRACKED_NAMES
from screens.overlays import ModalOverlay, SettingsContent, AchievementsContent
from ui_helpers import ICON_ACHIEVEMENTS, ICON_SETTINGS, create_label, AchievementBannerImage

from .game_clock import get_game_time_period
from .heartbeat import HeartbeatMixin
from .particles import ParticleLayer
from .rolling import roll, CUTSCENE_AURA_NAMES, MYSTERY_CHANCE_NAMES

# Путь к фоновой картинке биома "Обычный" (у остальных биомов пока просто
# плоская заливка цветом из change_biome)
BIOME_IMAGES_DIR = 'assets/images/biomes'
BIOME_IMAGES = {
    "Обычный": f"{BIOME_IMAGES_DIR}/common_biome.png",
    "Ветреный": f"{BIOME_IMAGES_DIR}/windy_biome.png",
    "Дождливый": f"{BIOME_IMAGES_DIR}/rainy_biome.png",
    "Мир подушек": f"{BIOME_IMAGES_DIR}/pillow_biome.png",
    "Сердечный": f"{BIOME_IMAGES_DIR}/heart_biome.png",
    "Пустота": f"{BIOME_IMAGES_DIR}/void_biome.png",
}

# Длительность плавного затемнения/высветления фона в катсцене редких аур
CUTSCENE_FADE_SECONDS = 0.4

# КД между роллами — ограничивает фарм спамом по ROLL. Клики при этом
# ВСЕГДА фиксируются в click_history для подсчёта КПС (heartbeat.py), иначе
# секретка HEARTBEAT (которая требует 14+ КПС) станет недостижимой при
# включённом КД: это два независимых слоя поверх одних и тех же нажатий,
# а не одна система.
ROLL_COOLDOWN_SECONDS = 0.4

# Сколько секунд баннер ачивки висит на экране, прежде чем уехать обратно
ACHIEVEMENT_TOAST_HOLD_SECONDS = 2.5

# Ширина кнопок-иконок в углах экрана
CORNER_ICON_SIZE = 76

# Размер обычного куба персонажа и каждого из двух кубов Twin Twin
CHARACTER_SIZE = 160
TWIN_CUBE_SIZE = 130

# Версия, отображаемая мелким текстом под биомом
GAME_VERSION = "v1.1"


def _bind_square(widget, rect):
    """Привязывает Rectangle к pos/size квадратного виджета-куба."""
    widget.bind(
        pos=lambda inst, val: setattr(rect, 'pos', val),
        size=lambda inst, val: setattr(rect, 'size', val),
    )


class GameScreen(HeartbeatMixin, Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_biome = "Обычный"
        self.is_cutscene = False
        self.last_rolled_aura = None
        self.heartbeat_count = 0
        self.god_saved = False
        self.click_history = []
        self.inv_click_history = []
        self.high_cps_start_time = None
        self.last_roll_time = 0

        # Корневой слой: на нём лежит основной интерфейс, а поверх него —
        # кнопки в углах, модальные окна и тост с ачивкой.
        self.root_overlay = FloatLayout()

        # Верхний паддинг увеличен отдельно (CORNER_ICON_SIZE + запас), чтобы
        # header_box (биом + время/версия) гарантированно начинался НИЖЕ
        # кнопок-иконок в углах — те рисуются поверх ui_layout и перекрывают
        # всё, что окажется в их зоне по pos_hint.
        self.ui_layout = BoxLayout(
            orientation='vertical',
            padding=[30, 30 + CORNER_ICON_SIZE + 6, 30, 30],
            spacing=20,
        )
        with self.canvas.before:
            self.bg_window_color = Color(0.15, 0.15, 0.15, 1)
            self.bg_window_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_window_rect, size=self.update_window_rect)

        # Фон биома — картинка на весь экран поверх плоской заливки,
        # source подставляется под текущий self.current_biome (см.
        # BIOME_IMAGES и _sync_biome_visuals). Слой частиц — поверх неё,
        # тоже на весь экран. Оба добавлены в root_overlay РАНЬШЕ ui_layout,
        # чтобы оставаться под основным интерфейсом (z-order = порядок
        # add_widget).
        self.biome_bg_image = Image(
            allow_stretch=True, keep_ratio=False,
            size_hint=(1, 1), opacity=0,
        )
        self.root_overlay.add_widget(self.biome_bg_image)

        self.particle_layer = ParticleLayer(size_hint=(1, 1))
        self.root_overlay.add_widget(self.particle_layer)

        # Биом + строка времени/версии — отдельный плотный блок с
        # ФИКСИРОВАННОЙ высотой впритык к тексту (а не долей от общей
        # высоты), иначе каждый Label центрируется в своей слишком большой
        # коробке и визуально получается зазор, даже если spacing крошечный.
        header_box = BoxLayout(orientation='vertical', size_hint=(1, None), height=74, spacing=2)

        self.biome_label = create_label(text="БИОМ: ОБЫЧНЫЙ", font_size='22sp', markup=True, size_hint=(1, None), height=42)
        header_box.add_widget(self.biome_label)

        # Мелкая строка под биомом: слева период суток (цветной), справа
        # версия игры (белым), у обоих приглушённая прозрачность.
        info_row = BoxLayout(orientation='horizontal', size_hint=(1, None), height=30)
        self.time_label = create_label(
            text="", font_size='13sp', markup=True, halign='left', valign='middle',
            size_hint=(0.5, 1), opacity=0.7,
        )
        self.time_label.bind(size=lambda inst, val: setattr(inst, 'text_size', val))
        self.version_label = create_label(
            text=GAME_VERSION, font_size='13sp', halign='right', valign='middle',
            size_hint=(0.5, 1), opacity=0.7, color=(1, 1, 1, 1),
        )
        self.version_label.bind(size=lambda inst, val: setattr(inst, 'text_size', val))
        info_row.add_widget(self.time_label)
        info_row.add_widget(self.version_label)
        header_box.add_widget(info_row)

        self.ui_layout.add_widget(header_box)

        self.label = create_label(
            text="Нажми [b]ROLL[/b]!", font_size='32sp', markup=True,
            halign='center', valign='middle', size_hint=(1, 0.45)
        )
        self.ui_layout.add_widget(self.label)

        # Ряд с кубом(ами) персонажа: обычно там один self.character,
        # но для двухцветных аур (Twin Twin) туда подставляются два
        # отдельных квадрата self.twin_left/self.twin_right вместо него.
        self.character_row = BoxLayout(
            orientation='horizontal', size_hint=(None, None),
            height=CHARACTER_SIZE, spacing=10, pos_hint={'center_x': 0.5},
        )
        self.character_row.bind(minimum_width=self.character_row.setter('width'))

        self.character = BoxLayout(size_hint=(None, None), size=(CHARACTER_SIZE, CHARACTER_SIZE))
        with self.character.canvas:
            self.bg_color = Color(0.5, 0.5, 0.5, 1)
            self.character_rect = Rectangle(pos=self.character.pos, size=self.character.size)
        _bind_square(self.character, self.character_rect)

        self.twin_left = BoxLayout(size_hint=(None, None), size=(TWIN_CUBE_SIZE, TWIN_CUBE_SIZE))
        with self.twin_left.canvas:
            self.twin_left_color = Color(0.5, 0.5, 0.5, 1)
            self.twin_left_rect = Rectangle(pos=self.twin_left.pos, size=self.twin_left.size)
        _bind_square(self.twin_left, self.twin_left_rect)

        self.twin_right = BoxLayout(size_hint=(None, None), size=(TWIN_CUBE_SIZE, TWIN_CUBE_SIZE))
        with self.twin_right.canvas:
            self.twin_right_color = Color(0.5, 0.5, 0.5, 1)
            self.twin_right_rect = Rectangle(pos=self.twin_right.pos, size=self.twin_right.size)
        _bind_square(self.twin_right, self.twin_right_rect)

        self.character_row.add_widget(self.character)
        self.ui_layout.add_widget(self.character_row)

        self.btns_box = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.15))
        self.roll_btn = Button(text="ROLL", font_size='22sp', on_press=self.roll_aura)
        self.claim_btn = Button(text="ВЗЯТЬ", font_size='22sp', on_press=self.claim_aura)
        self.btns_box.add_widget(self.roll_btn)
        self.btns_box.add_widget(self.claim_btn)
        self.ui_layout.add_widget(self.btns_box)

        self.inv_btn = Button(text="ИНВЕНТАРЬ", size_hint=(1, 0.1), font_size='18sp')
        self.inv_btn.bind(on_press=self.count_inv_click, on_release=self.try_go_to_inventory)
        self.ui_layout.add_widget(self.inv_btn)

        self.root_overlay.add_widget(self.ui_layout)

        # --- Кнопки в углах: ачивки слева, настройки справа ---
        self.achievements_btn = Button(
            size_hint=(None, None), size=(CORNER_ICON_SIZE, CORNER_ICON_SIZE),
            pos_hint={'x': 0.03, 'top': 0.98},
            background_normal=ICON_ACHIEVEMENTS,
            background_down=ICON_ACHIEVEMENTS,
            border=(0, 0, 0, 0),
        )
        self.achievements_btn.bind(on_release=self.open_achievements_window)
        self.root_overlay.add_widget(self.achievements_btn)

        self.settings_btn = Button(
            size_hint=(None, None), size=(CORNER_ICON_SIZE, CORNER_ICON_SIZE),
            pos_hint={'right': 0.97, 'top': 0.98},
            background_normal=ICON_SETTINGS,
            background_down=ICON_SETTINGS,
            border=(0, 0, 0, 0),
        )
        self.settings_btn.bind(on_release=self.open_settings_window)
        self.root_overlay.add_widget(self.settings_btn)

        self.add_widget(self.root_overlay)

        Clock.schedule_interval(self.change_biome, 45)
        Clock.schedule_interval(self.check_cps_logic, 0.1)
        Clock.schedule_interval(self.animate_wind, 0.05)
        # Игровые периоды короткие (2-4 мин), а не реальные часы — проверяем
        # почаще, чтобы смена "Утро -> День" и т.д. ловилась без задержки.
        Clock.schedule_interval(self.update_time_label, 5)
        self.update_time_label()
        self._sync_biome_visuals()

    # --- служебные колбэки отрисовки ---

    def update_window_rect(self, instance, value):
        self.bg_window_rect.pos, self.bg_window_rect.size = instance.pos, instance.size

    def animate_wind(self, dt):
        if self.current_biome == "Ветреный" and not self.is_cutscene:
            self.biome_label.pos_hint = {'center_x': 0.5 + random.uniform(-0.01, 0.01)}

    def update_time_label(self, dt=0):
        period_name, color = get_game_time_period()
        hex_c = "".join(f"{int(c * 255):02x}" for c in color)
        self.time_label.text = f"[color={hex_c}]{period_name}[/color]"

    # --- окна (ачивки / настройки) ---

    def open_achievements_window(self, instance):
        overlay = ModalOverlay(AchievementsContent())
        self.root_overlay.add_widget(overlay)

    def open_settings_window(self, instance):
        overlay = ModalOverlay(SettingsContent(), window_size_hint=(0.85, 0.65))
        self.root_overlay.add_widget(overlay)

    # --- ачивки: разблокировка и всплывающий тост ---

    def unlock_achievement(self, achievement_id):
        app = App.get_running_app()
        if achievement_id in app.achievements_unlocked:
            return
        app.achievements_unlocked.add(achievement_id)
        app.save_achievements()
        self.show_achievement_toast(achievement_id)

    def show_achievement_toast(self, achievement_id):
        app = App.get_running_app()
        if app.achievement_sound:
            app.achievement_sound.play()

        banner_width = self.width * 0.92
        toast = AchievementBannerImage(
            source=achievement_image_path(achievement_id, unlocked=True),
            size_hint=(None, None),
            width=banner_width,
            pos_hint={'center_x': 0.5},
        )
        self.root_overlay.add_widget(toast)

        def start_animation(dt):
            toast.y = self.height
            target_y = self.height - toast.height - 20

            def hide_and_remove(*args):
                anim_out = Animation(y=self.height, duration=0.4, t='in_quad')
                anim_out.bind(on_complete=lambda *a: self.root_overlay.remove_widget(toast))
                anim_out.start(toast)

            anim_in = Animation(y=target_y, duration=0.4, t='out_quad')
            anim_in.bind(on_complete=lambda *a: Clock.schedule_once(hide_and_remove, ACHIEVEMENT_TOAST_HOLD_SECONDS))
            anim_in.start(toast)

        # Ждём кадр, чтобы AchievementBannerImage успела посчитать высоту
        # из реальной текстуры, прежде чем считать позиции для анимации.
        Clock.schedule_once(start_animation, 0)

    # --- секретка через инвентарь (частые клики -> blackout) ---

    def count_inv_click(self, instance):
        now = time.time()
        self.inv_click_history = [t for t in self.inv_click_history if now - t <= 1.0]
        self.inv_click_history.append(now)

    def try_go_to_inventory(self, instance):
        if len(self.inv_click_history) > 5:
            self.inv_click_history = []
            self.manager.current = 'blackout'
        else:
            self.manager.current = 'inventory'

    # --- биомы ---

    def change_biome(self, dt=0):
        if self.is_cutscene:
            return
        self.biome_label.pos_hint = {'center_x': 0.5}
        rand_val = random.randint(1, 40)
        text_col = (1, 1, 1, 1)

        if rand_val == 1:
            self.current_biome, self.bg_window_color.rgb = "Пустота", (1, 1, 1)
            text_col = (0, 0, 0, 1)
        elif rand_val == 2:
            self.current_biome, self.bg_window_color.rgb = "Мир подушек", (0.35, 0.2, 0.1)
        elif 4 <= rand_val <= 7:
            self.current_biome, self.bg_window_color.rgb = "Ветреный", (0.4, 0.45, 0.5)
        else:
            self.current_biome = "Дождливый" if random.choice([True, False]) else "Обычный"
            self.bg_window_color.rgb = (0.1, 0.2, 0.3) if self.current_biome == "Дождливый" else (0.15, 0.15, 0.15)

        # В "Пустоте" фон белый — весь текст принудительно чёрным, иначе
        # сливается; в остальных биомах текст обычный белый.
        self.biome_label.color = text_col
        self.label.color = text_col
        self.biome_label.text = f"БИОМ: {self.current_biome.upper()}"
        self._sync_biome_visuals()

    def _sync_biome_visuals(self):
        """Подставляет картинку текущего биома (или прячет, если для него
        картинки ещё нет) и включает/выключает слой частиц."""
        image_path = BIOME_IMAGES.get(self.current_biome)
        if image_path:
            self.biome_bg_image.source = image_path
            self.biome_bg_image.opacity = 1
        else:
            self.biome_bg_image.opacity = 0

        if self.current_biome == "Ветреный":
            self.particle_layer.set_mode('wind')
        elif self.current_biome == "Дождливый":
            self.particle_layer.set_mode('rain')
        elif self.current_biome == "Сердечный":
            self.particle_layer.set_mode('cells')
        else:
            self.particle_layer.set_mode(None)

    # --- роллы ---

    def roll_aura(self, instance):
        if self.is_cutscene:
            return

        # Клик фиксируем всегда, до любых проверок КД — секретка HEARTBEAT
        # следит за частотой именно физических нажатий, а не за тем, сколько
        # роллов из них реально прошло КД.
        now = time.time()
        self.click_history.append(now)

        if now - self.last_roll_time < ROLL_COOLDOWN_SECONDS:
            return
        self.last_roll_time = now

        self.unlock_achievement("first_roll")

        app = App.get_running_app()
        app.stats['total_rolls'] += 1
        app.save_stats()

        if app.stats['total_rolls'] >= 1000:
            # unlock_achievement сам не делает ничего, если уже получена —
            # так что эта проверка на каждом ролле безопасна и заодно
            # сразу закрывает ачивку тем, у кого уже больше 1000 роллов
            # накопилось до обновления.
            self.unlock_achievement("rolls_1000")

        if app.roll_sound:
            app.roll_sound.play()

        rolled = roll(self.current_biome)

        self.last_rolled_aura = rolled
        if rolled['name'] == "Apeiros":
            self.unlock_achievement("blue_wonder")
        if rolled['name'] in CUTSCENE_AURA_NAMES:
            self.start_cutscene(rolled)
        else:
            self.show_aura_result(rolled)

    def claim_aura(self, instance):
        if not self.last_rolled_aura:
            return
        app = App.get_running_app()
        name = self.last_rolled_aura['name']
        app.inventory_data[name] = app.inventory_data.get(name, 0) + 1
        app.save_data()

        if name in RARE_TRACKED_NAMES:
            app.stats['rare_auras_caught'] += 1
            app.save_stats()

        self.label.text = f"[b]{name}[/b]\nвзята!"

    def show_aura_result(self, aura):
        chance = "???" if aura['name'] in MYSTERY_CHANCE_NAMES else f"1/{aura['chance']}"
        secondary = aura.get('secondary_color')

        self.character_row.clear_widgets()
        if secondary is not None:
            # Двухцветная аура (сейчас только Twin Twin) — два ОТДЕЛЬНЫХ
            # куба рядом (не один квадрат, поделенный пополам), и каждое
            # слово названия красится в цвет своего куба.
            hex_main = "".join(f"{int(c * 255):02x}" for c in aura['color'])
            hex_secondary = "".join(f"{int(c * 255):02x}" for c in secondary)
            words = aura['name'].upper().split(" ")
            first_word = words[0] if words else aura['name'].upper()
            second_word = words[1] if len(words) > 1 else first_word
            name_markup = f"[color={hex_main}][b]{first_word}[/b][/color] [color={hex_secondary}][b]{second_word}[/b][/color]"
            self.twin_left_color.rgb = aura['color']
            self.twin_right_color.rgb = secondary
            self.character_row.add_widget(self.twin_left)
            self.character_row.add_widget(self.twin_right)
        else:
            hex_main = "".join(f"{int(c * 255):02x}" for c in aura['color'])
            name_markup = f"[color={hex_main}][b]{aura['name'].upper()}[/b][/color]"
            self.bg_color.rgb = aura['color']
            self.character_row.add_widget(self.character)

        self.label.text = f"ВЫПАЛО:\n{name_markup}\n[size=20sp]ШАНС: {chance}[/size]"

    def start_cutscene(self, aura):
        self.is_cutscene = True
        self.roll_btn.disabled = self.claim_btn.disabled = True

        app = App.get_running_app()
        if app.cutscene_sound:
            app.cutscene_sound.play()

        self.old_bg = self.bg_window_color.rgb
        Animation.cancel_all(self.bg_window_color)
        Animation(rgb=(0, 0, 0), duration=CUTSCENE_FADE_SECONDS, t='out_quad').start(self.bg_window_color)
        self.character_row.opacity = 0
        # Прячем фон биома и частицы на время катсцены, иначе картинка
        # "Обычного" или частицы Ветреного/Дождливого будут видны поверх
        # чёрного экрана "ПОГЛОЩЕНИЕ..." (они отрисовываются поверх
        # canvas.before, который как раз и гаснет в чёрный).
        self.biome_bg_image.opacity = 0
        self.particle_layer.set_mode(None)
        self.label.text = "[color=ffffff][b]ПОГЛОЩЕНИЕ...[/b][/color]"
        Clock.schedule_once(lambda dt: self.end_cutscene(aura), 1.5)

    def end_cutscene(self, aura):
        Animation.cancel_all(self.bg_window_color)
        Animation(rgb=self.old_bg, duration=CUTSCENE_FADE_SECONDS, t='out_quad').start(self.bg_window_color)
        self.character_row.opacity = 1
        self._sync_biome_visuals()
        self.roll_btn.disabled = self.claim_btn.disabled = False
        self.is_cutscene = False
        self.show_aura_result(aura)
