import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from part2 import graph
from langchain_core.messages import HumanMessage

# Подключаемся к сохраненной базе данных
db_path = Path(__file__).parent / "outputs" / "memory.db"
connection = sqlite3.connect(str(db_path), check_same_thread=False)

# Подключаем память к графу
checkpointer = SqliteSaver(connection)
app = graph.compile(checkpointer=checkpointer)

# Открываем тот же разговор
config = {"configurable": {"thread_id": "s10"}}

# Читаем сохраненную историю
saved_state = app.get_state(config)
messages = saved_state.values.get("messages", [])

print("Saved messages:", len(messages))

# Показываем сообщения пользователя
for message in messages:
    if isinstance(message, HumanMessage):
        print("User:", message.content)
# Проверяем, что разговоры хранятся отдельно
new_config = {"configurable": {"thread_id": "s11"}}
new_state = app.get_state(new_config)

old_users = [
    m.content
    for m in new_state.values.get("messages", [])
    if isinstance(m, HumanMessage)
]

print("S11 user messages:", old_users)
print(
    "Old Wi-Fi conversation found:",
    any("My Wi-Fi does not work" in text for text in old_users)
)
connection.close()