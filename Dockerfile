FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc libpq-dev curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY avatar_independent ./avatar_independent
COPY voice_system ./voice_system
COPY static ./static
COPY main.py .
COPY data ./data
COPY docs ./docs
COPY railway_start.sh .
RUN chmod +x railway_start.sh && mkdir -p logs
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=15s --start-period=120s --retries=5 CMD curl -f http://localhost:8000/health || exit 1
CMD ["./railway_start.sh"]
