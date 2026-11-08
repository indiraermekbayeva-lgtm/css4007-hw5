import sqlite3
from pathlib import Path

# Подключаемся к базе данных
db_path = Path(__file__).parent / "outputs" / "memory.db"
connection = sqlite3.connect(str(db_path))
cursor = connection.cursor()

# Создаем таблицу предпочтений пользователей
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id TEXT PRIMARY KEY,
    language TEXT NOT NULL
)
""")

# Сохраняем язык первого пользователя
cursor.execute("""
INSERT OR REPLACE INTO user_preferences (user_id, language)
VALUES (?, ?)
""", ("demo-user-a", "Kazakh"))

connection.commit()

# Проверяем сохраненный язык
cursor.execute(
    "SELECT language FROM user_preferences WHERE user_id = ?",
    ("demo-user-a",)
)

print("User A language:", cursor.fetchone()[0])

connection.close()