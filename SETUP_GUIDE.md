# 🚀 Financial AI Platform - Complete Setup Guide

## ✅ All 6 Phases Completed!

Your production-grade, Dockerized Financial AI Platform is ready with:
- **Qwen 2.5 14B** model for enhanced reasoning capabilities
- Real-time financial data (Stocks, Crypto, IPOs, Mutual Funds)
- Streaming responses with Simple/Advanced mode toggle
- Persistent chat history in MongoDB
- Professional React + Tailwind UI

---

## 📁 Project Structure

```
/workspace/
├── docker-compose.yml          # Orchestrates all 4 containers
├── README.md                   # This file
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI application
│       ├── config.py           # Settings management
│       ├── database.py         # MongoDB connection
│       ├── models.py           # Pydantic schemas
│       ├── repositories.py     # Data access layer
│       ├── tools.py            # Financial data tools
│       ├── agent.py            # ReAct AI agent with Qwen 2.5
│       └── routers/
│           ├── chat.py         # Basic chat endpoints
│           └── chat_ai.py      # AI streaming endpoints
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx             # Full chat UI with streaming
        └── index.css
```

---

## 🏗️ Architecture (4 Docker Containers)

| Container | Technology | Port | Purpose |
|-----------|------------|------|---------|
| `mongodb` | MongoDB 6 | 27017 | Chat history & user context |
| `ollama` | Ollama + Qwen 2.5 14B | 11434 | Local LLM inference |
| `backend` | FastAPI + Python | 8000 | API, AI agent, data tools |
| `frontend` | React + Vite + Tailwind | 3000 | Chat interface |

---

## 🚀 Quick Start

### Step 1: Start All Containers

```bash
cd /workspace
docker compose up --build
```

**First-time setup will take 5-10 minutes:**
- Download Docker images (~500MB)
- Pull Qwen 2.5 14B model (~9GB)
- Install dependencies

### Step 2: Verify Everything is Running

```bash
# Check container status
docker compose ps

# Test backend health
curl http://localhost:8000/api/health

# Expected response:
# {"status":"healthy","service":"financial-ai-backend","version":"0.1.0"}
```

### Step 3: Open the Application

**Frontend:** http://localhost:3000  
**API Docs:** http://localhost:8000/docs

---

## 💡 How to Use

### 1. Start a Conversation
- Click "New Chat" to create a conversation
- Type your question in the input box
- Press Enter or click "Send"

### 2. Try These Example Queries

**Stocks:**
- "How is TCS performing today?"
- "What's the current price of Reliance Industries?"
- "Compare HDFC Bank and ICICI Bank"

**Crypto:**
- "What's the latest Bitcoin price?"
- "How is Ethereum doing compared to last week?"

**IPOs:**
- "What are the latest IPO GMP rates?"
- "Tell me about upcoming IPOs"

**Mutual Funds:**
- "What's the NAV of SBI Bluechip Fund?"

### 3. Toggle Modes

**Simple Mode (Default):**
- Clean, concise answers
- Perfect for quick insights

**Advanced Mode:**
- Shows AI's reasoning process 🧠
- Displays data sources and tool results 🔧
- Great for understanding the analysis

---

## 🔧 Configuration

### Change AI Model

Edit `backend/app/agent.py`:

```python
MODEL_NAME = "qwen2.5:14b"  # Options: llama3, qwen2.5:7b, qwen2.5:14b, mistral
```

Then rebuild:
```bash
docker compose up --build -d
```

### Enable GPU Acceleration (NVIDIA)

Uncomment in `docker-compose.yml`:

```yaml
ollama:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
```

### Adjust Context Window

Edit `backend/app/agent.py`:

```python
CONTEXT_WINDOW_SIZE = 10  # Number of messages to include
```

---

## 🛠️ Development Commands

```bash
# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Restart a service
docker compose restart backend

# Stop all containers
docker compose down

# Stop and remove volumes (reset database)
docker compose down -v

# Run backend locally (without Docker)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Run frontend locally
cd frontend
npm install
npm run dev
```

---

## 📊 API Endpoints

### Health & Status
- `GET /api/health` - Backend health check
- `GET /api/` - Welcome message

### Conversations
- `GET /api/chat/conversations` - List all conversations
- `POST /api/chat/conversation` - Create new conversation
- `GET /api/chat/conversation/{id}` - Get conversation with messages
- `DELETE /api/chat/conversation/{id}` - Delete conversation

### Messages
- `POST /api/chat/message` - Send message (non-streaming)
- `POST /api/chat/stream` - Send message with SSE streaming ⭐

---

## 🎯 Key Features Implemented

### ✅ Phase 1: Infrastructure
- [x] Docker Compose orchestration
- [x] 4 isolated containers
- [x] Internal Docker network
- [x] Health checks

### ✅ Phase 2: Memory Layer
- [x] MongoDB schema (Users, Conversations, Messages)
- [x] Context window logic (last N messages)
- [x] Persistent chat history

### ✅ Phase 3: Real-Time Data
- [x] Stock prices (yfinance - NSE/BSE/International)
- [x] Crypto prices (CoinGecko API)
- [x] IPO GMP data (web scraping)
- [x] Mutual Fund NAV (AMFI API)

### ✅ Phase 4: AI Agent
- [x] Qwen 2.5 14B integration
- [x] ReAct pattern (Reason + Act)
- [x] Function calling for data tools
- [x] Anti-hallucination safeguards
- [x] System prompt engineering

### ✅ Phase 5: Frontend UI
- [x] Modern React + Tailwind design
- [x] Server-Sent Events streaming
- [x] Simple/Advanced mode toggle
- [x] Conversation sidebar
- [x] Auto-scroll, loading states
- [x] Error handling

### ✅ Phase 6: Refinement
- [x] Graceful error handling
- [x] API timeout management
- [x] Optimized MongoDB queries
- [x] GPU passthrough configuration (optional)

---

## 🐛 Troubleshooting

### Backend won't start
```bash
docker compose logs backend
# Check MongoDB connection string in config.py
```

### Ollama model not found
```bash
# Wait for initial download (first run takes time)
docker compose logs ollama -f
```

### Frontend can't connect to backend
```bash
# Verify proxy in vite.config.js
# Check CORS settings in main.py
```

### Slow responses
- Enable GPU passthrough (see Configuration)
- Use smaller model: `qwen2.5:7b` instead of `14b`
- Reduce context window size

---

## 📝 Next Steps & Enhancements

### Recommended Improvements
1. **Add Authentication** - User login/signup
2. **Export Chats** - PDF/Markdown export
3. **Voice Input** - Speech-to-text integration
4. **More Data Sources** - News APIs, economic indicators
5. **Chart Visualization** - Price history graphs
6. **Portfolio Tracking** - Track user investments
7. **Alerts** - Price threshold notifications

### Production Deployment
- Add HTTPS/TLS
- Configure proper CORS origins
- Set up monitoring (Prometheus/Grafana)
- Implement rate limiting
- Add logging (ELK stack)

---

## 📄 License

MIT License - Free for personal and commercial use.

---

## 🤝 Support

For issues or questions:
1. Check logs: `docker compose logs -f`
2. Review API docs: http://localhost:8000/docs
3. Verify all containers are healthy: `docker compose ps`

---

**Built with ❤️ using:**
- FastAPI ⚡
- React + Vite 🔥
- MongoDB 🍃
- Ollama + Qwen 2.5 🤖
- Tailwind CSS 🎨
- Docker 🐳
