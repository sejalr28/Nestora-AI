# SocietyBoard AI

AI-powered platform for a co-op housing society: water schedule, occupancy
directory, service requests, guest parking, and redevelopment tracking —
accessible via a WhatsApp bot and a React admin dashboard.

## Stack
- **Backend:** FastAPI + PostgreSQL + SQLAlchemy
- **LLM:** Ollama (Llama 3.1) by default — swappable to Claude/OpenAI/Gemini
  via one config value (`LLM_PROVIDER` in `.env`)
- **WhatsApp:** Twilio Sandbox (free) + ngrok for local webhook testing
- **Frontend:** React + Tailwind (admin dashboard)

## Status: Step 1 — project skeleton ✅
- FastAPI app boots and serves `GET /health` (checks DB connectivity + shows
  active LLM provider)
- Postgres runs via docker-compose
- Config is centralized and env-driven (`app/config.py`)

## Run it

```bash
cd societyboard-ai
cp backend/.env.example backend/.env   # defaults work as-is for local dev
docker-compose up --build
```

Then check:
```bash
curl http://localhost:8000/health
# {"status":"ok","environment":"development","database":"connected","llm_provider":"ollama"}
```

If you don't want Docker for the backend itself (only Postgres), you can also run:
```bash
docker-compose up postgres -d
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## What's next
- **Step 2:** SQLAlchemy models (Resident, Flat, WaterSchedule, ServiceRequest,
  Vendor) + Alembic migrations + first CRUD routes
- **Step 3:** LLM provider interface (Ollama first) + tool-calling agent
- **Step 4:** Twilio WhatsApp webhook + ngrok tunnel + onboarding flow
- **Step 5:** React + Tailwind admin dashboard
