# Workflow

Back to [[Home]].

1. `main` holds the scaffold and [[api-contract]]. Everyone branches from it.
2. Work only in your own area (see [[Tasks]]) to avoid merge conflicts.
3. Commit small and often; push your branch; open a PR to `main`.
4. Contract changes go in a tiny PR first (edit `api-contract.md` and `backend/app/models.py` together), then tell the others.
5. Pull `main` into your branch before opening a PR.
6. Feature freeze at 17:45. Devpost draft by 18:30. Submission locks at 19:00.

## Run locally

Backend:

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```
cd frontend
npm install
npm run dev
```

Copy `.env.example` to `.env` and set `GEMINI_API_KEY`. Never commit `.env`.
