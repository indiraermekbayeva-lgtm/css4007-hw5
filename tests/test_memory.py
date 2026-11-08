import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage
from langgraph.graph.message import add_messages
from typing import TypedDict, Annotated


# Создаем простое состояние для проверки памяти
class MemoryState(TypedDict):
    messages: Annotated[list, add_messages]


# Создаем тестовый узел без OpenAI
def reply_node(state):
    return {"messages": []}


# Создаем тестовый граф
def create_app(connection):
    graph = StateGraph(MemoryState)
    graph.add_node("reply", reply_node)
    graph.add_edge(START, "reply")
    graph.add_edge("reply", END)

    checkpointer = SqliteSaver(connection)
    return graph.compile(checkpointer=checkpointer)


# Проверяем сохранение памяти после повторного открытия базы
def test_memory_after_restart(tmp_path):
    db_path = tmp_path / "memory.db"

    # Запускаем первый экземпляр приложения
    connection = sqlite3.connect(str(db_path), check_same_thread=False)
    app = create_app(connection)

    config = {"configurable": {"thread_id": "test-thread"}}

    app.invoke({
        "messages": [HumanMessage(content="My Wi-Fi does not work.")]
    }, config=config)

    connection.close()

    # Открываем базу снова, как после перезапуска
    connection = sqlite3.connect(str(db_path), check_same_thread=False)
    app = create_app(connection)

    saved = app.get_state(config)
    messages = saved.values["messages"]

    assert any(
        isinstance(message, HumanMessage)
        and message.content == "My Wi-Fi does not work."
        for message in messages
    )

    connection.close()


# Проверяем разделение разговоров
def test_separate_threads(tmp_path):
    db_path = tmp_path / "memory.db"

    connection = sqlite3.connect(str(db_path), check_same_thread=False)
    app = create_app(connection)

    first = {"configurable": {"thread_id": "thread-a"}}
    second = {"configurable": {"thread_id": "thread-b"}}

    app.invoke({
        "messages": [HumanMessage(content="Wi-Fi problem")]
    }, config=first)

    app.invoke({
        "messages": [HumanMessage(content="Password problem")]
    }, config=second)

    first_messages = app.get_state(first).values["messages"]
    second_messages = app.get_state(second).values["messages"]

    assert first_messages[0].content == "Wi-Fi problem"
    assert second_messages[0].content == "Password problem"
    assert len(first_messages) == 1
    assert len(second_messages) == 1

    connection.close()


# Проверяем разделение языковых предпочтений
def test_separate_users(tmp_path):
    db_path = tmp_path / "users.db"

    connection = sqlite3.connect(str(db_path), check_same_thread=False)
    cursor = connection.cursor()

    # Создаем таблицу предпочтений
    cursor.execute("""
        CREATE TABLE user_preferences (
            user_id TEXT PRIMARY KEY,
            language TEXT NOT NULL
        )
    """)

    # Сохраняем предпочтение первого пользователя
    cursor.execute(
        "INSERT INTO user_preferences VALUES (?, ?)",
        ("demo-user-a", "Kazakh")
    )
    connection.commit()

    # Проверяем предпочтения двух пользователей
    cursor.execute(
        "SELECT language FROM user_preferences WHERE user_id = ?",
        ("demo-user-a",)
    )
    user_a = cursor.fetchone()

    cursor.execute(
        "SELECT language FROM user_preferences WHERE user_id = ?",
        ("demo-user-b",)
    )
    user_b = cursor.fetchone()

    assert user_a[0] == "Kazakh"
    assert user_b is None

    connection.close()
