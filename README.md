# CardFlow

> **AI-Powered Business Card Digitization & Voice Notes Orchestrator**

CardFlow transforms the friction of manual contact entry into a two-second tap. Point your phone at a business card, speak a quick note, and the contact is automatically extracted, deduplicated, enriched with company metadata, logged to Google Sheets, and your manager is notified on WhatsApp — all in a single conversational interaction.

---

## Table of Contents

1. [Problem Statement](#-problem-statement)
2. [Key Features](#-key-features)
3. [Architecture Overview](#-architecture-overview)
4. [LangGraph Workflow](#-langgraph-workflow)
5. [Tech Stack](#-tech-stack)
6. [Environment Variables](#-environment-variables)
7. [Local Setup Guide](#-local-setup-guide)
8. [Docker Setup](#-docker-setup)
9. [Testing Guide](#-testing-guide)
10. [API Reference](#-api-reference)
11. [Demo Scenarios](#-demo-scenarios)
12. [Deployment Notes](#-deployment-notes)

---

## 🎯 Problem Statement

Sales teams and field representatives collect dozens of business cards daily at conferences and client meetings. The traditional workflow — photograph, type manually into a CRM, remember to notify the manager — is slow, error-prone, and breaks under volume.

**CardFlow solves this entirely.** It provides an intelligent chat interface where:
- A card photo is OCR-processed by Gemini Vision in under 3 seconds.
- Extracted fields are presented for human confirmation (HITL) before any write occurs.
- Duplicate contacts are caught before hitting Google Sheets.
- Company websites and LinkedIn profiles are auto-discovered via enrichment.
- Managers receive a WhatsApp Business API notification the instant a new lead is logged.
- Voice notes can be attached to any contact — transcribed by Gemini Audio and stored persistently.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| **Gemini OCR** | Extracts Name, Phone, Email, Company from any business card image |
| **Human-in-the-Loop Confirmation** | LangGraph `interrupt()` pauses the graph; the user edits & confirms before any write |
| **Duplicate Detection** | Fuzzy match on phone + email against all rows in Google Sheets |
| **Google Sheets CRM** | Auto-appends confirmed contacts with Session ID, timestamps, and audio links |
| **Company Enrichment** | Gemini discovers company website and LinkedIn URL, updates the sheet row |
| **WhatsApp Notifications** | Manager receives a real-time WhatsApp Business API alert per new contact |
| **Voice Notes** | Record audio against an active contact; Gemini transcribes and stores it permanently |
| **Persistent Audio Storage** | Supabase Storage → Cloudinary → Local fallback, with public URLs embedded in the sheet |
| **Session Management** | MongoDB-backed sessions with full chat history replay |
| **Health Summary API** | `/api/health/summary` reports per-feature configuration status without leaking secrets |

---

## 🏗 Architecture Overview

```
┌──────────────────────────────────────────────┐
│                React Frontend                │
│  ChatWindow · ConfirmationCard · Sidebar     │
│  Vite + Tailwind · Toast category system     │
└───────────────────┬──────────────────────────┘
                    │ REST / multipart form
┌───────────────────▼──────────────────────────┐
│              FastAPI Backend                 │
│  /api/sessions/{id}/messages  (POST)         │
│  /api/sessions/{id}/confirm   (POST)         │
│  /api/sessions/{id}/messages  (GET)          │
│  /uploads/*                   (static)       │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│         LangGraph Agent (StateGraph)         │
│  Nodes: extract_card · request_confirmation  │
│         check_duplicate · handle_duplicate   │
│         write_to_sheet · enrich_company      │
│         notify_whatsapp · transcribe_audio   │
│         process_text · handle_extraction_err │
│  Checkpointer: MongoDB (langgraph-checkpoint)│
└──┬────────┬────────┬───────────┬─────────────┘
   │        │        │           │
   ▼        ▼        ▼           ▼
Gemini   Google   WhatsApp   Supabase /
Vision   Sheets   Cloud API  Cloudinary
Audio    (gsheets)(Meta API) Storage
Enrichmt
```

### Component Responsibilities

| Component | Technology | Role |
|---|---|---|
| **Frontend** | React 18, Vite, Tailwind | Conversational chat UI, card confirmation flow |
| **Backend** | FastAPI, Uvicorn | REST API, multipart file handling, response orchestration |
| **Agent Workflow** | LangGraph `StateGraph` | Directed graph with conditional routing and HITL interrupt |
| **State Persistence** | MongoDB + `langgraph-checkpoint-mongodb` | Per-session graph checkpoint and replay |
| **OCR** | Google Gemini 2.5 Flash (multimodal) | Business card text extraction from images |
| **Audio Transcription** | Google Gemini Audio | Voice note transcription to text |
| **Company Enrichment** | Google Gemini | Discovers company website & LinkedIn URL |
| **CRM Storage** | Google Sheets API v4 | Append, update, and deduplicate contact rows |
| **Notifications** | WhatsApp Cloud API (Meta) | Real-time manager alerts on new contact saves |
| **Audio Storage** | Supabase Storage / Cloudinary / Local | Persistent public audio URLs linked in the sheet |

---

## 🔄 LangGraph Workflow

### Workflow Diagram

```mermaid
flowchart TD
    START([START]) --> route_input{route_input}

    route_input -->|image| extract_card
    route_input -->|audio| transcribe_audio
    route_input -->|text| process_text

    extract_card --> route_after_extraction{extraction valid?}
    route_after_extraction -->|yes| request_confirmation
    route_after_extraction -->|no| handle_extraction_error

    handle_extraction_error --> END_ERR([END])

    request_confirmation -->|HITL interrupt ⏸| check_duplicate

    check_duplicate --> route_dedup{is_duplicate?}
    route_dedup -->|yes| handle_duplicate
    route_dedup -->|no| write_to_sheet

    handle_duplicate --> END_DUP([END])

    write_to_sheet --> enrich_company
    enrich_company --> notify_whatsapp
    notify_whatsapp --> END_OK([END])

    transcribe_audio --> END_AUDIO([END])
    process_text --> END_TEXT([END])
```

### Node-by-Node Explanation

| Node | Trigger | Action |
|---|---|---|
| `extract_card` | Image uploaded | Gemini Vision extracts JSON `{name, phone, email, company}` from card image; saves image thumbnail to `uploads/` |
| `handle_extraction_error` | OCR fails or returns all-empty fields | Returns user-friendly error message (quota / unavailable / unclear card) |
| `request_confirmation` | Valid extraction | LangGraph `interrupt()` pauses the graph and surfaces extracted data to the frontend for editing |
| `check_duplicate` | User confirms card | Fetches all rows from Google Sheets; fuzzy-matches on phone and email |
| `handle_duplicate` | Duplicate detected | Returns warning message with matched contact name; graph terminates without writing |
| `write_to_sheet` | No duplicate | Appends new row to Google Sheets with contact fields + Session ID |
| `enrich_company` | After sheet write | Calls Gemini to discover website and LinkedIn URL for the company; updates the sheet row |
| `notify_whatsapp` | After enrichment | Sends WhatsApp Business API message to manager's phone number |
| `transcribe_audio` | Audio uploaded | Transcribes voice note via Gemini Audio; links audio URL and transcript to the active contact row |
| `process_text` | Text message received | Generates a contextual Gemini response based on the current session's saved contact |

---

## 🛠 Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Frontend Framework | React | 18 |
| Build Tool | Vite | Latest |
| Styling | Tailwind CSS | 3 |
| Backend Framework | FastAPI | 0.138.0 |
| ASGI Server | Uvicorn | 0.49.0 |
| Agent Orchestration | LangGraph | 1.2.6 |
| LLM Integration | LangChain / LangChain-Google-GenAI | 1.3.10 / 4.2.5 |
| AI Model | Google Gemini 2.5 Flash | — |
| State Persistence | MongoDB + langgraph-checkpoint-mongodb | 0.4.0 |
| CRM | Google Sheets API v4 | — |
| Notifications | WhatsApp Cloud API (Meta) | — |
| Audio Storage | Supabase / Cloudinary / Local | — |
| Containerization | Docker + Docker Compose | — |
| Testing | pytest + pytest-asyncio | — |

---

## 🔑 Environment Variables

Copy `.env.example` to `.env` and populate the values below.

### Backend (`backend/.env` or root `.env`)

| Variable | Required | Description | Example |
|---|---|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | **Required** | Path to Google service account JSON file | `./service-account.json` |
| `GOOGLE_SHEET_ID` | **Required** | Google Sheets spreadsheet ID (from URL) | `1BxiMVs0XRA5nFMd...` |
| `MONGO_URI` | **Required** | MongoDB connection string (Atlas or local) | `mongodb+srv://user:pass@cluster.mongodb.net/cardflow` |
| `GEMINI_API_KEY` | **Required** | Master Gemini API key (used as fallback for all features) | `AIza...` |
| `GEMINI_OCR_KEY` | Optional | Dedicated Gemini key for OCR (avoids rate limit sharing) | `AIza...` |
| `GEMINI_AUDIO_KEY` | Optional | Dedicated Gemini key for audio transcription | `AIza...` |
| `GEMINI_ENRICHMENT_KEY` | Optional | Dedicated Gemini key for company enrichment | `AIza...` |
| `WHATSAPP_TOKEN` | Optional | WhatsApp Cloud API Bearer token (Meta) | `EAAGm0...` |
| `WHATSAPP_PHONE_NUMBER_ID` | Optional | WhatsApp sender Phone Number ID | `107170...` |
| `MANAGER_PHONE_NUMBER` | Optional | Recipient phone in E.164 format | `91XXXXXXXXXX` |
| `CORS_ALLOWED_ORIGINS` | Optional | Comma-separated allowed CORS origins | `http://localhost:5173,https://yourdomain.com` |
| `PUBLIC_BASE_URL` | Optional* | Public base URL of your backend deployment | `https://api.yourdomain.com` |
| `ENV` | Optional | `development` or `production` | `development` |
| `SUPABASE_URL` | Optional | Supabase project URL for audio storage | `https://xxx.supabase.co` |
| `SUPABASE_KEY` | Optional | Supabase service role key | `eyJ...` |
| `SUPABASE_BUCKET` | Optional | Supabase Storage bucket name | `cardflow` |
| `CLOUDINARY_CLOUD_NAME` | Optional | Cloudinary cloud name (fallback audio storage) | `dxxxxxx` |
| `CLOUDINARY_UPLOAD_PRESET` | Optional | Cloudinary unsigned upload preset | `cardflow_audio` |

> **\*** `PUBLIC_BASE_URL` is required in production (`ENV=production`). Localhost values are blocked in production to ensure audio URLs are accessible to external reviewers.

### Frontend (`frontend/.env`)

| Variable | Required | Description | Example |
|---|---|---|---|
| `VITE_API_BASE_URL` | **Required** | Base URL for the FastAPI backend | `http://localhost:8000/api` |

---

## 🚀 Local Setup Guide

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB Atlas cluster (or local MongoDB instance)
- Google Cloud project with Sheets API enabled and a service account JSON
- Gemini API key from [Google AI Studio](https://aistudio.google.com)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/CardFlow.git
cd CardFlow
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# From the project root
cp .env.example .env
```

Open `.env` and fill in all required fields (see [Environment Variables](#-environment-variables)).

Place your Google service account JSON at the path specified in `GOOGLE_APPLICATION_CREDENTIALS` (default: `./service-account.json`).

### 4. Google Sheet Setup

Your Google Sheet must have the following column headers in row 1:

```
Name | Phone | Email | Company | Session ID | Date Added | Audio URL | Audio Notes | Website | LinkedIn
```

Share the sheet with the service account email (found in `service-account.json` under `client_email`) with **Editor** access.

### 5. Start the Backend

```bash
# From the backend/ directory
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at `http://localhost:8000`.  
Swagger docs: `http://localhost:8000/docs`

### 6. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create frontend env file
echo "VITE_API_BASE_URL=http://localhost:8000/api" > .env
```

### 7. Start the Frontend

```bash
npm run dev
```

Frontend will be available at `http://localhost:5173`.

---

## 🐳 Docker Setup

```bash
# From the project root (requires .env to be populated)
docker-compose up --build
```

Services:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

---

## 🧪 Testing Guide

### Run All Tests

```bash
cd backend
python -m pytest tests/ -v
```

### Run Specific Test Suites

```bash
# Core agent node unit tests
python -m pytest tests/test_nodes.py -v

# Toast & duplicate flow integration tests
python -m pytest tests/test_toast_integration.py -v

# Full audit scenario tests (success / duplicate / WhatsApp failure paths)
python -m pytest tests/test_audit_scenarios.py -v

# Audio transcription tests
python -m pytest tests/test_audio.py -v

# Storage service tests
python -m pytest tests/test_storage.py -v

# Audio URL validation tests
python -m pytest tests/test_urls.py -v
```

### Expected Output

All tests mock external services (Gemini, Google Sheets, WhatsApp, MongoDB) and run entirely offline.

```
============================= test session starts ==============================
collected 28 items

tests/test_nodes.py ............                                         [ 42%]
tests/test_toast_integration.py .....                                    [ 60%]
tests/test_audit_scenarios.py ......                                     [ 81%]
tests/test_audio.py ..                                                   [ 88%]
tests/test_storage.py ...                                                [100%]

============================== 28 passed in 1.23s ==============================
```

### What Is Tested

| Test File | Coverage |
|---|---|
| `test_nodes.py` | `extract_card`, `check_duplicate`, `handle_duplicate`, `write_to_sheet`, `notify_whatsapp` node logic |
| `test_toast_integration.py` | `make_response_payload()` duplicate guardrails; saved→duplicate sequence produces no success flags |
| `test_audit_scenarios.py` | Success path, duplicate path, WhatsApp failure path — all status flags asserted |
| `test_audio.py` | Transcription success and failure paths, row linking, session ID resolution |
| `test_storage.py` | Supabase, Cloudinary, and local fallback upload paths |
| `test_urls.py` | `get_validated_public_audio_url()` — blocks localhost in production, allows in development |

---

## 📡 API Reference

### `POST /api/sessions/{session_id}/messages`
Upload a business card image, voice note, or text message.

**Form Fields:**
- `text` (string, optional) — freeform text message
- `image` (file, optional) — business card image (JPEG, PNG, WebP, GIF)
- `audio` (file, optional) — voice note (WAV, MP3, M4A)

**Response:**
```json
{
  "success": true,
  "action": "ocr",
  "status": "success",
  "message": "I extracted the following contact info...",
  "awaiting_confirmation": true,
  "raw_extraction": { "name": "...", "phone": "...", "email": "...", "company": "..." },
  "details": {
    "duplicate_found": false,
    "saved_to_sheet": false,
    "whatsapp_sent": false,
    "enrichment_completed": false,
    "transcription_completed": false
  }
}
```

### `POST /api/sessions/{session_id}/confirm`
Resume the graph with the user-confirmed contact fields.

**Body:**
```json
{ "name": "Alice Johnson", "phone": "+1 555 0199", "email": "alice@example.com", "company": "Acme Corp" }
```

**Response actions:** `sheet_write` (success) | `duplicate_check` (duplicate found)

### `GET /api/sessions/{session_id}/messages`
Retrieve full chat history for a session.

### `GET /api/sessions`
List all sessions with labels and last message previews.

### `GET /api/health/summary`
Returns per-feature readiness flags without exposing secrets.

```json
{
  "ocr": true,
  "audio": true,
  "enrichment": true,
  "google_sheets": true,
  "whatsapp": false,
  "storage": true
}
```

---

## 🎬 Demo Scenarios

### Scenario 1 — Happy Path (New Contact)
1. Open the app and create a new session.
2. Upload a business card image.
3. Review and confirm the auto-extracted contact fields.
4. Observe: Google Sheets row appended, company enrichment updated, WhatsApp notification sent.
5. Upload a voice note to attach a memo.
6. Observe: Audio transcribed and linked to the contact in the sheet.

### Scenario 2 — Duplicate Detection
1. Upload the same card a second time.
2. Confirm the fields.
3. Observe: "Duplicate found! Contact already exists: [Name]" — no sheet write occurs, no WhatsApp sent.

### Scenario 3 — OCR Failure Recovery
1. Upload a heavily blurred or blank image.
2. Observe: Graceful error message — "Could not extract contact details. Try a clearer image."
3. No incomplete data reaches the sheet.

### Scenario 4 — WhatsApp Failure (Graceful Degradation)
1. Remove `WHATSAPP_TOKEN` from `.env` and restart.
2. Upload and confirm a contact.
3. Observe: Contact is saved to Google Sheets. Chat message reads "Contact saved successfully. Manager notification could not be delivered at this time." — no false success claim.

---

## 🚢 Deployment Notes

- Set `ENV=production` to enable production-mode validations.
- `PUBLIC_BASE_URL` must be set to a publicly reachable HTTPS URL in production (localhost is blocked).
- Use separate Gemini API keys (`GEMINI_OCR_KEY`, `GEMINI_AUDIO_KEY`, `GEMINI_ENRICHMENT_KEY`) to stay within the free tier's per-project rate limits.
- The MongoDB connection is used for both session management (custom collection) and LangGraph checkpointing.
- Supabase Storage is recommended for persistent audio URLs in production. Without cloud storage, audio files are stored locally and will be lost on redeploy.

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
