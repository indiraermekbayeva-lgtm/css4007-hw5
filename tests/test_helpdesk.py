import json
from pathlib import Path

from part1 import app
import part2


# Проверяем правильное определение категории
def test_routing():
    examples = [
        ("I cannot connect to Wi-Fi.", "wifi"),
        ("I forgot my PASSWORD.", "password"),
        ("My laptop screen is broken.", "other"),
        ("My Wi-Fi password does not work.", "clarify"),
    ]

    for message, expected in examples:
        result = app.invoke({
            "message": message,
            "category": "",
            "reply": ""
        })

        assert result["category"] == expected
        assert result["reply"]


# Проверяем поиск инструкций Wi-Fi
def test_find_instructions():
    result = part2.find_instructions.invoke({"topic": "wifi"})

    assert isinstance(result, str)
    assert result
    assert result != "No instructions found for this topic."


# Проверяем поиск инструкций для неизвестной темы
def test_unknown_instructions():
    result = part2.find_instructions.invoke({"topic": "printer"})

    assert result == "No instructions found for this topic."


# Проверяем статус сервиса
def test_check_service_status():
    result = part2.check_service_status.invoke({
        "service": "wifi",
        "profile": "normal"
    })

    assert "Status:" in result


# Проверяем неизвестный профиль
def test_unknown_status_profile():
    result = part2.check_service_status.invoke({
        "service": "wifi",
        "profile": "invalid_profile"
    })

    assert result == "Unknown status profile."


# Проверяем создание заявки без настоящего сервиса
def test_prepare_ticket(tmp_path, monkeypatch):
    # Перенаправляем заявки во временную папку
    monkeypatch.setattr(part2, "__file__", str(tmp_path / "part2.py"))

    result = part2.prepare_ticket.invoke({
        "problem": "Wi-Fi does not work.",
        "steps_tried": ["Enabled Wi-Fi"],
        "category": "wifi",
        "user_id": "demo-user-a",
        "thread_id": "test-thread"
    })

    assert "Ticket draft saved:" in result

    # Проверяем содержимое сохраненного JSON
    tickets = list((tmp_path / "outputs" / "tickets").glob("*.json"))
    assert len(tickets) == 1

    ticket = json.loads(tickets[0].read_text(encoding="utf-8"))

    assert ticket["category"] == "wifi"
    assert ticket["user_id"] == "demo-user-a"
    assert ticket["thread_id"] == "test-thread"
    assert ticket["steps_tried"] == ["Enabled Wi-Fi"]
