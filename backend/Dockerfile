FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data output directories
RUN mkdir -p /data/svg_output /data/stl_output

ENV PYTHONPATH=/app
ENV DATA_DIR=/data

EXPOSE 8000

# Run directly (not through main.py) so SIGTERM kills the process correctly
CMD ["uvicorn", "app.api.router:app", "--host", "0.0.0.0", "--port", "8000"]