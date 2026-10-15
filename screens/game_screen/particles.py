"""
Простые частицы для биомов. Без сторонних библиотек и без отдельного
виджета на каждую частицу — все фигуры живут в одном общем canvas и
двигаются вручную по Clock, это ощутимо дешевле по производительности на
телефоне, чем N виджетов.

Режимы:
  'rain'  — Дождливый, падающие палочки-капли
  'wind'  — Ветреный, летящие вбок палочки с покачиванием
  'cells' — Сердечный, всплывающие вверх круги темнее фона ("эритроциты")
"""

import math
import random

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line
from kivy.uix.widget import Widget

PARTICLE_UPDATE_INTERVAL = 1 / 30  # ~30 обновлений в секунду

PARTICLE_COUNT = 28  # для 'rain' и 'wind'

RAIN_COLOR = (0.6, 0.75, 0.9, 0.8)
RAIN_SPEED_RANGE = (420, 620)   # px/сек вниз
RAIN_LENGTH_RANGE = (14, 26)
RAIN_SLANT = 6                  # лёгкий наклон капель вбок

WIND_COLOR = (0.85, 0.85, 0.9, 0.7)
WIND_SPEED_RANGE = (160, 280)   # px/сек по горизонтали
WIND_LENGTH_RANGE = (18, 34)
WIND_WOBBLE = 6                 # амплитуда покачивания по Y

CELLS_COUNT = 18                # кругов меньше и крупнее — спокойнее на вид
CELLS_COLOR = (0.18, 0.0, 0.0, 0.65)   # темнее фона "Сердечного" (0.3, 0, 0)
CELLS_SPEED_RANGE = (18, 38)    # px/сек вверх — медленно всплывают
CELLS_RADIUS_RANGE = (9, 20)
CELLS_WOBBLE = 10               # амплитуда покачивания по X


class _Particle:
    __slots__ = ('x', 'y', 'speed', 'length', 'phase')

    def __init__(self, x, y, speed, length, phase=0.0):
        self.x = x
        self.y = y
        self.speed = speed
        self.length = length  # для 'cells' это радиус, не длина палочки
        self.phase = phase


class ParticleLayer(Widget):
    """
    Прозрачный слой частиц поверх фона биома.
    set_mode('rain' | 'wind' | 'cells' | None) — None полностью прячет и
    останавливает частицы (используется во время катсцен).
    """

    MODES = ('rain', 'wind', 'cells')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = None
        self._particles = []
        self._shapes = []
        self._update_event = None
        self.bind(pos=self._on_layout_change, size=self._on_layout_change)

    def set_mode(self, mode):
        if mode == self.mode:
            return
        self.mode = mode
        self._rebuild()

    def _on_layout_change(self, *args):
        if self.mode in self.MODES:
            self._rebuild()

    def _count(self):
        return CELLS_COUNT if self.mode == 'cells' else PARTICLE_COUNT

    def _color(self):
        if self.mode == 'rain':
            return RAIN_COLOR
        if self.mode == 'wind':
            return WIND_COLOR
        return CELLS_COLOR

    def _rebuild(self):
        self.canvas.clear()
        self._particles = []
        self._shapes = []

        if self._update_event is not None:
            self._update_event.cancel()
            self._update_event = None

        if self.mode not in self.MODES or self.width <= 0 or self.height <= 0:
            self.opacity = 0
            return

        self.opacity = 1
        with self.canvas:
            Color(*self._color())
            for _ in range(self._count()):
                particle = self._spawn_particle(initial=True)
                self._particles.append(particle)
                if self.mode == 'cells':
                    pos, size = self._ellipse_args(particle)
                    self._shapes.append(Ellipse(pos=pos, size=size))
                else:
                    self._shapes.append(Line(points=self._line_points(particle), width=1.4))

        self._update_event = Clock.schedule_interval(self._update, PARTICLE_UPDATE_INTERVAL)

    def _spawn_particle(self, initial=False):
        if self.mode == 'rain':
            speed = random.uniform(*RAIN_SPEED_RANGE)
            length = random.uniform(*RAIN_LENGTH_RANGE)
            x = random.uniform(0, self.width)
            y = random.uniform(0, self.height) if initial else self.height + length
            return _Particle(x, y, speed, length)

        if self.mode == 'wind':
            speed = random.uniform(*WIND_SPEED_RANGE)
            length = random.uniform(*WIND_LENGTH_RANGE)
            y = random.uniform(0, self.height)
            x = random.uniform(0, self.width) if initial else -length
            phase = random.uniform(0, 2 * math.pi)
            return _Particle(x, y, speed, length, phase)

        # 'cells'
        speed = random.uniform(*CELLS_SPEED_RANGE)
        radius = random.uniform(*CELLS_RADIUS_RANGE)
        x = random.uniform(radius, max(radius, self.width - radius))
        y = random.uniform(0, self.height) if initial else -radius
        phase = random.uniform(0, 2 * math.pi)
        return _Particle(x, y, speed, radius, phase)

    def _line_points(self, particle):
        x, y = self.x + particle.x, self.y + particle.y
        if self.mode == 'rain':
            return [x, y, x - RAIN_SLANT, y - particle.length]
        wobble = WIND_WOBBLE * math.sin(particle.phase)
        return [x, y + wobble, x + particle.length, y + wobble]

    def _ellipse_args(self, particle):
        wobble = CELLS_WOBBLE * math.sin(particle.phase)
        cx = self.x + particle.x + wobble
        cy = self.y + particle.y
        d = particle.length * 2
        return (cx - particle.length, cy - particle.length), (d, d)

    def _update(self, dt):
        if self.mode == 'rain':
            for i, particle in enumerate(self._particles):
                particle.y -= particle.speed * dt
                if particle.y + particle.length < 0:
                    self._particles[i] = particle = self._spawn_particle()
                self._shapes[i].points = self._line_points(particle)
        elif self.mode == 'wind':
            for i, particle in enumerate(self._particles):
                particle.x += particle.speed * dt
                particle.phase += dt * 3
                if particle.x > self.width:
                    self._particles[i] = particle = self._spawn_particle()
                self._shapes[i].points = self._line_points(particle)
        elif self.mode == 'cells':
            for i, particle in enumerate(self._particles):
                particle.y += particle.speed * dt
                particle.phase += dt * 1.5
                if particle.y - particle.length > self.height:
                    self._particles[i] = particle = self._spawn_particle()
                pos, size = self._ellipse_args(particle)
                self._shapes[i].pos = pos
                self._shapes[i].size = size
