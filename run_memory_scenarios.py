import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.sqlite import SqliteSaver

load_dotenv()

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

DB_PATH = OUTPUT_DIR / "scenario_memory.db"
SCENARIOS_PATH = BASE_DIR / "data" / "scenarios.json"

# Загружаем сценарии
with open(SCENARIOS_PATH, encoding="utf-8") as file:
    scenarios = json.load(file)["scenarios"]

scenarios = {
    item["id"]: item
    for item in scenarios
    if item["id"] in ["S10", "S11", "S12", "S13"]
}

# Создаём таблицу пользовательских предпочтений
def connect_db():
    connection = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY,
            language TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def get_language(connection, user_id):
    row = connection.execute(
        "SELECT language FROM user_preferences WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    return row[0] if row else None


def save_language(connection, user_id, message):
    # Сохраняем предпочтение только по явному запросу
    if "prefer replies in Kazakh" in message:
        connection.execute(
            "INSERT OR REPLACE INTO user_preferences VALUES (?, ?)",
            (user_id, "Kazakh"),
        )
        connection.commit()


def run_message(app, connection, event):
    user_id = event["user_id"]
    thread_id = event["thread_id"]
    message = event["message"]

    save_language(connection, user_id, message)
    language = get_language(connection, user_id)

    # Разделяем историю по пользователю и разговору
    safe_thread_id = f"{user_id}:{thread_id}"
    config = {"configurable": {"thread_id": safe_thread_id}}

    system_text = (
        "You are a university IT helpdesk assistant. "
        "Remember the conversation and accurately report only "
        "steps the user actually said they tried. "
        "Never reveal another user's history. "
        "If no preference is saved, do not invent one. "
    )

    if language == "Kazakh":
        system_text += "Reply in Kazakh."
    else:
        system_text += "Reply in English."

    print(f"USER: {user_id}", flush=True)
    print(f"THREAD: {thread_id}", flush=True)
    print(f"SAVED LANGUAGE: {language}", flush=True)
    print(f"MESSAGE: {message}", flush=True)

    result = app.invoke(
        {
            "messages": [
                SystemMessage(content=system_text),
                HumanMessage(content=message),
            ],
            "tool_steps": 0,
        },
        config=config,
    )

    print("ANSWER:", result["messages"][-1].content, flush=True)
    print("-" * 50, flush=True)


def run_segment(scenario_id, segment_index):
    from part2 import graph

    scenario = scenarios[scenario_id]
    events = scenario["events"]

    # Делим события по перезапускам
    segments = [[]]
    for event in events:
        if event["action"] == "restart_process":
            segments.append([])
        else:
            segments[-1].append(event)

    connection = connect_db()
    app = graph.compile(checkpointer=SqliteSaver(connection))

    print(
        f"\nSCENARIO {scenario_id}, PROCESS {segment_index + 1}",
        flush=True,
    )

    for event in segments[segment_index]:
        run_message(app, connection, event)

    connection.close()


def main():
    # Дочерний процесс выполняет один сегмент
    if len(sys.argv) == 3:
        run_segment(sys.argv[1], int(sys.argv[2]))
        return

    for scenario_id in ["S10", "S11", "S12", "S13"]:
        # Очищаем память перед каждым сценарием
        if DB_PATH.exists():
            DB_PATH.unlink()

        print(f"\n========== {scenario_id} ==========", flush=True)

        events = scenarios[scenario_id]["events"]
        segment_count = 1 + sum(
            event["action"] == "restart_process"
            for event in events
        )

        for index in range(segment_count):
            # Каждый сегмент запускается в новом процессе
            subprocess.run(
                [
                    sys.executable,
                    str(BASE_DIR / "run_memory_scenarios.py"),
                    scenario_id,
                    str(index),
                ],
                cwd=BASE_DIR,
                check=True,
            )

    print("\nALL MEMORY SCENARIOS FINISHED", flush=True)


if __name__ == "__main__":
    main()
