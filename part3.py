import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

# Создаем папку для хранения памяти
MEMORY_DIR = Path(__file__).parent / "outputs"
MEMORY_DIR.mkdir(exist_ok=True)

# Указываем файл базы данных
DB_PATH = MEMORY_DIR / "memory.db"

# Подключаем SQLite
connection = sqlite3.connect(
    str(DB_PATH),
    check_same_thread=False
)

# Создаем постоянное хранилище разговоров
checkpointer = SqliteSaver(connection)

print("Conversation memory is ready.")
# Используем граф из Part 2
from part2 import graph

# Подключаем постоянную память к графу
app = graph.compile(checkpointer=checkpointer)

print("LangGraph memory is connected.")
from langchain_core.messages import HumanMessage, SystemMessage

# Проверяем память одного разговора
config = {"configurable": {"thread_id": "s10"}}

# Первое сообщение пользователя
result = app.invoke(
    {
        "messages": [
            SystemMessage(content="""
            You are a university IT helpdesk assistant.
            Use previous messages to understand the user's problem.
            Do not invent steps the user has tried.
            """),
            HumanMessage(content="My Wi-Fi does not work. What should I try?")
        ],
        "tool_steps": 0
    },
    config=config
)

print("First answer:")
print(result["messages"][-1].content)

# Второе сообщение в том же разговоре
result = app.invoke(
    {
        "messages": [
            HumanMessage(content="I already tried that.")
        ],
        "tool_steps": 0
    },
    config=config
)

print("\nSecond answer:")
print(result["messages"][-1].content)
# Проверяем сохраненную историю разговора
saved_state = app.get_state(config)

print("\nSaved messages:", len(saved_state.values["messages"]))
print("Last user message:")
print([
    m.content
    for m in saved_state.values["messages"]
    if isinstance(m, HumanMessage)
][-1])