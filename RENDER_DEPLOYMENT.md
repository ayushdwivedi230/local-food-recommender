# LocalFood AI - Render.com Deployment Guide

## Overview

This guide covers deploying **LocalFood AI to Render.com** as a **single unified Web Service** that serves:
- ✅ React + Vite frontend (UI)
- ✅ Node.js + Express API backend
- ✅ Python LocalFood agent
- ✅ JSON-based session memory and restaurant data

Everything runs in **one Render Web Service** for simplicity.

## Prerequisites

1. **GitHub account** with repository containing LocalFood AI code
2. **Render.com account** (free tier available at https://render.com)
3. Repository is **public** on GitHub

## Architecture

```
Render Web Service (Node.js)
├── Frontend (React + Vite) → Served as static files on /
├── API Routes → /api/* (Express)
├── Python Agent → Runs on backend for recommendations
└── Session Memory → JSON files (restaurants.json, sessions.json)
```

**Key Benefit:** All requests go to the same origin, so no CORS issues, no environment variable complexity.

---

## Step 1: Create Render Web Service

### 1.1 Go to Render Dashboard
- Visit https://dashboard.render.com
- Click **"New+"** → **"Web Service"**

### 1.2 Connect GitHub Repository
- Click **"Connect account"** and authorize Render to access GitHub
- Search for and select your repository
- Click **"Connect"**

### 1.3 Configure the Service

| Setting | Value |
|---------|-------|
| **Name** | `localfood-ai` |
| **Environment** | `Node` |
| **Region** | `Oregon` (or closest to you) |
| **Branch** | `main` |
| **Build Command** | `cd artifacts/localfood-ai && pnpm install --frozen-lockfile && pnpm run build && cd ../api-server && pnpm install --frozen-lockfile && pnpm run build` |
| **Start Command** | `node --enable-source-maps ./artifacts/api-server/dist/index.mjs` |
| **Plan** | `Free` |

**Build Command Explanation:**
1. Build React frontend → outputs to `artifacts/localfood-ai/dist/public/`
2. Build Node API server → outputs to `artifacts/api-server/dist/`
3. The API server's Express app serves the frontend static files automatically

### 1.4 Environment Variables

Click **"Advanced"** and add these:

```
NODE_ENV=production
LOCALFOOD_PYTHON=python3
OPENAI_API_KEY=(leave blank for now)
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
PORT=3000
```

**Note:** No `VITE_API_URL` or `BASE_PATH` needed—the frontend makes API calls to the same origin.

### 1.5 Deploy
Click **"Create Web Service"** and wait 5-10 minutes for the build to complete.

**Your app will be live at:** `https://localfood-ai.onrender.com` (or your custom domain)

---

## Step 2: Verify Deployment

### 2.1 Test the Frontend
1. Open your service URL: `https://localfood-ai.onrender.com`
2. You should see the **LocalFood AI chat interface**
3. Try a search: *"I'm vegetarian and want Punjabi food in Jalandhar"*
4. Verify the agent responds with recommendations

### 2.2 Check Logs
1. Click your service in Render Dashboard
2. Scroll to **"Logs"** section
3. Look for `Server listening on port 3000`
4. API requests should appear in real-time

### 2.3 If You See "Cannot GET /"
- **Build might still be in progress** (takes 5-10 minutes)
- Click **"Events"** tab to check build status
- Wait for build to complete and service to restart
- Then refresh the page

### 2.4 If API Calls Fail
1. Check backend logs for Python errors
2. Verify `LOCALFOOD_PYTHON=python3` is set in environment variables
3. Check that restaurant data loads: Look for `restaurants.json` in logs

---

## Step 3: How It Works

### Frontend Static Files
- React app builds to `artifacts/localfood-ai/dist/public/`
- Express server serves these files as static content
- Navigation routes (React Router) automatically handled via SPA fallback

### API Routes
- All `/api/*` requests are routed to Express handlers
- Example: `POST /api/run-agent` → Python agent processes and returns recommendations
- Same origin = no CORS issues, all requests go to your Render domain

### Python Agent
- Runs inside the Node.js server process via subprocess calls
- Processes food recommendations with diet constraints
- Session memory persisted in `backend/data/sessions.json`

---

## Step 4: Auto-Deploy on Code Push

Render automatically redeploys when you push to GitHub:

```bash
git push origin main
```

**Render will:**
1. Detect the push
2. Trigger a new build (5-10 minutes)
3. Deploy the new version with zero downtime

No manual deployment needed!

---

## Troubleshooting

### **Build Fails with "Cannot find module"**
- **Cause:** Dependency installation failed
- **Solution:**
  1. Click service → **"Settings"**
  2. Click **"Clear build cache"**
  3. Click **"Manual Deploy"** → **"Deploy latest commit"**

### **"Cannot GET /" When You Open the URL**
- **Cause:** Build not finished yet, or SPA fallback route not working
- **Solution:**
  1. Wait 5-10 minutes for build to complete
  2. Check **"Events"** tab for build status
  3. Check **"Logs"** tab for errors
  4. Refresh the page once build is done

### **API Calls Return 404**
- **Cause:** Backend not running or `/api` routes not configured
- **Solution:**
  1. Check logs for `Server listening on port 3000`
  2. Verify build completed successfully
  3. Check backend error logs

### **"Cannot find module '@workspace/...'"**
- **Cause:** Workspace monorepo dependencies not installed
- **Solution:**
  1. Run `pnpm install` locally
  2. Check `pnpm-workspace.yaml` exists
  3. Build commands must run in correct order

### **Python Agent Errors in Logs**
- **Cause:** Python 3 not found or agent code issue
- **Solution:**
  1. Verify `LOCALFOOD_PYTHON=python3` environment variable
  2. Check backend logs for specific Python errors
  3. Test locally: `python -m py_compile backend/*.py`

### **Service Goes to Sleep (Free Tier)**
- **Cause:** Free tier services spin down after 15 minutes of inactivity
- **Solution:**
  1. Make a request to wake the service
  2. Or upgrade to **Starter** tier ($7/month) for persistent service

---

## Production Checklist

When ready for production use:

- [ ] Set `NODE_ENV=production` ✅ (already configured)
- [ ] Add valid `OPENAI_API_KEY` if using real LLM
- [ ] Upgrade from Free to Starter tier (no auto-sleep)
- [ ] Add custom domain name (optional)
- [ ] Enable automatic backups for session data
- [ ] Monitor service logs regularly

---

## Services Included

✅ **Frontend**: React 19 + Vite + Tailwind CSS  
✅ **Backend API**: Node.js + Express  
✅ **AI Agent**: Python recommendation engine  
✅ **Data**: JSON files (restaurants, session memory)  
✅ **Logging**: Structured JSON logs via Pino  

## Architecture Diagram

```
Browser
  ↓
https://localfood-ai.onrender.com
  ↓
Render Web Service (Node.js + Express)
  ├── GET / → Serves index.html (React app loads)
  ├── GET /assets/* → Serves JS/CSS/images
  ├── GET * → SPA fallback (serves index.html for React routing)
  ├── POST /api/run-agent → Python agent processes request
  └── GET /api/health → Health check
```

## Next Steps

1. **Deploy to Render** using the instructions above
2. **Test the live app** at your Render URL
3. **Share the URL** with others
4. **Monitor logs** if issues occur
5. **(Optional) Upgrade to paid tier** when ready for production use

---

## Questions?

- Check **Render Documentation**: https://render.com/docs
- Check **Service Logs** in Render Dashboard
- Review **Build Output** in the Events tab
- Test **locally first** before pushing to GitHub

Happy deploying! 🚀
