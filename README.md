# TestForge

TestForge is an automotive electronics test management platform built around the
**ISO 16750** standard (Parts 1, 2, 4 and 5 — Road vehicles, Environmental conditions
and testing for electrical and electronic equipment).

It helps test engineers:

- Register a Device Under Test (DUT) with its electrical, mechanical and environmental
  parameters.
- Automatically generate an ISO 16750-based test plan with the help of a local LLM
  (via [Ollama](https://ollama.com/)), with sensible offline fallbacks when the LLM is
  unavailable.
- Generate per-test pre-test checklists (equipment & calibration, safety precautions,
  DUT preparation) and export them as PDF.
- Record test results (measured values, conditions, observations, deviations) and
  generate a formal Turkish test report, exportable as DOCX or PDF.
- Track campaign-wide progress on a dashboard with pass/fail statistics, filters and a
  results chart.

## Tech stack

| Layer    | Technology |
|----------|------------|
| Frontend | React 18 + Vite 5 + Tailwind CSS + Chart.js (react-chartjs-2) + react-hot-toast + axios |
| Backend API | Flask 3 + SQLite + python-docx + ReportLab + qrcode + Pillow |
| AI Backend | Flask 3 service that owns all LLM/Ollama calls |
| AI Runtime | [Ollama](https://ollama.com/) REST API, model `qwen2.5:14b` |
| CI/CD    | GitHub Actions (lint + tests + semantic version bump, Docker build + health check) |

## Project structure

```
testforge/
├── ai_backend/               # Separate AI backend server, proxies prompts to Ollama
├── backend/
│   ├── app/
│   │   ├── services/        # DUTService, PlanService, ChecklistService, ReportService
│   │   ├── routes/           # Flask blueprints (dut, plan, checklist, result, report, dashboard)
│   │   ├── utils/             # docx/pdf export helpers, QR codes, response envelopes
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── ai_backend_client.py
│   │   ├── prompts.py
│   │   └── fallbacks.py
│   ├── tests/                 # pytest test suite
│   ├── requirements.txt
│   ├── Dockerfile
│   └── run.py
├── frontend/
│   ├── src/
│   │   ├── pages/             # DUTRegistration, TestPlan, Checklist, ResultReport, Dashboard
│   │   ├── components/        # Navbar, TestCard, Badge, Spinner
│   │   ├── api/                # axios client + API functions
│   │   └── utils/
│   ├── package.json
│   └── Dockerfile
├── .github/workflows/         # ci.yml, cd.yml
├── docker-compose.yml
├── start.bat                   # Windows one-click launcher
├── pytest.ini
├── VERSION
└── README.md
```

## Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.11+
- **[Ollama](https://ollama.com/)** running locally with the `qwen2.5:14b` model pulled:

  ```
  ollama pull qwen2.5:14b
  ollama serve
  ```

  TestForge works without Ollama too — every AI-powered feature (test plan,
  checklist, report) falls back to a built-in mock dataset so the app remains
  fully usable offline.

## Running on Windows (recommended): `start.bat`

From the `testforge/` folder, double-click **`start.bat`** (or run it from a
terminal). It will:

1. Create Python virtual environments for `ai_backend/` and `backend/` if missing.
2. Install `ai_backend/requirements.txt` and `backend/requirements.txt`.
3. Install frontend npm dependencies if `frontend/node_modules` is missing.
4. Launch the AI Flask backend on **http://localhost:5001** in its own window.
5. Launch the main Flask backend on **http://localhost:5000** in its own window.
6. Launch the Vite dev server on **http://localhost:5173** in its own window.
7. Open the app in your default browser.

Close the three opened terminal windows to stop the servers.

## Manual setup

### AI Backend (Flask)

```powershell
cd ai_backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

The AI API will be available at `http://localhost:5001/api`. Health check:
`GET http://localhost:5001/api/health`.

AI configuration is read from environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_URL` | `http://localhost:11434` | Base URL of the Ollama server |
| `OLLAMA_MODEL` | `qwen2.5:14b` | Model used for generation |
| `OLLAMA_TIMEOUT` | `120` | Request timeout (seconds) |

### Backend API (Flask)

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
$env:AI_BACKEND_URL = "http://localhost:5001"
python run.py
```

The API will be available at `http://localhost:5000/api`. Health check:
`GET http://localhost:5000/api/health`.

Configuration is read from environment variables (all optional, with defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_BACKEND_URL` | `http://localhost:5001` | Base URL of the separate AI backend |
| `AI_BACKEND_TIMEOUT` | `130` | Request timeout for AI backend calls (seconds) |
| `TESTFORGE_DB_PATH` | `backend/data/testforge.db` | SQLite database path |
| `TESTFORGE_EXPORT_DIR` | `backend/exports` | Directory for generated DOCX/PDF files |

### Frontend (React + Vite)

```powershell
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`. The Vite dev server proxies
`/api` requests to `http://localhost:5000`.

### Running tests & linting

```powershell
# Backend
cd backend
venv\Scripts\activate
pytest -v
flake8 backend --max-line-length=100

# Frontend
cd frontend
npm run lint
npm run build
```

## Running with Docker Compose

```powershell
docker compose up --build
```

- Frontend (served via nginx, proxying `/api` to the backend): `http://localhost:8080`
- Backend API: `http://localhost:5000`
- AI Backend API: `http://localhost:5001`

The Docker Compose topology is one frontend container plus two backend containers:
`frontend -> backend -> ai-backend -> Ollama`. The AI backend container reaches
Ollama on the Windows/macOS host via `host.docker.internal:11434` (already
configured in `docker-compose.yml`).

## CI/CD (GitHub Actions)

No extra setup is required beyond pushing to a GitHub repository — the workflows
under `.github/workflows/` run automatically:

- **`ci.yml`** — on every push/PR: installs backend dependencies, runs `flake8`,
  runs the `pytest` suite, and (on pushes) bumps `VERSION` based on the latest
  commit message:
  - `BREAKING` → major version bump
  - `feat:` → minor version bump
  - `fix:` → patch version bump
  - anything else → no version change
- **`cd.yml`** — on push to `main`/`master`: builds the `testforge-backend` Docker
  image, runs it, waits for the container health check to pass, performs an HTTP
  health check against `/api/health`, and prints a success message with the current
  version.

To enable the automatic version-bump commit in `ci.yml`, make sure the repository
allows GitHub Actions to push commits (**Settings → Actions → General → Workflow
permissions → Read and write permissions**).

## Screenshots

| Page | Screenshot |
|------|------------|
| DUT Registration | <img width="1118" height="1078" alt="image" src="https://github.com/user-attachments/assets/c1290d48-e65d-49ee-9373-ec67071f3a5d" /> |
| Test Plan | <img width="1144" height="1080" alt="image" src="https://github.com/user-attachments/assets/5a745975-2485-45f9-a633-e0b67a43b367" /> |
| Checklist | <img width="1115" height="1080" alt="image" src="https://github.com/user-attachments/assets/7032ad27-7752-4881-8491-fd177b660095" /> |
| Result & Report | <img width="1241" height="1013" alt="image" src="https://github.com/user-attachments/assets/0305bd35-61b5-4366-b9ef-1de3e2d23383" /> |
| Campaign Dashboard | <img width="1279" height="1080" alt="image" src="https://github.com/user-attachments/assets/89dcaedb-e312-4c2b-ba5b-0a5afd5dacda" /> |
