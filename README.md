# BuildSight AI — Multimodal Construction Intelligence Platform

A college/demo-ready full-stack prototype based on the supplied architecture diagram. It includes a React + Vite dashboard and a Python/FastAPI API for multimodal site intake, safety/crack review, indicative project costing/material estimates/scheduling, property valuation, and a weather-advisory scaffold.

> **Important limitation:** The application is a decision-support prototype, not a certified safety, structural-engineering, quantity-surveying, weather, or property-appraisal system. Demo mode does not perform computer vision. AI outputs are unverified and can be wrong. Do not use this application to declare a structure safe, diagnose a crack, or direct hazardous site work. Escalate urgent hazards to site leadership and qualified professionals.

## Included features

- **Dashboard:** service status, recent review, priority finding count, cost and valuation snapshots.
- **Multimodal input:** image upload (PNG/JPG/WEBP, maximum 10 MB), field notes, and structured project JSON.
- **Safety and crack review:** schema-validated findings with category, severity, confidence, recommended action, next steps, and explicit disclaimer. With no provider key, the demo returns clearly labelled sample/intake findings rather than pretending to inspect the image.
- **Optional multimodal model:** server-side OpenAI-compatible API integration using environment variables. The key never belongs in the browser.
- **Project planning:** illustrative cost baseline, simplified material quantities, contingency, and phase schedule.
- **Real-estate valuation:** illustrative area/rate calculation with simple age and condition adjustments.
- **Site assistant:** checklist and weather limitation message; no live weather feed is connected.
- **API validation:** Pydantic request/response models and validation for empty input, malformed JSON, unsupported file type, empty images, and oversize uploads.

## Requirements

- Python 3.9+ (Python 3.11 recommended)
- Node.js 20+ and npm
- Optional API key for an OpenAI-compatible multimodal model

## Run locally

Open two terminal windows from the project root.

### 1. Backend

```bash
cd backend
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Optional: edit backend/.env and add OPENAI_API_KEY and OPENAI_MODEL
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs  
Health check: http://127.0.0.1:8000/api/health

Without `OPENAI_API_KEY`, the API operates in demo mode. If the configured provider is unavailable or returns invalid output, it falls back to demo mode and logs a provider error server-side.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (normally http://localhost:5173). By default, the frontend calls `http://127.0.0.1:8000`. To change this, create `frontend/.env.local`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Build the static frontend with `npm run build`; preview it with `npm run preview`.

## Tests

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | API status and AI configuration status |
| POST | `/api/analyze` | Multipart image + description + JSON project data |
| POST | `/api/plan` | Cost/material/schedule baseline |
| POST | `/api/valuation` | Indicative property value |
| GET | `/api/weather-advisory` | Weather-aware site checklist scaffold |

`POST /api/analyze` accepts multipart form fields `description` (string), `project_data` (JSON object string), and optional `image` (image file). Responses use a stable schema with `mode`, `summary`, `image_received`, `input_completeness`, `findings`, `next_steps`, and `disclaimer`.

## Security and deployment notes

- Never commit `.env`, API keys, production credentials, or sensitive site imagery. `.gitignore` excludes common local secrets and build artefacts.
- For deployment, set `OPENAI_API_KEY`, `OPENAI_MODEL`, `MAX_UPLOAD_MB`, and `CORS_ORIGINS` through the hosting provider's secret/configuration interface.
- Restrict CORS to the actual deployed frontend origin; do not use wildcard CORS with credentials.
- Add authentication, rate limiting, audit logging, malware scanning, object-storage policies, retention controls, HTTPS, and monitoring before production use.
- Configure the chosen AI provider's data-handling terms appropriately for construction imagery and client data.
- No database has been wired in this version; requests are not persisted. `Data Storage` in the supplied architecture is therefore a planned extension, not an implemented database.
- The weather module is a scaffold and does not fetch live forecasts. The valuation tool does not query comparable sales. Cost/material calculations are illustrative assumptions, not a bill of quantities.
- The current AI adapter uses the OpenAI-compatible Chat Completions API. Model names, image support, and response-format support vary by provider; confirm compatibility with your selected endpoint.

## Suggested demo flow

1. Start backend and frontend; verify the API-connected status.
2. Open **Site safety**, enter a description and project JSON, optionally upload a site image, then generate a review.
3. Mention a crack in the notes to see the demo crack-concern workflow when no API key is configured.
4. Open **Project planning** and generate an indicative estimate.
5. Open **Property valuation** and calculate an illustrative value.
6. Open **Site assistant** to show the weather-aware checklist and live-data limitation.
7. Use `/docs` to demonstrate typed API contracts and validation.

## Repository layout

```text
construction-intelligence/
├── backend/
│   ├── app/main.py
│   ├── tests/test_api.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/main.jsx
│   ├── src/styles.css
│   ├── index.html
│   └── package.json
└── README.md
```
