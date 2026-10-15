"""
Чистая логика ролла: собрать пул доступных аур под текущий биом/игровое
время суток и выбрать одну по шансам. Не трогает никакие Kivy-виджеты —
удобно дёргать отдельно (например, для прогона симуляции N роллов и
проверки реальных частот против задуманных).
"""

import random

from auras import AURAS, VOID_AURA, PILLOW_AURA, NIGHTMARE_AURA, LIVER_AURA
from .game_clock import is_game_night

# Ауры, при выпадении которых играется катсцена "ПОГЛОЩЕНИЕ..."
CUTSCENE_AURA_NAMES = [
    "MYTHIC", "LEGENDARY", "Gamma", "Apeiros", "Twin Twin", "Liver", "PILLOW", "NIGHTMARE", "Mellantid",
]

# Ауры без числового шанса — в show_aura_result вместо "1/N" показываем "???"
MYSTERY_CHANCE_NAMES = ["NIGHTMARE", "HEARTBEAT", "Mellantid"]


def build_pool(current_biome):
    """Собирает пул аур для одного ролла с учётом биома и ИГРОВОГО времени
    суток (см. game_clock.py — это не реальные системные часы)."""
    pool = AURAS.copy()

    pillow = PILLOW_AURA.copy()
    pillow['chance'] = 400 if current_biome == "Мир подушек" else 1000
    pool.append(pillow)

    liver = LIVER_AURA.copy()
    liver['chance'] = 4000 if current_biome == "Сердечный" else 7000
    pool.append(liver)

    if current_biome == "Пустота":
        pool.append(VOID_AURA)

    if is_game_night():
        pool.append(NIGHTMARE_AURA)

    return pool


def pick_aura(pool):
    """Выбирает ауру из пула: идём от самой редкой к самой частой (по
    убыванию chance) и на каждой бросаем 1/chance; кто первый выпал — тот
    и ушёл. chance == 0 пропускаем (такие ауры роллом в принципе не берутся)."""
    rolled = pool[0]
    for aura in sorted(pool, key=lambda x: x['chance'], reverse=True):
        if aura['chance'] == 0:
            continue
        if random.randint(1, aura['chance']) == 1:
            rolled = aura
            break
    return rolled


def roll(current_biome):
    """Полный ролл одним вызовом: собрать пул и сразу выбрать ауру.
    Mellantid сюда не входит — она исход секретки HEARTBEAT, см.
    heartbeat.py, а не обычного ролла."""
    pool = build_pool(current_biome)
    return pick_aura(pool)
