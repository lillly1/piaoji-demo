FROM unclecode/crawl4ai:0.8.6

WORKDIR /app
USER root
RUN pip install --no-cache-dir fastapi==0.116.1 uvicorn[standard]==0.35.0
COPY backend /app/backend
COPY index.html /app/index.html

ENV PYTHONUNBUFFERED=1
EXPOSE 10000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
