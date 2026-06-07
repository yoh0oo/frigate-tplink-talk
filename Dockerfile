FROM python:3.12-slim
WORKDIR /app
COPY rtsp_proxy.py .
EXPOSE 554
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD ["sh", "-c", "kill -0 1"]
ENTRYPOINT ["python3", "-u", "rtsp_proxy.py"]
