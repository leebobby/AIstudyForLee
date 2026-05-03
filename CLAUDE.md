# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is an AI learning repository. The active project is **`clustermanager/`** — a cluster configuration, management, and diagnostics system with a three-plane network architecture (management/GE, control/10GE, data/100GE). Other directories (`cpp_agent/`, `basicstudy/`) can be ignored.

---

## clustermanager

### Stack

- **Backend**: Python, FastAPI, SQLAlchemy (SQLite by default), Uvicorn
- **Frontend**: Vue 3, Vite, Element Plus, Vue Router, Axios, D3.js (topology visualization)

### Running the backend

```bash
cd clustermanager/backend
pip install -r requirements.txt
python run.py
# or: uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

On startup the backend auto-initializes the SQLite DB and seeds demo data (1 Master + 5 Slave + 1 Sensor node). Swagger docs available at http://localhost:8000/docs.

### Running the frontend

```bash
cd clustermanager/frontend
npm install
npm run dev    # dev server on http://localhost:3000
npm run build  # production build
```

### Backend architecture

```
backend/
├── main.py          # FastAPI app entry, DB init, router registration
├── run.py           # Convenience launcher
├── models/          # SQLAlchemy ORM models
├── api/             # Route handlers: nodes, network, alerts, diagnose, ipmi, patrol, pxe
├── services/        # Business logic: ipmi_service, network_service, pxe_service
├── parsers/         # Log/data parsers
└── tasks/           # Background scheduled tasks
```

### Frontend architecture

```
frontend/src/
├── main.js          # App entry, Element Plus setup
├── App.vue          # Root layout with sidebar navigation
├── router/          # Vue Router config
├── views/           # Page components: Dashboard, NetworkMap, Nodes, PXEDeploy,
│                    #   Alerts, Patrol, Diagnose
└── components/      # Shared UI components
```

The `NetworkMap.vue` view renders a D3.js three-plane topology graph. The backend API base URL is configured per-view via Axios (proxied through Vite in dev mode).

