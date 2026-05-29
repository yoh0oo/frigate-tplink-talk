FROM python:3.12-slim
WORKDIR /app
COPY rtsp_proxy.py .
EXPOSE 554
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python3 -c "import os,socket; s=socket.create_connection(('127.0.0.1',int(os.getenv('LISTEN_PORT','554'))),3); s.close()"
ENTRYPOINT ["python3", "-u", "rtsp_proxy.py"]
