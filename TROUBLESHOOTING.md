# 🔧 Troubleshooting Guide - Financial AI Platform

## Issue: 500 Internal Server Error on `/api/chat/users`

### Root Cause
The backend container cannot connect to MongoDB, or there's an unhandled exception in the user creation logic.

---

## ✅ Solution Steps

### Step 1: Rebuild with Debug Logging
```powershell
# Stop all containers and remove volumes (fresh start)
docker compose down -v

# Rebuild with new debug logging
docker compose up --build -d
```

### Step 2: Check Backend Logs
```powershell
# Watch backend logs in real-time
docker compose logs -f backend
```

Look for these messages:
- ✅ `"Connected to MongoDB"` - Database connection successful
- ❌ `"Warning: Could not connect to MongoDB"` - Database connection failed
- ❌ `"ERROR: Database connection not available"` - DB object is None
- ❌ Stack traces showing the exact error

### Step 3: Verify MongoDB is Running
```powershell
# Check MongoDB container status
docker compose ps mongodb

# Should show: "Up X minutes (healthy)"

# Check MongoDB logs
docker compose logs mongodb --tail=20
```

### Step 4: Test Backend Directly
```powershell
# Test health endpoint
curl http://localhost:8000/api/health

# Expected: {"status":"healthy","service":"financial-ai-backend","version":"0.1.0"}
```

### Step 5: Check Network Connectivity
```powershell
# Enter backend container
docker exec -it financial-ai-backend bash

# Test MongoDB connection from inside container
ping mongodb

# Should resolve to an IP like 172.18.0.x
```

---

## 🐛 Common Issues & Fixes

### Issue 1: Ollama Container Unhealthy
**Symptom:** `financial-ai-ollama` shows as unhealthy

**Fix:**
```powershell
# The model needs to be pulled manually after first startup
docker exec -it financial-ai-ollama ollama pull qwen2.5:14b

# This takes 5-10 minutes (~9GB download)
```

### Issue 2: Frontend Crashing with PostCSS Error
**Symptom:** `module is not defined in ES module scope`

**Fix:** Already fixed! The `postcss.config.js` now uses ES module syntax:
```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

### Issue 3: Backend Can't Connect to MongoDB
**Symptom:** 500 errors, logs show "Could not connect to MongoDB"

**Possible Causes:**
1. MongoDB container not healthy yet (wait 30-60 seconds)
2. Network issue between containers
3. MongoDB crashed

**Fix:**
```powershell
# Restart everything
docker compose down
docker compose up -d

# Wait 2 minutes for all services to stabilize
docker compose ps
```

### Issue 4: Chat Input Not Working
**Symptom:** Can't type messages or press Enter

**Fix:** Already fixed! Changed `onKeyPress` to `onKeyDown` in App.jsx

---

## 📊 Expected Startup Sequence

1. **MongoDB starts** (10-20 seconds) → becomes healthy
2. **Ollama starts** (30-60 seconds) → becomes healthy  
3. **Backend starts** (10-20 seconds) → connects to MongoDB → becomes healthy
4. **Frontend starts** (10-20 seconds) → connects to backend → accessible at :3000

**Total time:** 2-3 minutes for full startup

---

## 🔍 Debug Commands

### View All Container Status
```powershell
docker compose ps
```

### View Specific Service Logs
```powershell
docker compose logs backend --tail=100
docker compose logs frontend --tail=50
docker compose logs mongodb --tail=30
docker compose logs ai-engine --tail=30
```

### Real-time Log Streaming
```powershell
docker compose logs -f
```

### Enter Container for Debugging
```powershell
# Backend
docker exec -it financial-ai-backend bash

# MongoDB
docker exec -it financial-ai-mongodb mongosh

# Ollama
docker exec -it financial-ai-ollama ollama list
```

### Test API Endpoints
```powershell
# Health check
curl http://localhost:8000/api/health

# Create user (PowerShell)
$body = @{ email = "test@example.com"; name = "Test" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/chat/users" -Method Post -Body $body -ContentType "application/json"
```

---

## 🎯 Success Indicators

✅ All containers show `(healthy)` in `docker compose ps`
✅ Backend logs show `"Connected to MongoDB"`
✅ Frontend accessible at http://localhost:3000
✅ Can create users via API
✅ Can send chat messages
✅ AI responses stream in real-time

---

## 🚀 Quick Fix Command

If nothing works, try this nuclear option:

```powershell
# Complete reset
docker compose down -v --remove-orphans
docker system prune -f

# Fresh build
docker compose up --build -d

# Wait 3 minutes, then check
docker compose ps
```

---

## 📞 Still Having Issues?

1. Check Docker Desktop is running
2. Ensure ports 3000, 8000, 27017, 11434 are not blocked
3. Check Windows Firewall isn't blocking Docker
4. Try running PowerShell as Administrator
5. Check disk space (Docker needs ~15GB for images + models)
