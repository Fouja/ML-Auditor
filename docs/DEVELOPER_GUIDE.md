# ML-Auditor Developer Guide

## Prerequisites

- Python 3.13+
- Node.js 20+
- Docker & Docker Compose (optional)
- NVIDIA NIM API key (for ML features)

## Setup

```bash
git clone https://github.com/yourusername/ml-auditor.git
cd ml-auditor
```

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# For local testing without PostgreSQL:
export DJANGO_SETTINGS_MODULE=config.settings_test
python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

### ML Service

```bash
cd ml-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

## Development Workflow

### Code Style

- **Python**: Black formatter, isort imports, flake8 linting
- **TypeScript**: ESLint, Prettier with Tailwind plugin
- **Git**: Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`)

### Running Tests

```bash
# Backend (38 tests)
cd backend
DJANGO_SETTINGS_MODULE=config.settings_test pytest tests/ -v

# With coverage
DJANGO_SETTINGS_MODULE=config.settings_test pytest --cov=apps --cov-report=term-missing

# Frontend (13 tests)
cd frontend
npx vitest run

# Watch mode
npx vitest
```

### Adding a New Django App

1. Create `apps/myapp/` with `models.py`, `api.py`, `schemas.py`, `admin.py`
2. Add to `LOCAL_APPS` in `config/settings.py`
3. Create migration: `python manage.py makemigrations myapp`
4. Register router in `config/api.py`
5. Add tests in `tests/test_api.py`

### Adding a New Frontend Page

1. Create `src/app/dashboard/my-page/page.tsx`
2. Add to sidebar in `src/components/layout/sidebar.tsx`
3. Create API hook in `src/hooks/` if needed
4. Add test in `src/__tests__/`

### Adding a Celery Task

1. Define task in `apps/myapp/tasks.py`
2. Register in `CELERY_BEAT_SCHEDULE` if recurring
3. Queue: Use `queue="myqueue"` for specialized workers

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
# Required
DJANGO_SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
NIM_API_KEY=nvapi-your-nim-key

# Optional (for integrations)
PLAID_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_ID=
CANVA_CLIENT_ID=
```

## API Development

### Django Ninja Routers

```python
from ninja import Router
from .schemas import MySchema

router = Router()

@router.get("/my-endpoint", response=MySchema)
def my_view(request):
    # request.auth = authenticated user
    return {"data": "value"}
```

### Authentication

All endpoints except `/api/users/register` and `/api/users/login` require JWT:

```bash
# Get token
curl -X POST http://localhost:8000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@test.com", "password": "pass123"}'

# Use token
curl http://localhost:8000/api/workspace/tasks \
  -H "Authorization: Bearer <access_token>"
```

## Troubleshooting

| Issue | Solution |
|-------|---------|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| `relation does not exist` | `python manage.py migrate` |
| `JWT decode error` | Clear localStorage, re-login |
| Port 3000 in use | `lsof -i :3000` then kill process |
| Tests fail with SQLite | Ensure `DJANGO_SETTINGS_MODULE=config.settings_test` |
