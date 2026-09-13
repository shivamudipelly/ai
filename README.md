# Financial AI Platform - Phase 1 Setup Guide

## 📁 Project Structure

```
/workspace/
├── docker-compose.yml          # Main orchestration file
├── frontend/                   # React (Vite) + Tailwind
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       └── index.css
└── backend/                    # Python FastAPI
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        ├── main.py
        ├── config.py
        └── database.py
```

## 🚀 Quick Start

### Step 1: Navigate to the project directory
```bash
cd /workspace
```

### Step 2: Build and start all containers
```bash
docker-compose up --build
```

**Note:** First-time startup will take 10-15 minutes as it:
- Downloads MongoDB image (~500MB)
- Downloads Ollama image (~200MB)
- Downloads Qwen 2.5 14B model (~9GB) - **Reasoning-capable LLM**
- Builds frontend and backend images

### Step 3: Access the services

Once all containers are healthy, access them at:

| Service     | URL                          | Port  |
|-------------|------------------------------|-------|
| Frontend    | http://localhost:3000        | 3000  |
| Backend API | http://localhost:8000        | 8000  |
| MongoDB     | mongodb://localhost:27017    | 27017 |
| Ollama      | http://localhost:11434       | 11434 |

### Step 4: Verify everything is working

#### Test Backend Health
```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "financial-ai-backend",
  "version": "0.1.0"
}
```

#### Test Frontend
Open your browser and navigate to: http://localhost:3000

You should see the Financial AI Platform interface with backend status showing "connected".

#### Check Container Status
```bash
docker-compose ps
```

All 4 containers should show "healthy" status.

#### View Logs
```bash
# All containers
docker-compose logs -f

# Specific container
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f mongodb
docker-compose logs -f ai-engine
```

## 🔧 Troubleshooting

### Container won't start
```bash
# Rebuild specific service
docker-compose up --build backend

# Force recreate
docker-compose up --force-recreate
```

### Check if ports are available
```bash
# Linux/Mac
lsof -i :3000
lsof -i :8000
lsof -i :11434
lsof -i :27017

# Windows
netstat -ano | findstr :3000
netstat -ano | findstr :8000
```

### Reset everything
```bash
# Stop and remove all containers and volumes
docker-compose down -v

# Rebuild from scratch
docker-compose up --build
```

## 📋 What's Included in Phase 1

✅ **Docker Infrastructure**
- [x] Frontend Dockerfile (Node.js 20 + Vite)
- [x] Backend Dockerfile (Python 3.11 + FastAPI)
- [x] docker-compose.yml with all 4 services
- [x] Internal Docker network for container communication
- [x] Health checks for all services
- [x] Persistent volumes for MongoDB and Ollama data

✅ **Frontend (React + Vite + Tailwind)**
- [x] Basic React application structure
- [x] Tailwind CSS configuration
- [x] Vite dev server with proxy to backend
- [x] Simple UI showing system status

✅ **Backend (FastAPI)**
- [x] FastAPI application with lifespan events
- [x] MongoDB connection with Motor (async driver)
- [x] Configuration management with Pydantic Settings
- [x] Health check endpoint
- [x] CORS middleware for Docker network

✅ **Database (MongoDB)**
- [x] MongoDB 7.0 container
- [x] Persistent volume for data
- [x] Health check configuration

✅ **AI Engine (Ollama)**
- [x] Ollama container ready for LLM deployment
- [x] Persistent volume for models
- [x] Port exposed for model management
- [x] Optional GPU passthrough configuration (commented out)

## 🎯 Next Steps

Once Phase 1 is running successfully, we'll proceed to:

**Phase 2**: Memory Layer (MongoDB schemas, chat history, context window)
**Phase 3**: Real-Time Data Engine (yfinance, CoinGecko, IPO data tools)
**Phase 4**: AI Agent & Reasoning Core (Ollama integration, ReAct pattern)
**Phase 5**: Frontend UI (Full chat interface with streaming)
**Phase 6**: Refinement & Optimization (Error handling, GPU acceleration)

## ⚠️ Important Notes

1. **First Run**: The Ollama container will automatically pull the **Qwen 2.5 14B** model on first run. This can take 15-25 minutes depending on your internet speed. This model has superior reasoning capabilities compared to Llama 3, making it ideal for financial analysis.

2. **Why Qwen 2.5?** 
   - **Enhanced Reasoning**: Better at logical deduction and multi-step problem solving
   - **Financial Domain Knowledge**: Trained on extensive financial and technical data
   - **Function Calling**: Superior at understanding when to call external tools (yfinance, CoinGecko)
   - **14B Parameters**: Sweet spot between performance and resource usage (~9GB RAM)

3. **GPU Acceleration**: If you have an NVIDIA GPU, uncomment the GPU section in `docker-compose.yml` under the `ai-engine` service for significantly faster inference (5-10x speedup).

4. **Resource Usage**: 
   - Ollama with Qwen 2.5 14B requires ~9-10GB RAM
   - Total system memory usage: ~12-14GB
   - Ensure you have at least 16GB RAM for smooth operation (32GB recommended)

5. **Alternative Models**: If Qwen 2.5 14B is too large for your system, you can change to:
   - `qwen2.5:7b` (5GB RAM) - Good balance
   - `qwen2.5:3b` (2GB RAM) - Lightweight option
   - `llama3.1:8b` (5GB RAM) - Meta's latest
   
   Simply update `OLLAMA_MODEL` in `docker-compose.yml` and `config.py`.

6. **Stopping Services**: Use `docker-compose down` to stop all containers gracefully. The model will remain cached in the `ollama_data` volume for faster subsequent startups.

---

**Ready to proceed?** Once you confirm Phase 1 is running successfully, we'll move to Phase 2!
