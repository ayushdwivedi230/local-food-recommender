# LocalFood AI

LocalFood AI is a reactive, agentic local-food recommender for the T13 “Local Food Recommender” travel project. It uses two real Python tools: `find_restaurants(city)` searches the fictional local restaurant index, and `filter_by_cuisine(type)` narrows the previous tool observation by cuisine. The API invokes the Python agent for every turn, so tool calls and their structured results are not simulated in the interface.

The agent remembers diet, preferred and disliked cuisine, spice preference, budget, and location in a session-backed JSON memory file. On later turns it reads those preferences before planning, treats diet as a hard constraint, then ranks safe results across cuisine, diet, rating, budget, taste, and distance. If an unknown city, empty match, tool error, or dietary conflict occurs, it stops honestly and explains why.

During development we intentionally exercised a tool failure path. The local search tool raised an error instead of returning fabricated restaurants; the API converted that failure into a user-safe message and kept the app running. This same explicit failure behavior is available for the demo by including “simulate tool error” in a request.

## Run

The project uses the existing workspace workflows:

```bash
pnpm install
pnpm --filter @workspace/api-server run dev
pnpm --filter @workspace/localfood-ai run dev
```

The web app is served at the project preview root and calls the shared `/api` service. Python 3 is required for the agent bridge. The default interpreter is `python3`; set `LOCALFOOD_PYTHON` if your environment uses a different executable.

## Environment

Copy `.env.example` if you want to configure an OpenAI-compatible provider for future provider-backed planning. No API key is needed for the fully functional deterministic Demo Mode used by the course presentation. Never put secrets in frontend code or commit `.env`.

## Notebook demo

Run `jupyter notebook demo.ipynb` (or open it in JupyterLab) and execute all cells top-to-bottom. It contains three demonstrations: a full vegetarian Punjabi recommendation, memory carried from one turn to the next, and a dietary conflict that is refused safely.