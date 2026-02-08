FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ bot/
COPY api/ api/
COPY tools/ tools/
COPY plugins/ plugins/
COPY admin/ admin/
COPY main.py .
COPY run_bot_from_settings.py .
COPY tests/ tests/
COPY pytest.ini .

# API + админка (Фазы 1–2). БД: /app/data/settings.db (volume в compose).
ENV DATABASE_URL=sqlite:///./data/settings.db

EXPOSE 8000
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
