FROM python:3.11-slim

RUN useradd -m -u 1000 user

WORKDIR /home/user/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .

USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    MODEL_DIR=/home/user/app/models \
    CORS_ORIGINS="*"

RUN mkdir -p /home/user/app/models

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
