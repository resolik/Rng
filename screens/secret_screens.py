from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen

from ui_helpers import create_label


class BlackoutScreen(Screen):
    """Секретный экран-пасхалка: открывается частыми кликами по кнопке инвентаря."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 1)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_rect, size=self.update_rect)

    def on_enter(self):
        Clock.schedule_once(self.go_to_questions, 5)

    def go_to_questions(self, dt):
        self.manager.current = 'smart_check'

    def update_rect(self, *args):
        self.rect.pos, self.rect.size = self.pos, self.size


class SmartCheckScreen(Screen):
    """
    Секретный квиз-пасхалка после blackout'а.
    Раньше выдавал ауры Question (G)/(R) — награда убрана,
    экран остался чисто как флэйвор-секретка.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stage = 1
        self.layout = BoxLayout(orientation='vertical', padding=50, spacing=30)
        with self.canvas.before:
            Color(0, 0, 0, 1)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_rect, size=self.update_rect)

        self.q_label = create_label(text="You are too smart?", font_size='32sp')
        self.layout.add_widget(self.q_label)

        self.btn_box = BoxLayout(spacing=20, size_hint=(1, 0.3))
        self.yes_btn = Button(text="Yes", on_press=self.on_yes)
        self.no_btn = Button(text="No", on_press=self.on_no)
        self.btn_box.add_widget(self.yes_btn)
        self.btn_box.add_widget(self.no_btn)
        self.layout.add_widget(self.btn_box)
        self.add_widget(self.layout)

    def on_enter(self):
        self.stage = 1
        self.q_label.text = "You are too smart?"

    def update_rect(self, *args):
        self.rect.pos, self.rect.size = self.pos, self.size

    def on_no(self, instance):
        if self.stage == 1:
            self.manager.current = 'game'
        else:
            self.finish()

    def on_yes(self, instance):
        if self.stage == 1:
            self.stage = 2
            self.q_label.text = "Are you human?"
        else:
            self.finish()

    def finish(self):
        self.manager.current = 'game'
