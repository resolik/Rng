"""
Данные об аурах: имя, редкость (1 / chance) и цвет (RGB, 0..1).
chance == 0 значит "не выпадает обычным роллом" — выдаётся отдельной логикой
(секретки, HEARTBEAT и т.п.). NIGHTMARE выпадает обычным роллом, но только
в игровую Ночь (см. screens/game_screen/game_clock.py — это НЕ реальные
системные часы). У PILLOW и Liver шанс переопределяется по биому прямо в
screens/game_screen/rolling.py (эти записи — только дефолтные значения/цвет).

"Twin Twin" — двухцветная аура: "color" и "secondary_color" задают цвета
двух отдельных кубов персонажа и двух слов названия на главном экране (в
хранилище показывается как один составной значок, см. inventory_screen.py).
Все остальные ауры одноцветные и просто игнорируют отсутствующий
"secondary_color".
"""

ALL_AURAS_DATA = [
    {"name": "Common", "chance": 2, "color": (0.7, 0.7, 0.7)},
    {"name": "Uncommon", "chance": 5, "color": (0.2, 0.8, 0.2)},
    {"name": "Rare", "chance": 20, "color": (0.2, 0.5, 1.0)},
    {"name": "Epic", "chance": 80, "color": (0.6, 0.2, 0.8)},
    {"name": "Ember", "chance": 400, "color": (1.0, 0.55, 0.15)},  # между Epic и MYTHIC, тёплый оранжевый
    {"name": "MYTHIC", "chance": 1500, "color": (1.0, 0.0, 0.0)},
    {"name": "LEGENDARY", "chance": 2500, "color": (1.0, 0.8, 0.0)},
    {"name": "Gamma", "chance": 5000, "color": (0.85, 0.75, 1.0)},  # реже LEGENDARY, светло-сиреневая
    {"name": "Apeiros", "chance": 10000, "color": (0.6, 0.8, 1.0)},  # реже Gamma, светлее Rare
    {
        "name": "Twin Twin",
        "chance": 6000,  # между Gamma и Apeiros
        "color": (0.95, 0.85, 0.35),           # светло-жёлтый — первый куб / первое "Twin"
        "secondary_color": (0.25, 0.25, 0.25),  # тёмно-серый — второй куб / второе "Twin"
    },
    {"name": "VOID", "chance": 50, "color": (0.5, 0.0, 1.0)},
    {"name": "PILLOW", "chance": 1000, "color": (0.96, 0.94, 0.85)},
    {"name": "NIGHTMARE", "chance": 2500, "color": (0.15, 0.0, 0.25)},  # шанс как у LEGENDARY, только игровой ночью
    {"name": "Liver", "chance": 7000, "color": (0.28, 0.02, 0.08)},  # бордовая, темнее HEARTBEAT; 1/4000 в биоме "Сердечный"
    {"name": "Mellantid", "chance": 0, "color": (1.0, 0.35, 0.65)},  # секретка на стыке игровой Ночи и Утра, см. game_clock.py
    {"name": "HEARTBEAT", "chance": 0, "color": (0.5, 0.0, 0.0)},
]

# Упрощённые ссылки на группы аур (индексы соответствуют списку выше)
AURAS = ALL_AURAS_DATA[:10]           # Common..Twin Twin (постоянный шанс)
VOID_AURA = ALL_AURAS_DATA[10]
PILLOW_AURA = ALL_AURAS_DATA[11]
NIGHTMARE_AURA = ALL_AURAS_DATA[12]
LIVER_AURA = ALL_AURAS_DATA[13]
MELLANTID_AURA = ALL_AURAS_DATA[14]
HEARTBEAT_AURA = ALL_AURAS_DATA[15]

# Ауры редкостью строже 1/1000 (по которым ведётся отдельная статистика в
# playerdata/stats.json) — PILLOW явно включён в список по отдельной просьбе,
# хотя его дефолтный шанс ровно 1/1000, а не строже. Ember (1/400) сюда
# намеренно не входит — он "частая редкая", а не топ-тир.
RARE_TRACKED_NAMES = ["MYTHIC", "LEGENDARY", "Gamma", "Apeiros", "Twin Twin", "Liver", "NIGHTMARE", "PILLOW"]

# Порядок аур по возрастанию редкости для окна хранилища (не строго по
# числу chance — VOID и NIGHTMARE заперты биомом/временем, так что их
# реальная "добываемость" ниже, чем голая цифра шанса намекает; HEARTBEAT
# вообще без числового шанса, это чистая секретка за поведение).
RARITY_ORDER = [
    "Common", "Uncommon", "Rare", "Epic", "VOID", "Ember", "PILLOW", "MYTHIC",
    "LEGENDARY", "NIGHTMARE", "Gamma", "Twin Twin", "Liver", "Apeiros", "Mellantid", "HEARTBEAT",
]
