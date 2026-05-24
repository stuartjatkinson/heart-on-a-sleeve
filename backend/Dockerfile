FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data output directories
RUN mkdir -p /data/svg_output /data/stl_output

ENV PYTHONPATH=/app
ENV DATA_DIR=/data

EXPOSE 8080

# PORT is injected by Cloud Run (default 8080); fall back to 8000 for local use
ENV PORT=8080
CMD ["sh", "-c", "uvicorn app.api.router:app --host 0.0.0.0 --port ${PORT}"]