# VeriField Nexus

> A production-ready field data collection and verification platform for climate projects.

## Overview

VeriField Nexus enables field agents to collect, verify, and report activity data for climate projects including clean cooking, agriculture, and real estate sustainability. The platform uses a Trust Engine to score submissions (0-100) based on GPS consistency, image uniqueness, and submission frequency, with AI-powered anomaly detection to flag suspicious entries.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Flutter Mobile  │────▶│  FastAPI Backend │────▶│    Supabase      │
│  (Android-first) │     │  (REST API)      │     │  (PostgreSQL +   │
│                  │     │                  │     │   Storage)       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              ▲
                              │
                        ┌─────────────────┐
                        │  Next.js Dashboard│
                        │  (Admin Panel)    │
                        └─────────────────┘
```

## Tech Stack

| Component   | Technology              |
|------------|-------------------------|
| Mobile     | Flutter (Dart)          |
| Backend    | FastAPI (Python 3.12)   |
| Database   | PostgreSQL (Supabase)   |
| Storage    | Supabase Storage        |
| Auth       | Supabase Auth           |
| Dashboard  | Next.js + TailwindCSS   |
| Charts     | Recharts                |
| Maps       | Google Maps             |

## Project Structure

```
├── mobile/          # Flutter mobile app
├── backend/         # FastAPI REST API
├── dashboard/       # Next.js admin dashboard
├── docker-compose.yml
└── README.md
```

## Quick Start

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Fill in your Supabase credentials
uvicorn app.main:app --reload --port 8000
```

### Dashboard
```bash
cd dashboard
npm install
cp .env.example .env.local  # Fill in your API URL and keys
npm run dev
```

### Mobile
```bash
cd mobile
flutter pub get
flutter run
```

## Environment Variables

### Backend (.env)
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
JWT_SECRET=your-jwt-secret
```

### Dashboard (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_GOOGLE_MAPS_KEY=your-google-maps-key
```

## License

Proprietary — All rights reserved.
