"""
Игровой цикл времени суток — НЕ завязан на реальные системные часы.
Отсчитывается с момента запуска приложения (один раз за процесс) и крутится
по кругу: Утро 2 игр. мин, День 2 игр. мин, Вечер 2 игр. мин, Ночь 4 игр.
мин, затем сначала. Специально отдельно от реального времени, чтобы
игроки не путали "ночь по часам телефона" с игровой ночью, от которой
зависит NIGHTMARE (см. is_game_night()).
"""

import time

MORNING_SECONDS = 120
DAY_SECONDS = 120
EVENING_SECONDS = 120
NIGHT_SECONDS = 240
CYCLE_SECONDS = MORNING_SECONDS + DAY_SECONDS + EVENING_SECONDS + NIGHT_SECONDS

# Момент запуска приложения — точка отсчёта цикла, фиксируется один раз
# при первом импорте модуля.
_START_TIME = time.time()

_PERIODS = [
    ("Утро", MORNING_SECONDS, (1.0, 0.95, 0.6)),    # светло-жёлтый
    ("День", DAY_SECONDS, (1.0, 0.85, 0.0)),        # жёлтый
    ("Вечер", EVENING_SECONDS, (1.0, 0.6, 0.75)),   # розовый
    ("Ночь", NIGHT_SECONDS, (0.15, 0.0, 0.25)),     # как NIGHTMARE
]


def get_game_time_period():
    """Возвращает (название_периода, цвет) текущего ИГРОВОГО времени суток."""
    elapsed = (time.time() - _START_TIME) % CYCLE_SECONDS
    for name, duration, color in _PERIODS:
        if elapsed < duration:
            return name, color
        elapsed -= duration
    return _PERIODS[-1][0], _PERIODS[-1][2]  # сюда в теории не дойдём


def is_game_night():
    """True, если сейчас игровая Ночь (не реальные системные часы)."""
    return get_game_time_period()[0] == "Ночь"


# Секретка Mellantid: окно в несколько секунд сразу после смены
# Ночь -> Утро (т.е. в самом начале нового цикла). Поймать её можно, только
# роллнув ровно в этот момент.
MELLANTID_WINDOW_SECONDS = 3


def is_mellantid_window():
    """True, если сейчас то самое окно на стыке Ночь -> Утро."""
    elapsed = (time.time() - _START_TIME) % CYCLE_SECONDS
    return elapsed < MELLANTID_WINDOW_SECONDS
