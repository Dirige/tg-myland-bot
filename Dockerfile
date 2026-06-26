FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/data
ENV PYTHONUNBUFFERED=1
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import os; exit(0 if any('bot.py' in c for c in open('/proc/1/cmdline','rb').read().decode('utf-8','ignore').split('\0')) else 1)"
CMD ["python", "bot.py"]
