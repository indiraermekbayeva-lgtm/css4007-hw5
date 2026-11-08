from typing import TypedDict
from langchain_core.messages import BaseMessage
from typing import Annotated
from langgraph.graph.message import add_messages
import json
import uuid
from pathlib import Path
from langchain_core.tools import tool
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, SystemMessage

# Указываем путь к данным
DATA_DIR = Path(__file__).parent / "data"

# Загружаем статусы сервисов
with open(DATA_DIR / "service_status.json", "r", encoding="utf-8") as file:
    service_data = json.load(file)

# Создаем инструмент для проверки статуса
@tool
def check_service_status(service: str, profile: str = "normal") -> str:
    """Check the status of a fictional university service."""

    # Проверяем, существует ли профиль
    profiles = service_data["profiles"]

    if profile not in profiles:
        return "Unknown status profile."

    # Получаем данные выбранного сервиса
    services = profiles[profile]

    # Приводим название сервиса к нижнему регистру
    service = service.lower().replace("-", "").replace(" ", "")

    # Проверяем, существует ли сервис
    if service not in services:
        return "Unknown service."

    # Возвращаем статус и сообщение
    result = services[service]

    return f"Status: {result['status']}. {result['message']}"

# Загружаем инструкции службы поддержки
with open(DATA_DIR / "helpdesk.json", "r", encoding="utf-8") as file:
    helpdesk_data = json.load(file)

# Создаем инструмент для поиска инструкций
@tool
def find_instructions(topic: str) -> str:
    """Find helpdesk instructions for Wi-Fi or password problems."""

    instructions = helpdesk_data["instructions"]

    topic = topic.lower()

    if "wifi" in topic or "wi-fi" in topic:
        topic = "wifi"
    elif "password" in topic:
        topic = "password"

    if topic not in instructions:
        return "No instructions found for this topic."

    steps = instructions[topic]["steps"]

    return "\n".join(steps)

# Загружаем шаблон заявки
with open(DATA_DIR / "ticket_template.json", "r", encoding="utf-8") as file:
    ticket_template = json.load(file)

# Создаем инструмент для подготовки заявки
@tool
def prepare_ticket(
    problem: str,
    steps_tried: list[str],
    category: str,
    user_id: str = "demo_user",
    thread_id: str = "demo_thread",
    service_status: str = "unknown",
    status_profile: str = "normal"
) -> str:
    """Create and save a local helpdesk ticket draft."""

    # Создаем копию шаблона
    ticket = ticket_template["ticket"].copy()

    # Заполняем поля заявки
    ticket["ticket_id"] = str(uuid.uuid4())[:8]
    ticket["user_id"] = user_id
    ticket["thread_id"] = thread_id
    ticket["category"] = category
    ticket["summary"] = problem
    ticket["steps_tried"] = steps_tried
    ticket["service_status"] = service_status
    ticket["status_profile"] = status_profile
    ticket["reference_ids"] = []

    # Создаем папку для заявок
    tickets_dir = Path(__file__).parent / "outputs" / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)

    # Сохраняем заявку в JSON
    ticket_path = tickets_dir / f"{ticket['ticket_id']}.json"

    with open(ticket_path, "w", encoding="utf-8") as file:
        json.dump(ticket, file, indent=4, ensure_ascii=False)

    return f"Ticket draft saved: {ticket_path}"

# Загружаем настройки из .env
load_dotenv()

# Получаем название AI-модели
model_name = os.getenv("MODEL_NAME")

# Создаем модель без обязательного API-ключа при импорте
if os.getenv("OPENAI_API_KEY"):
    model = ChatOpenAI(model=model_name)
else:
    model = None

# Создаем список наших инструментов
tools = [
    find_instructions,
    check_service_status,
    prepare_ticket
]

# Подключаем инструменты, если модель доступна
model_with_tools = model.bind_tools(tools) if model else None

# Создаем узел для выполнения инструментов
tool_node = ToolNode(tools)

# Определяем состояние AI-помощника
class HelpdeskState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    tool_steps: int

# Ограничиваем количество вызовов инструментов
MAX_TOOL_STEPS = 4

# Получаем ответ AI-модели
def assistant(state):
    # Проверяем, достигнут ли лимит
    if state["tool_steps"] >= MAX_TOOL_STEPS:
        response = model.invoke(state["messages"])
    else:
        response = model_with_tools.invoke(state["messages"])

    # Показываем запросы модели к инструментам
    for call in response.tool_calls:
        print("Model requests:", call["name"])
        print("Arguments:", call["args"])

    return {"messages": [response]}

# Проверяем, нужно ли вызвать инструмент
def choose_next(state):
    last_message = state["messages"][-1]

    if last_message.tool_calls and state["tool_steps"] < MAX_TOOL_STEPS:
        return "tools"

    return "end"


# Выполняем инструменты и считаем их вызовы
def run_tools(state):
    result = tool_node.invoke(state)

    # Считаем количество выполненных вызовов
    steps = state["tool_steps"] + len(state["messages"][-1].tool_calls)

    # Показываем результаты инструментов
    for message in result["messages"]:
        print("Tool result:", message.content)

    return {
        "messages": result["messages"],
        "tool_steps": steps
    }


# Создаем граф
graph = StateGraph(HelpdeskState)

# Добавляем узлы
graph.add_node("assistant", assistant)
graph.add_node("tools", run_tools)

# Определяем начало графа
graph.add_edge(START, "assistant")

# Выбираем следующий узел
graph.add_conditional_edges(
    "assistant",
    choose_next,
    {
        "tools": "tools",
        "end": END
    }
)

# Возвращаем результат инструментов модели
graph.add_edge("tools", "assistant")

# Компилируем граф
app = graph.compile()

# Проверяем инструмент
if __name__ == "__main__":
    print(check_service_status.invoke({
        "service": "wifi",
        "profile": "wifi_outage"
    }))
    # Проверяем поиск инструкций
    print("\nInstructions:")
    print(find_instructions.invoke({"topic": "wifi"}))

    # Проверяем создание заявки
    print("\nTicket:")
    print(prepare_ticket.invoke({
        "problem": "Wi-Fi still does not work.",
        "steps_tried": ["Restarted Wi-Fi", "Forgot the network"],
        "category": "wifi",
        "service_status": "operational",
        "status_profile": "normal"
    }))
    # Проверяем два сообщения в одном разговоре
    print("\nSCENARIO S06")

    messages = [
        SystemMessage(content="""
        You are a university IT helpdesk assistant.
        Use the available tools.
        First, find Wi-Fi instructions.
        Then check the Wi-Fi service status.
        If the service is operational, prepare a ticket.
        Use only the steps provided by the user.
        If there is an outage, do not create a ticket.
        Tickets are local drafts only.
        """)
    ]

    # Первое сообщение
    messages.append(
        HumanMessage(content="Show me the Wi-Fi troubleshooting steps.")
    )

    result = app.invoke({
        "messages": messages,
        "tool_steps": 0
    })

    messages = result["messages"]

    print("First answer:")
    print(messages[-1].content)

    # Второе сообщение в том же разговоре
    messages.append(
        HumanMessage(content=(
            "I enabled Wi-Fi and forgot the saved network, "
            "but Campus-Demo still will not connect. "
            "Check whether Wi-Fi is down. "
            "If it is operating, prepare a ticket about this problem."
        ))
    )

    result = app.invoke({
        "messages": messages,
        "tool_steps": 0
    })

    messages = result["messages"]

    print("Second answer:")
    print(messages[-1].content)
    print("--------------------")

    # Проверяем четыре сценария работы AI-помощника
    scenarios = [
        {
            "profile": "normal",
            "service": "wifi",
            "message": "I enabled Wi-Fi and forgot the saved network, "
                    "but Campus-Demo still will not connect. "
                    "Check whether Wi-Fi is down. "
                    "If it is operating, prepare a ticket about this problem."
        },
        {
            "profile": "wifi_outage",
            "service": "wifi",
            "message": "I enabled Wi-Fi and forgot the saved network, "
                    "but Campus-Demo still will not connect. "
                    "Check whether Wi-Fi is down. "
                    "If it is operating, prepare a ticket about this problem."
        },
        {
            "profile": "status_unavailable",
            "service": "wifi",
            "message": "Check whether Wi-Fi is down. "
                    "If it is operating, prepare a ticket. "
                    "I already enabled Wi-Fi and reconnected, with no success."
        },
        {
            "profile": "recovery_outage",
            "service": "account_recovery",
            "message": "My password recovery page is unavailable. "
                    "Check the service status. Is there a known problem?"
        }
    ]

    for scenario in scenarios:
        profile = scenario["profile"]
        service = scenario["service"]

        print("\nPROFILE:", profile)

        result = app.invoke(
            {
                "messages": [
                    SystemMessage(
                        content=f"""
                        You are a university IT helpdesk assistant.
                        Check the status of {service}
                        using profile: {profile}.

                        If there is an outage, explain it.
                        Do not create a ticket.

                        If the service is operational,
                        check the instructions and prepare a ticket
                        using the user's information.

                        If status is unknown,
                        ask permission before preparing a ticket.

                        Never invent information.
                        Tickets are local drafts only.
                        """
                    ),
                    HumanMessage(content=scenario["message"])
                ],
                "tool_steps": 0
            },
            config={"recursion_limit": 15}
        )

        print("AI Answer:")
        print(result["messages"][-1].content)
        print("--------------------")
    # Проверяем сценарий S09
    print("\nSCENARIO S09")

    messages = [
        SystemMessage(content="""
        You are a university IT helpdesk assistant.
        Use tools when needed.
        Before creating a ticket, ask for the problem
        and the steps already tried if they are missing.
        Do not invent information.
        Tickets are local drafts only.
        Never add troubleshooting steps that the user
        did not explicitly say they completed.
        Instructions are suggestions, not completed actions.
        """),
        HumanMessage(content="Prepare a support ticket.")
    ]

    # Проверяем первое сообщение
    result = app.invoke({
        "messages": messages,
        "tool_steps": 0
    })

    print("First answer:", result["messages"][-1].content)

    # Добавляем ответ пользователя в тот же разговор
    messages = result["messages"]
    messages.append(HumanMessage(content=(
        "The issue is Wi-Fi. I enabled it and tried "
        "reconnecting, but it still fails."
    )))

    # Проверяем второе сообщение
    result = app.invoke({
        "messages": messages,
        "tool_steps": 0
    })

    print("Second answer:", result["messages"][-1].content)