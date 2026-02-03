FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ bot/
COPY main.py .
COPY tests/ tests/
COPY pytest.ini .

# .env не копируем — передаётся через env_file при запуске
CMD ["python", "-u", "main.py"]
