"""
Список ачивок. Каждая задаётся id (англ., snake_case) — по нему строятся
пути к готовым картинкам (текст и статус уже зашиты в саму картинку):

assets/images/achievements/{id}_done.png   — получена (та же картинка
                                              используется как баннер
                                              всплывающего уведомления)
assets/images/achievements/{id}_locked.png — не получена
"""

ACHIEVEMENT_IDS = [
    "first_roll",
    "rolls_1000",
    "validol",
    "blue_wonder",
]

ACHIEVEMENTS_DIR = "assets/images/achievements"


def achievement_image_path(achievement_id, unlocked):
    suffix = "done" if unlocked else "locked"
    return f"{ACHIEVEMENTS_DIR}/{achievement_id}_{suffix}.png"
