# LocalFood AI - Render.com Deployment Guide

## Overview

This guide covers deploying LocalFood AI to **Render.com** with:
- Backend API service (Node.js + Python agent)
- Frontend web service (React + Vite)
- Automatic builds from GitHub pushes

## Prerequisites

1. **GitHub account** with the repository `ayushdwivedi230/local-food-recommender`
2. **Render.com account** (free tier available)
3. Repository is already public

## Step 1: Create Backend API Service

### 1.1 Go to Render Dashboard
- Visit https://dashboard.render.com
- Click **"New+"** → **"Web Service"**

### 1.2 Connect GitHub Repository
- Click **"Connect account"** (authorize Render to access GitHub)
- Search for and select: `ayushdwivedi230/local-food-recommender`
- Click **"Connect"**

### 1.3 Configure Backend Service

| Setting | Value |
|---------|-------|
| **Name** | `localfood-api` |
| **Environment** | `Node` |
| **Region** | `Oregon` (or closest to you) |
| **Branch** | `main` |
| **Build Command** | `cd artifacts/api-server && pnpm install --frozen-lockfile && pnpm run build` |
| **Start Command** | `node --enable-source-maps ./artifacts/api-server/dist/index.mjs` |
| **Plan** | `Free` |

### 1.4 Environment Variables
Click **"Advanced"** and add:

```
NODE_ENV=production
LOCALFOOD_PYTHON=python3
OPENAI_API_KEY=(leave blank for now)
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

### 1.5 Deploy
Click **"Create Web Service"** → Wait 3-5 minutes for deployment

**Note the API URL:** `https://localfood-api.onrender.com` (or similar)

---

## Step 2: Create Frontend Web Service

### 2.1 Create New Service
- In Render dashboard, click **"New+"** → **"Web Service"** again
- Connect GitHub (same account)
- Select: `ayushdwivedi230/local-food-recommender`

### 2.2 Configure Frontend Service

| Setting | Value |
|---------|-------|
| **Name** | `localfood-web` |
| **Environment** | `Node` |
| **Region** | `Oregon` (same as backend) |
| **Branch** | `main` |
| **Build Command** | `cd artifacts/localfood-ai && pnpm install --frozen-lockfile && pnpm run build` |
| **Start Command** | `cd artifacts/localfood-ai && pnpm run serve` |
| **Plan** | `Free` |

### 2.3 Environment Variables

1. Click **"Advanced"** to expand environment variables
2. Add the following (all required):

| Key | Value |
|-----|-------|
| `VITE_API_URL` | `https://localfood-api.onrender.com` |
| `PORT` | `3000` |
| `BASE_PATH` | `/` |
| `NODE_ENV` | `production` |

**Important:** Replace `localfood-api` in the VITE_API_URL with your actual backend service URL from Step 1.

### 2.4 Deploy
Click **"Create Web Service"** → Wait 3-5 minutes

**Your app is now live at:** `https://localfood-web.onrender.com`

---

## Step 3: Verify Deployment

1. Open `https://localfood-web.onrender.com`
2. You should see the LocalFood AI interface
3. Try a search: *"I'm vegetarian and want Punjabi food in Jalandhar"*
4. Verify the agent responds with recommendations

### If you get API errors:

1. Check backend API status in Render dashboard
2. Verify `VITE_API_URL` environment variable in frontend service
3. Check logs: Click service → Logs tab

---

## Step 4: API URL Configuration (Automatic)

The frontend automatically reads the `VITE_API_URL` environment variable set in Step 2.3.

### If Frontend Can't Reach Backend:

1. **Verify environment variables** are set correctly in frontend service settings
   - Click `localfood-web` service → Environment tab
   - Check that `VITE_API_URL` points to the correct backend URL
   
2. **Rebuild frontend** (Render will auto-do this on env var change)
   - Click **"Manual Deploy"** → **"Deploy latest commit"**
   - Or push a new commit to GitHub (Render auto-redeploys)

3. **Check backend service status**
   - Click `localfood-api` service
   - Scroll to Logs section
   - Verify service is running and responding

---

## Services Deployed

✅ **Backend API**: Node.js + Python agent loop  
✅ **Frontend**: React + Vite  
✅ **Database**: Local JSON (restaurants.json in repo)  
✅ **Memory**: JSON-backed session store

## Monitoring & Logs

### Backend Logs
1. Render Dashboard → Click `localfood-api`
2. Scroll to **"Logs"** section
3. Watch real-time logs from all requests

### Frontend Logs
1. Render Dashboard → Click `localfood-web`
2. Scroll to **"Logs"** section

## Auto-Deploy on Push

Both services have `autoDeploy: true` configured:

```bash
git push origin main
```

Render automatically:
1. Detects the push
2. Triggers builds
3. Deploys new versions (2-5 minutes)

No manual intervention needed!

## Common Issues & Solutions

### **"Cannot find module"**
- Usually means missing dependencies
- Solution: Clear Render cache and rebuild
  1. Service settings → Clear build cache
  2. Manual deploy or push new commit

### **API returns 404**
- Backend service might be sleeping (free tier sleeps after 15 min inactivity)
- Solution: Make a request to wake it up, or upgrade to paid tier

### **Frontend loads but can't search**
- Check `VITE_API_URL` environment variable
- Check backend service is running (check logs)
- Browser console should show exact error

### **Python agent errors**
- Backend service needs Python 3
- Render includes Python by default
- Check backend logs for errors

## Upgrade to Production (Optional)

When ready for actual production:

1. **Upgrade services from Free to Starter** ($7/month each)
   - No more auto-sleep
   - 1GB RAM
   - Persistent storage option

2. **Add a database** (PostgreSQL, MongoDB, etc.)
   - Currently using local JSON files
   - Works fine for demo, but file-based session store

3. **Add SSL certificate** (auto-generated by Render)

## Next Steps

1. ✅ Push code to GitHub (done)
2. ✅ Create Render.com account
3. ✅ Deploy backend service
4. ✅ Deploy frontend service
5. ✅ Test the live application
6. ✅ Share URL with instructor for viva

---

## Support

- **Render Docs**: https://render.com/docs
- **GitHub Issues**: https://github.com/ayushdwivedi230/local-food-recommender/issues

Good luck! 🚀
