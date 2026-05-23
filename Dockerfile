FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    sox && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py .

EXPOSE 8554 8556

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8556/health')" || exit 1

ENTRYPOINT ["python3", "-u", "rtsp_proxy.py"]
