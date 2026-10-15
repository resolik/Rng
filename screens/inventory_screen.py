from kivy.app import App
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from auras import ALL_AURAS_DATA, RARITY_ORDER
from ui_helpers import create_label

# Один слот на всю ширину экрана (в один столбец) — места достаточно, чтобы
# куб и три текстовых сектора не наезжали друг на друга.
SLOT_HEIGHT = 92
SLOT_BG_COLOR = (0.12, 0.12, 0.12, 1)


def _aura_by_name(name):
    for aura in ALL_AURAS_DATA:
        if aura['name'] == name:
            return aura
    return None


class _AuraCube(Widget):
    """
    Квадратик слота. Для пойманных аур — заливка цветом (для двухцветных,
    как Twin Twin, — две смежные половины). Для непойманных — тёмный фон с
    "???" по центру, тем же размером, что и обычный куб.
    """

    def __init__(self, color, secondary_color=None, **kwargs):
        super().__init__(**kwargs)
        self._secondary = secondary_color
        self._caught = color is not None

        with self.canvas:
            if not self._caught:
                Color(0.22, 0.22, 0.22, 1)
                self.rect_left = Rectangle()
                self.rect_right = None
            elif secondary_color is not None:
                Color(*color)
                self.rect_left = Rectangle()
                Color(*secondary_color)
                self.rect_right = Rectangle()
            else:
                Color(*color)
                self.rect_left = Rectangle()
                self.rect_right = None
        self.bind(pos=self._update, size=self._update)

        if not self._caught:
            self._mark = create_label(text="???", font_size='15sp', halign='center', valign='middle')
            self.add_widget(self._mark)
            self.bind(pos=self._update_mark, size=self._update_mark)

    def _update(self, *args):
        if self.rect_right is not None:
            half_w = self.width / 2
            self.rect_left.pos = self.pos
            self.rect_left.size = (half_w, self.height)
            self.rect_right.pos = (self.x + half_w, self.y)
            self.rect_right.size = (half_w, self.height)
        else:
            self.rect_left.pos = self.pos
            self.rect_left.size = self.size

    def _update_mark(self, *args):
        self._mark.pos = self.pos
        self._mark.size = self.size


class _AuraSlot(BoxLayout):
    """
    Один слот хранилища на всю ширину: куб ауры | название | количество |
    поле удаления. Если аура ещё не поймана — первые три сектора "???",
    поле удаления отключено.
    """

    def __init__(self, aura_name, count, on_change, **kwargs):
        super().__init__(orientation='horizontal', size_hint=(1, None), height=SLOT_HEIGHT, spacing=10, padding=10, **kwargs)
        with self.canvas.before:
            Color(*SLOT_BG_COLOR)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.aura_name = aura_name
        self.on_change = on_change
        aura_data = _aura_by_name(aura_name)
        caught = count > 0

        # 1) куб
        cube_color = aura_data['color'] if caught else None
        cube_secondary = aura_data.get('secondary_color') if caught else None
        self.add_widget(_AuraCube(cube_color, cube_secondary, size_hint=(0.2, 1)))

        # 2) название
        name_text = aura_name if caught else "???"
        self.add_widget(create_label(
            text=name_text, font_size='18sp', size_hint=(0.4, 1),
            halign='center', valign='middle', shorten=True,
        ))

        # 3) количество
        count_text = str(count) if caught else "???"
        self.add_widget(create_label(text=count_text, font_size='18sp', size_hint=(0.15, 1), halign='center', valign='middle'))

        # 4) поле "сколько удалить"
        self.delete_input = TextInput(
            hint_text="0", input_filter='int', multiline=False,
            size_hint=(0.25, None), height=50, font_size='16sp',
            disabled=not caught, padding=[10, 12, 10, 12],
        )
        self.delete_input.bind(on_text_validate=self._on_delete_confirm)
        self.add_widget(self.delete_input)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def _on_delete_confirm(self, instance):
        text = self.delete_input.text.strip()
        if not text:
            return
        amount = int(text)
        if amount <= 0:
            return
        app = App.get_running_app()
        app.remove_from_inventory(self.aura_name, amount)
        self.delete_input.text = ""
        if self.on_change:
            self.on_change()


class InventoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Явный чёрный фон экрана, нарисованный сразу в canvas.before —
        # чтобы при переходе сюда не было кадра, где сетка аур уже видна,
        # а фон под ней ещё не закрашен (гонка между контентом и фоном).
        with self.canvas.before:
            Color(0, 0, 0, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        self.scroll = ScrollView(size_hint=(1, 1))
        self.grid = GridLayout(cols=1, size_hint=(1, None), spacing=8)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.scroll.add_widget(self.grid)
        self.layout.add_widget(self.scroll)

        self.layout.add_widget(
            Button(text="НАЗАД", size_hint=(1, 0.1), on_press=lambda x: setattr(self.manager, 'current', 'game'))
        )
        self.add_widget(self.layout)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def on_enter(self):
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        self.grid.clear_widgets()
        for aura_name in RARITY_ORDER:
            count = app.inventory_data.get(aura_name, 0)
            slot = _AuraSlot(aura_name, count, on_change=self.refresh)
            self.grid.add_widget(slot)
