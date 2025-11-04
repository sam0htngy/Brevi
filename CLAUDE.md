# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Brevi is a video processing platform that allows users to upload long videos and automatically generates short highlight clips using AI-based analysis. The application is built as a monorepo with a Python FastAPI backend and React TypeScript frontend.

## Architecture

### Monorepo Structure
```
brevi/
├── apps/
│   ├── api/          # Python FastAPI backend
│   └── frontend/     # React TypeScript frontend
```

### Backend (FastAPI)
- **Location**: `brevi/apps/api/`
- **Framework**: FastAPI with Uvicorn server
- **Database**: Supabase (PostgreSQL) for video metadata storage
- **Storage**: Supabase Storage for video files
- **Video Processing**: FFmpeg for video manipulation and analysis
- **Key Files**:
  - `main.py`: FastAPI app with video upload endpoint
  - `storage.py`: Supabase storage configuration
  - `db.py`: Database connection setup

### Frontend (React + TypeScript)
- **Location**: `brevi/apps/frontend/`
- **Framework**: React 19.1.1 with TypeScript
- **Build Tool**: Create React App (react-scripts)
- **Testing**: React Testing Library with Jest

### Video Processing Flow
1. Client uploads video metadata to `/api/video` endpoint
2. Backend generates unique UUID for the video
3. Storage path is created: `videos/{uuid}.{extension}`
4. Video record is inserted into Supabase `videos` table with status "pending"
5. FFmpeg processes the video to generate highlight clips (AI analysis integration)

## Development Commands

### Backend (Python/FastAPI)

**Initial Setup**:
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

**Run the API server**:
```bash
cd brevi/apps/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**API Health Check**:
```bash
curl http://localhost:8000/health
```

### Frontend (React)

**Navigate to frontend directory**:
```bash
cd brevi/apps/frontend
```

**Install dependencies**:
```bash
npm install
```

**Run development server**:
```bash
npm start
# Opens browser at http://localhost:3000
```

**Run tests**:
```bash
npm test
```

**Build for production**:
```bash
npm build
```

**Run specific test file**:
```bash
npm test -- App.test.tsx
```

### Docker

**Build API container**:
```bash
docker build -f brevi/apps/api/dockerfile -t brevi-api .
```

**Run API container**:
```bash
docker run -p 8000:8000 --env-file brevi/.env brevi-api
```

## Environment Configuration

The backend requires environment variables configured in `brevi/.env`:

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

These credentials are used for:
- Database operations (video metadata)
- Storage operations (video file uploads)

## Key Technical Considerations

### Supabase Integration
- The backend uses the Supabase Python client to interact with both the database and storage
- Video records are stored in a `videos` table with fields: `id`, `filename`, `storage_path`, `status`
- Storage paths follow the pattern: `videos/{uuid}.{extension}`

### CORS Configuration
- FastAPI backend includes CORS middleware to allow frontend requests
- Configured in `main.py` for cross-origin communication

### Video File Handling
- The API accepts video metadata (filename) via POST request
- UUIDs are generated server-side to ensure unique storage paths
- File extensions are preserved from the original filename
- FFmpeg is installed in the Docker container for video processing capabilities

### Status Tracking
- Videos are initially created with `"pending"` status
- This allows for asynchronous processing of video uploads
- Status can be updated as the video progresses through the processing pipeline

## FFmpeg Integration
- FFmpeg is installed in the Docker container (see `brevi/apps/api/dockerfile`)
- Used for video analysis and highlight clip generation
- Available for various video manipulation tasks (trimming, format conversion, etc.)
