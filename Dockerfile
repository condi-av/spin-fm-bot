FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .   # <-- должен быть ДО pip install
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-u", "bot/main.py"]
