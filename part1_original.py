import json
from pathlib import Path
from typing import TypedDict
from langgraph.graph import StateGraph, START, END


# Загружаем локальные инструкции службы поддержки
DATA_PATH = Path(__file__).parent / "data" / "helpdesk.json"
with open(DATA_PATH, "r", encoding="utf-8") as file:
    helpdesk_data = json.load(file)


# Определяем состояние графа
class HelpdeskState(TypedDict):
    message: str
    category: str
    reply: str


# Определяем категорию проблемы
def read_request(state):
    message = state["message"].lower()

    # Проверяем, есть ли в сообщении Wi-Fi
    if "wifi" in message or "wi-fi" in message:
        category = "wifi"

    # Проверяем, есть ли в сообщении password
    elif "password" in message:
        category = "password"

    # Если тема другая, выбираем other
    else:
        category = "other"

    return {"category": category}

# Wi-Fi help
def wifi_help(state):
    steps = helpdesk_data["instructions"]["wifi"]["steps"]
    return {"reply": "\n".join(steps)}

# Password help
def password_help(state):
    steps = helpdesk_data["instructions"]["password"]["steps"]
    return {"reply": "\n".join(steps)}

# Other problems
def other_help(state):
    return {
        "reply": "Is your problem about Wi-Fi or password?"
    }

# Выбераем следующий узел
def choose_route(state):
    return state["category"]


# Create the graph
graph = StateGraph(HelpdeskState)

# Add nodes
graph.add_node("read_request", read_request)
graph.add_node("wifi_help", wifi_help)
graph.add_node("password_help", password_help)
graph.add_node("other_help", other_help)

# Start the graph
graph.add_edge(START, "read_request")


# Выбираем следующий узел по категории
graph.add_conditional_edges(
    "read_request",
    choose_route,
    {
        "wifi": "wifi_help",
        "password": "password_help",
        "other": "other_help",
    }
)

# Finish the graph
graph.add_edge("wifi_help", END)
graph.add_edge("password_help", END)
graph.add_edge("other_help", END)

# Compile the graph
app = graph.compile()

# Test the graph

# Создаем четыре сообщения для проверки
messages = [
    "I cannot connect to Wi-Fi.",
    "I forgot my PASSWORD.",
    "My laptop screen is broken.",
    "My Wi-Fi password does not work."
]

# Проверяем путь каждого сообщения
for message in messages:
    print("\nMessage:", message)

    # Показываем название узла и полное состояние
    for mode, data in app.stream({
        "message": message,
        "category": "",
        "reply": ""
    }, stream_mode=["updates", "values"]):
        if mode == "updates":
            print("Node:", list(data.keys())[0])
        else:
            print("State:", data)

    print("--------------------")
