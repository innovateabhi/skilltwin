# SkillTwin Standalone Chatbot

Standalone SkillTwin chatbot with separate React frontend and FastAPI backend.

## Structure

chatbot/
├── frontend/
├── backend/
└── embed/
    └── embed.js

## Run backend

cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

## Run frontend

cd frontend
npm install
npm run dev

Frontend: http://localhost:5174
Backend: http://127.0.0.1:8001
Docs: http://127.0.0.1:8001/docs

Pricing is intentionally marked as not finalized until official plans are supplied.
