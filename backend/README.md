# FastAPI Backend

Run from the repository root:

```powershell
.\venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Endpoints:

- `GET /health`
- `POST /api/research`
- `POST /api/research/stream`

Optional local clients:

```powershell
.\venv\Scripts\python.exe -m streamlit run backend\streamlit_app.py
```

```powershell
.\venv\Scripts\python.exe -m backend.cli
```
