FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files (since main.py is in root)
RUN mkdir api
COPY ./api ./api
COPY ./SoilVoc.ttl .

RUN mkdir site
COPY ./index.html ./site/
COPY ./assets ./site/assets

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]