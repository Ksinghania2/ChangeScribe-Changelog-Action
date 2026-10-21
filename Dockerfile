FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY changescribe ./changescribe
EXPOSE 8000
# Web UI by default; override with:  docker run ... changescribe generate --repo /repo
ENTRYPOINT ["python", "-m", "changescribe"]
CMD ["serve", "--port", "8000"]
