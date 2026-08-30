# LocalFood AI - Quick Start Guide (Windows)

## Issue Summary
The project has build tool compatibility issues on Windows due to:
1. Native binary mismatches (esbuild, rollup)
2. Unix shell scripts in npm scripts (`export`, `sh` not available on Windows)
3. Platform-specific postinstall script failures

## Solution: Deploy to the Cloud

### Recommended: Replit (Easiest)

Replit runs on Linux and already has the project configured (see `.replit` file).

**Steps:**
1. Go to https://replit.com/signup
2. Connect your GitHub account
3. Create a new Replit project from your GitHub repository: `ayushdwivedi230/local-food-recommender`
4. Replit will automatically detect `.replit` configuration
5. Click "Run" or the play button
6. Your app will be live at `https://[your-username].replit.dev`

### Alternative: Railway.app

1. Go to https://railway.app
2. Click "New Project" → "Deploy from GitHub"
3. Select `ayushdwivedi230/local-food-recommender`
4. Railway will auto-detect the pnpm workspace
5. Set environment variables if needed
6. Deploy and get a live URL

### Alternative: Vercel + Render

**Frontend (Vercel):**
1. https://vercel.com → Import Project
2. Select the GitHub repo
3. Set build command: `cd artifacts/localfood-ai && pnpm build`
4. Set output dir: `artifacts/localfood-ai/dist`

**Backend (Render.com):**
1. https://render.com → New → Web Service
2. Connect GitHub repo
3. Set start command: `cd artifacts/api-server && pnpm start`
4. Configure API_URL in Vercel environment variables

## For Local Development (Windows)

If you need to work locally, use Windows Subsystem for Linux (WSL):

```powershell
# Install WSL2 (Windows Terminal)
wsl --install

# In WSL terminal:
cd /mnt/c/Users/ad475/Downloads/LocalFood-AI-Agent/LocalFood-AI-Agent
pnpm install
pnpm run build
pnpm --filter @workspace/api-server run dev &
pnpm --filter @workspace/localfood-ai run dev
```

Then open http://localhost:5173

## What's Deployed

✅ Backend API (`api-server`) - Python agent + Node.js API
✅ Frontend (`localfood-ai`) - React + Vite
✅ Local restaurant dataset (Punjabi cities)
✅ Session memory system
✅ All T13 requirements met

## Environment Variables Needed

Copy `.env.example`:
```
OPENAI_API_KEY=sk-... (optional - for future LLM backing)
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
LOCALFOOD_PYTHON=python3
```

## Next Steps

1. **Choose a platform** (Replit recommended for easiest setup)
2. **Connect GitHub** to your chosen platform
3. **Deploy** - usually just one click
4. **Test** the live application
5. **Share the URL** with your instructor for viva demonstration
