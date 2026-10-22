FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Train the model at build time so the container starts instantly
RUN python -c "from app.categoriser import Categoriser; Categoriser()"
ENV SPENDSENSE_DB=/data/spendsense.db
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
