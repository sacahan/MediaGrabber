# MediaGrabber Agents

This document outlines the various specialized agents used within the MediaGrabber project to assist with different software engineering tasks. Each agent has a specific purpose and set of instructions to ensure efficient and consistent development.

All agents are located in the `.github/agents/` directory.

---

## Project Overview

### What is MediaGrabber?

MediaGrabber is a multi-platform media downloader with web interface and CLI support. It provides unified download capabilities for YouTube, Instagram, Facebook, X/Twitter, and Threads with automatic format conversion and mobile-optimized transcoding.

### Technology Stack

**Backend (Python 3.10+):**
- **Flask 2.0+** - REST API server with CORS and Swagger documentation
- **yt-dlp 2025.0.0+** - Primary download engine for all platforms
- **pytubefix 10.3.5+** - YouTube-specific fallback
- **FFmpeg** - Video transcoding (H.264) and audio extraction
- **Playwright 1.56.0+** - Browser automation for restricted content
- **Click 8.0.0+** - CLI framework
- **Pydantic 2.0.0+** - Data validation
- **pytest 9.0.1+** - Testing framework

**Frontend (TypeScript/JavaScript):**
- **Svelte 5.34.7** - Reactive UI framework
- **Vite 6.3.5** - Build tool and dev server
- **TypeScript 5.6.3** - Type safety
- **Tailwind CSS** - Utility-first CSS with forms plugin
- **Vitest 2.0.5** - Unit testing framework

**Media Processing:**
- **yt-dlp** - Multi-platform video/audio extraction with built-in FFmpeg integration
- **FFmpeg** - H.264 encoding (libx264), audio extraction (AAC), resolution scaling
- **Cookies.txt** - Platform authentication support

### Architecture Overview

```
MediaGrabber/
├── backend/                    # Python Flask REST API
│   ├── app/
│   │   ├── api/               # REST endpoints (downloads.py - 984 LOC)
│   │   ├── services/          # Business logic (~1,500 LOC)
│   │   │   ├── download_service.py      # Download orchestration
│   │   │   ├── transcode_service.py     # FFmpeg transcoding
│   │   │   ├── transcode_queue.py       # Concurrency control
│   │   │   ├── progress_bus.py          # Real-time event publishing
│   │   │   ├── retry_policy.py          # Exponential backoff
│   │   │   ├── remediation.py           # Error remediation
│   │   │   ├── output_manager.py        # File management
│   │   │   └── playlist_packager.py     # ZIP packaging
│   │   ├── models/            # Data models (download_job, progress_state)
│   │   ├── cli/               # CLI interface
│   │   └── utils/             # Settings and configuration
│   ├── cookies/               # Platform-specific authentication
│   ├── logs/                  # Rotating log files (10MB × 5)
│   └── output/                # Download artifacts (24h retention)
│
├── frontend/                  # Svelte 5 SPA
│   └── src/
│       ├── App.svelte        # Main UI (1,163 LOC)
│       └── lib/services/
│           └── downloads.ts   # API client (232 LOC)
│
├── .github/agents/           # Specialized AI agents
├── docs/                      # Documentation
├── scripts/                   # Deployment scripts
└── Dockerfile                # Multi-stage container build
```

### Core Components

**Backend Services:**
- `api/downloads.py` - REST API with 5 endpoints (POST /downloads, GET /downloads/:id, GET /progress, GET /file, GET /docs)
- `services/transcode_service.py` - H.264 Baseline encoding with 9:16 mobile aspect ratio, CRF 22 quality
- `services/progress_bus.py` - Pub/sub pattern for real-time progress updates with TTL-based cleanup
- `services/retry_policy.py` - Intelligent retry with error categorization and exponential backoff
- `models/download_job.py` - Job lifecycle management with status tracking (pending → queued → downloading → transcoding → completed/failed)

**Frontend Features:**
- Platform tabs (YouTube, Instagram, Threads, Facebook, X/Twitter)
- Real-time progress tracking (percent, speed, ETA, queue position)
- Download history with 24h retention (max 50 items, sortable)
- Dark/light theme with auto-switching (18:00-6:00)
- Threads cookie authentication with Netscape format validation

### Key Features

**Platform Support:**
1. **YouTube** - Video (MP4), audio extraction (MP3), playlist support
2. **Instagram** - Reels and posts with optional cookie authentication
3. **Facebook** - Videos and Reels
4. **X/Twitter** - Video downloads
5. **Threads** - Custom HTML parser (yt-dlp doesn't support yet), requires cookies

**Download Capabilities:**
- Format conversion: MP4 (best video + audio merge), MP3 (192kbps audio extraction)
- Cookie-based authentication (Base64 transmission, Netscape cookies.txt format)
- Mandatory transcoding: H.264 Baseline Profile Level 4.0, 9:16 aspect ratio, AAC 160kbps
- Automatic cleanup (24h file retention, 5min progress state TTL)

**Development Features:**
- Swagger UI at `/api/docs` with interactive endpoint testing
- Rotating log files with configurable levels and JSON/text format
- Health check endpoint at `/health`
- Multi-platform Docker build (linux/amd64, linux/arm64)

### Architecture Patterns

- **Service-Oriented Architecture** - Clear separation: API → Services → Models
- **Repository Pattern** - In-memory job storage with thread-safe access (migration to Redis/DB planned)
- **Pub/Sub Pattern** - Progress updates via ProgressBus with TTL cleanup
- **Strategy Pattern** - Pluggable download backends (yt-dlp, pytubefix)
- **Chain of Responsibility** - Transcode profiles (primary → fallback if file too large)
- **Retry Pattern** - Exponential backoff with error classification and remediation suggestions
- **Factory Pattern** - Centralized Flask application configuration
- **Observer Pattern** - Frontend polling for real-time UI updates

---

## Available Agents

### `code-review.agent.md`
**Purpose**: Performs comprehensive code reviews as a senior software engineer. Reviews code for security issues, performance & efficiency, and code quality, providing constructive and actionable feedback.

### `speckit.analyze.agent.md`
**Purpose**: Performs non-destructive cross-artifact consistency and quality analysis across `spec.md`, `plan.md`, and `tasks.md` after task generation. Identifies inconsistencies, duplications, ambiguities, and underspecified items.

### `speckit.checklist.agent.md`
**Purpose**: Generates custom checklists for requirements quality validation. Acts as "unit tests for English" - validating the quality, clarity, and completeness of requirements rather than verifying implementation.

### `speckit.clarify.agent.md`
**Purpose**: Identifies underspecified areas in feature specs by asking up to 5 highly targeted clarification questions and encoding answers back into the spec. Designed to run before `/speckit.plan`.

### `speckit.constitution.agent.md`
**Purpose**: Creates or updates the project constitution (`.specify/memory/constitution.md`) from interactive or provided principle inputs, ensuring all dependent templates stay in sync.

### `speckit.implement.agent.md`
**Purpose**: Executes the implementation plan by processing and executing all tasks defined in `tasks.md`. Validates checklist completion before proceeding with implementation.

### `speckit.plan.agent.md`
**Purpose**: Executes the implementation planning workflow using the plan template to generate design artifacts. Creates technical plans based on feature specifications.

### `speckit.specify.agent.md`
**Purpose**: Creates or updates feature specifications from natural language feature descriptions. Generates branch names and structured spec documents.

### `speckit.tasks.agent.md`
**Purpose**: Generates actionable, dependency-ordered `tasks.md` for features based on available design artifacts (plan.md, spec.md, and optional documents like data-model.md, contracts/, research.md).

### `speckit.taskstoissues.agent.md`
**Purpose**: Converts existing tasks into actionable, dependency-ordered GitHub issues using the GitHub MCP server. Only creates issues for repositories matching the Git remote URL.

## Development Guidelines

### `.github/agents/copilot-instructions.md`
**Purpose**: MediaGrabber-specific development guidelines including active technologies (Python 3.12, Flask, Svelte 5, TypeScript, ffmpeg), project structure, build commands, and code style conventions.

### `.github/copilot-instructions.md`
**Purpose**: General coding guidelines covering indentation, shell tool usage, naming conventions, type exports, and commenting standards. Serves as a reference for overall code style.
