# MediaGrabber

## Project Overview

This project, MediaGrabber, is a unified web application and CLI for downloading media from various platforms. It consists of a Python Flask backend and a Svelte frontend.

- **Backend:** A Python-based REST API using Flask. It uses `yt-dlp` to handle the downloading of media from **YouTube, Facebook, Instagram, X (Twitter), and Threads**. The backend provides endpoints for fetching metadata, initiating downloads, checking download progress, and transcoding media.
- **Frontend:** A Svelte-based single-page application (SPA) built with Vite and styled with Tailwind CSS. It provides a user-friendly interface for users to paste URLs, manage downloads, and handle cookies for restricted content.
- **Architecture:** The application is designed to be run either in a local development environment (CLI or Web) or as a Docker container for production. The frontend communicates with the backend via a REST API.

## Key Features

- **Multi-Platform Support**: YouTube (Video/Audio), Instagram, Facebook, X (Twitter), and Threads.
- **Advanced Processing**:
  - Mandatory 9:16 vertical transcoding for consistency.
  - Playlist packaging (ZIP download).
- **Authentication**: Cookie support for Threads and other restricted content.
- **Documentation**: Built-in Swagger/OpenAPI documentation at `/api/docs`.

## Building and Running

### Development Mode

To run the application in development mode, you need to run the backend and frontend separately.

**1. Backend (Flask):**

```bash
cd backend
# Install dependencies using uv (recommended) or pip
pip install uv && uv sync
# Run the Flask application module
python -m app.web
```

The backend API will be running on `http://localhost:8080`.
Swagger documentation is available at `http://localhost:8080/api/docs`.

**2. Frontend (Svelte):**

```bash
cd frontend
# Install dependencies
npm install
# Start the development server
npm run dev
```

The frontend will be accessible at `http://localhost:5173`.

### Production Mode (Docker)

For a production-like environment, you can use Docker. The project includes a `Dockerfile` and a deployment script.

```bash
# Build and deploy the Docker container
./scripts/deploy.sh
```

This script will build a multi-platform Docker image and push it to Docker Hub.

## Development Conventions

- **Python:** The Python code follows standard conventions and uses `pre-commit` and `ruff` for linting and formatting.
- **Frontend:** The Svelte code is built with Vite and uses Tailwind CSS for styling.
- **API:** The backend provides a REST API with OpenAPI (Swagger) specifications. The core logic is structured within the `backend/app` package.
