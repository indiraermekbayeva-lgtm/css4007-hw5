import sqlite3
from pathlib import Path
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from part2 import graph

# Подключаемся к сохраненной базе
db_path = Path(__file__).parent / "outputs" / "memory.db"
connection = sqlite3.connect(str(db_path), check_same_thread=False)

# Подключаем граф к памяти
checkpointer = SqliteSaver(connection)
app = graph.compile(checkpointer=checkpointer)

# Получаем сохраненный язык пользователя
def get_language(user_id):
    cursor = connection.execute(
        "SELECT language FROM user_preferences WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    return result[0] if result else None

# Проверяем двух разных пользователей
users = [
    ("demo-user-a", "s11"),
    ("demo-user-b", "s12")
]

for user_id, thread_id in users:
    language = get_language(user_id)

    print("\nUser:", user_id)
    print("Thread:", thread_id)
    print("Saved language:", language)

    # Применяем сохраненное предпочтение, если оно есть
    instruction = (
        f"Reply in {language}."
        if language
        else "Reply in English."
    )

    # Создаем новый разговор
    result = app.invoke(
        {
            "messages": [
                SystemMessage(content=(
                    "You are a university IT helpdesk assistant. "
                    + instruction
                )),
                HumanMessage(content="Hello! Can you help me?")
            ],
            "tool_steps": 0
        },
        config={"configurable": {"thread_id": thread_id}}
    )

    print("AI Answer:")
    print(result["messages"][-1].content)

connection.close()