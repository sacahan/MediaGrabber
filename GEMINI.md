# MediaGrabber

## Project Overview

This project, MediaGrabber, is a web application for downloading media from various platforms. It consists of a Python Flask backend and a Svelte frontend.

- **Backend:** A Python-based REST API using Flask. It uses `yt-dlp` to handle the downloading of media from YouTube, Facebook, and Instagram. The backend provides endpoints for fetching metadata, initiating downloads, and checking download progress.

- **Frontend:** A Svelte-based single-page application (SPA) built with Vite and styled with Tailwind CSS. It provides a user-friendly interface for users to paste URLs and download media.

- **Architecture:** The application is designed to be run either in a local development environment or as a Docker container for production. The frontend communicates with the backend via a REST API.

## Building and Running

### Development Mode

To run the application in development mode, you need to run the backend and frontend separately.

**1. Backend (Flask):**

```bash
cd backend
# Install dependencies if you haven't already
pip install -r requirements.txt
# Run the Flask application
python media_grabber_web.py
```

The backend API will be running on `http://localhost:8080`.

**2. Frontend (Svelte):**

```bash
cd frontend
# Install dependencies if you haven't already
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
- **API:** The backend provides a simple REST API for the frontend to consume. The API endpoints are defined in `backend/media_grabber_web.py`.
