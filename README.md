# 📈 Financial AI Platform - Docker Setup & User Guide

A production-grade, containerized Financial AI Assistant powered by local LLMs (Qwen 2.5 via Ollama), real-time financial market tools (Yahoo Finance, CoinGecko, IPO GMP tracker, Mutual Funds), FastAPI, and React.

---

## 🏗️ Architecture

```
                                  ┌────────────────────────┐
                                  │   React + Vite UI      │
                                  │  http://localhost:3000 │
                                  └───────────┬────────────┘
                                              │
                                              ▼ (API Proxy / SSE)
┌───────────────────────┐         ┌────────────────────────┐
│  Ollama LLM Engine    │ ◄─────► │   FastAPI Backend      │
│  http://localhost:11434│         │  http://localhost:8000 │
└───────────┬───────────┘         └───────────┬────────────┘
            │                                 │
     (Model Auto-pull)                        ▼
┌───────────┴───────────┐         ┌────────────────────────┐
│  ollama-init Service  │         │   MongoDB Database     │
│  (One-time Provision) │         │   localhost:27017      │
└───────────────────────┘         └────────────────────────┘
```

| Service | Container Name | Port | Description |
|---|---|---|---|
| **Frontend** | `financial-ai-frontend` | `3000` | Modern React + Tailwind chat interface |
| **Backend** | `financial-ai-backend` | `8000` | FastAPI server, ReAct agent, financial tools |
| **Ollama** | `financial-ai-ollama` | `11434` | Local LLM inference engine |
| **Ollama Init** | `financial-ai-ollama-init` | - | Automatic model provisioner on startup |
| **MongoDB** | `financial-ai-mongodb` | `27017` | Database storing conversations & messages |

---

## 🚀 One-Command Docker Quickstart

### Windows (PowerShell)
```powershell
.\start.ps1
```
*(Or double-click `start.bat`)*

### Linux / macOS
```bash
chmod +x start.sh
./start.sh
```

### Standard Docker Compose
```bash
docker compose up --build -d
```

On first startup:
1. Docker builds the Backend and Frontend images.
2. MongoDB and Ollama start up with persistent named volumes.
3. The `ollama-init` service automatically checks and downloads the configured LLM model (`qwen2.5:1.5b` by default).
4. Once all services are healthy, open **http://localhost:3000** in your browser!

---

## ⚙️ Configuration (`.env`)

You can customize the setup using the `.env` file (copied automatically from `.env.example`):

```env
# Ollama LLM Model Selection:
# - qwen2.5:1.5b : Fastest, lightweight (~1GB RAM), ideal for CPU systems
# - qwen2.5:7b   : High accuracy (~5GB RAM), recommended for 16GB RAM systems
# - qwen2.5:14b  : Maximum reasoning (~10GB RAM), requires GPU or >16GB RAM
OLLAMA_MODEL=qwen2.5:1.5b

MONGODB_URL=mongodb://mongodb:27017
MONGODB_DB_NAME=financial_ai
OLLAMA_HOST=http://ai-engine:11434
VITE_API_URL=http://localhost:8000/api
```

---

## 🛠️ Useful Docker Commands

### Check Service Status
```bash
docker compose ps
```

### View Live Logs
```bash
# All services
docker compose logs -f

# Backend only
docker compose logs -f backend

# Ollama model download progress
docker compose logs -f ollama-init
```

### Pull or Switch LLM Models
To use another model (e.g. `qwen2.5:7b`):
1. Update `OLLAMA_MODEL=qwen2.5:7b` in `.env`.
2. Restart backend:
   ```bash
   docker compose up -d
   ```

### Stop All Containers
```bash
docker compose down
```
*(Or run `.\stop.ps1` / `stop.bat`)*

---

## 🔍 Verification & Health Checks

- **Backend Health:** `http://localhost:8000/api/health`
- **Swagger Documentation:** `http://localhost:8000/docs`
- **Frontend App:** `http://localhost:3000`
- **Ollama Installed Models:** `docker exec financial-ai-ollama ollama list`
