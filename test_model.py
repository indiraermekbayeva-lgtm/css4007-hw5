import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Загружаем настройки из .env
load_dotenv()

# Получаем название модели
model_name = os.getenv("MODEL_NAME")

# Создаем AI-модель
model = ChatOpenAI(model=model_name)

# Отправляем тестовое сообщение
response = model.invoke("Say hello in one short sentence.")

# Выводим ответ
print(response.content)
