# Stage 1: Build the Svelte frontend
FROM node:18-alpine AS builder
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install
COPY frontend/ ./
# Create an env file for Vite build so import.meta.env.VITE_API_BASE_URL is available
RUN echo "VITE_API_BASE_URL=${VITE_API_BASE_URL}" > .env.production
RUN npm run build

# Stage 2: Create the Python backend
FROM python:3.12-slim
WORKDIR /app

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Install dependencies using pyproject.toml
COPY ./pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy backend application
COPY backend/ ./backend/

# Copy frontend build
COPY --from=builder /app/frontend/dist ./frontend/dist

# Create directories for logs and output
RUN mkdir -p /app/logs /app/output

# Environment variables
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=8080
ENV MG_OUTPUT_DIR=/app/output
ENV MG_LOG_DIR=/app/logs
ENV MG_MAX_TRANSCODE_WORKERS=2
ENV MG_PROGRESS_TTL_SECONDS=300

EXPOSE 8080

# Set Python path to include backend directory
ENV PYTHONPATH=/app/backend

# Use new application entry point
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--chdir", "/app/backend", "app.web:create_app()"]
