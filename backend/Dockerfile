FROM python:3.12-slim
WORKDIR /srv
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY scripts/ ./scripts/
ENV PYTHONPATH=/srv/backend
WORKDIR /srv/backend
CMD ["sh", "-c", "python ../scripts/init_db.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
