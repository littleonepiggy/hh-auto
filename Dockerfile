# Используем официальный Python-образ
FROM python:3.11-slim

# Обновление системы и установка зависимостей
RUN apt-get update && apt-get install -y \
    wget unzip curl gnupg2 \
    chromium-driver chromium \
    && rm -rf /var/lib/apt/lists/*

# Установка переменных окружения
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Установка Python-зависимостей
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта
COPY . .

# Указываем рабочую директорию
WORKDIR /app

# Команда по умолчанию (можно изменить)
ENTRYPOINT ["python", "main.py"]