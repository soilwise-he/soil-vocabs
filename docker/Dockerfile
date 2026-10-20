FROM node:24-bookworm-slim AS viewer-build

WORKDIR /build/viewer
COPY viewer/package.json viewer/package-lock.json viewer/.npmrc ./
RUN npm ci
COPY viewer/ ./
COPY SoilVoc.ttl SoilVoc_augmented.ttl SoilVoc_concepts.csv CITATION.cff LICENSE /build/
RUN npm run build

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the API and its canonical vocabulary.
RUN mkdir api
COPY ./api ./api
COPY ./SoilVoc.ttl .

COPY --from=viewer-build /build/viewer/dist ./site/

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
