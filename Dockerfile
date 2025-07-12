# Stage 1: Build the Svelte frontend
FROM node:18-alpine AS builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Create the Python backend
FROM python:3.10-slim
WORKDIR /app

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Install dependencies using pyproject.toml
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir .

COPY backend/ ./
COPY --from=builder /app/frontend/dist ./frontend/dist
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "media_grabber_web:app"]
