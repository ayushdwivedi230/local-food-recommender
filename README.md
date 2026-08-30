# LocalFood AI

LocalFood AI is a **single-agent, agentic local-food recommender** built for the T13 "Local Food Recommender" course assessment. It demonstrates a real plan → act → observe → decide loop using two Python tool functions that are called at runtime — no simulated output.

## 🚀 Deploy Now

**[Deploy to Render.com →](RENDER_DEPLOYMENT.md)** (5 minutes, free tier available)

Or see [DEPLOYMENT.md](DEPLOYMENT.md) for other options (Replit, Railway, WSL).

## How it works

The agent runs a transparent multi-step loop for every food request:

1. **Read memory** — retrieve dietary preferences, cuisine, spice level, and budget from earlier turns
2. **Plan** — decide which tools to call based on available state
3. **Act** → call `find_restaurants(city)` — searches the local restaurant index for the requested city
4. **Observe** — inspect the list of restaurants returned
5. **Act** → call `filter_by_cuisine(type)` — narrows the observation to the preferred cuisine type
6. **Observe** — inspect the filtered list
7. **Apply dietary guardrail** — remove any restaurant that violates the user's remembered diet (vegetarian, vegan, Jain-friendly, or non-vegetarian)
8. **Rank and recommend** — score remaining candidates on cuisine match, diet, rating, budget, taste, and distance; return the top 5

## Two required tools

| Tool | Signature | Role |
|------|-----------|------|
| `find_restaurants` | `find_restaurants(city: str) → list` | Searches the local dataset for all restaurants in a given city |
| `filter_by_cuisine` | `filter_by_cuisine(type: str) → list` | Narrows the previous tool's observation to a specific cuisine type |

Both tools are plain Python functions in [`backend/tools.py`](backend/tools.py). The agent calls them in sequence — `filter_by_cuisine` operates on the in-memory result of `find_restaurants`, so the correct ordering is enforced by design.

## Memory

Preferences are persisted in a JSON-backed session store ([`backend/memory.py`](backend/memory.py)). The agent stores:

- **diet** — vegetarian / vegan-friendly / Jain-friendly / non-vegetarian
- **preferredCuisine** — e.g. Punjabi, South Indian
- **dislikedCuisine** — cuisines to avoid
- **spicePreference** — mild or spicy
- **budget** — maximum price per meal (₹)
- **location** — last city searched

On every subsequent turn, the agent reads this memory before planning. A dietary preference set in Turn 1 is used as a hard constraint in Turn 2, even if the user never mentions it again.

## Honest failure cases

During development, three honest failure modes are intentionally preserved:

1. **Unknown city** — `find_restaurants` returns an empty list; the agent stops and names the supported cities rather than fabricating results.
2. **Dietary conflict** — if a new request contradicts a remembered dietary requirement (e.g. asking for non-vegetarian food after storing `diet=vegetarian`), the agent refuses before calling any tools and explains the conflict.
3. **No matching result** — if the city has restaurants but none satisfy the cuisine + diet combination, the agent reports zero recommendations honestly. A live example: requesting Jain-friendly Chinese food in Jalandhar returns no match because the dataset has no such entry. The agent says so rather than lowering its standards silently.
4. **Tool error** — the `find_restaurants` tool raises a `RuntimeError` when the city string is `"simulate tool error"`. The API converts that to a safe user message without fabricating restaurant data. This path is available for viva demonstration.

## Conversation handling

The agent classifies every message before entering the agentic loop:

- **Greetings** ("Hello", "Hi", "Hey", "Namaste") → friendly reply, no tool calls
- **Capability query** ("What can you do?", "Help") → structured list of tools, memory, and guardrails
- **Food/preference requests** → full plan → act → observe → decide loop

## Run

```bash
pnpm install
pnpm --filter @workspace/api-server run dev
pnpm --filter @workspace/localfood-ai run dev
```

The web app is served at the project preview root and calls the shared `/api` service. Python 3 is required for the agent bridge. The default interpreter is `python3`; set `LOCALFOOD_PYTHON` if your environment uses a different executable.

## Environment

Copy `.env.example` if you want to configure an OpenAI-compatible provider for future provider-backed planning. No API key is needed for the fully functional deterministic Demo Mode used by the course presentation. Never put secrets in frontend code or commit `.env`.

## Notebook demo

Run `jupyter notebook demo.ipynb` (or open it in JupyterLab) and execute all cells top-to-bottom. The notebook contains **four demonstrations**:

1. **Full recommendation** — both tools fire in sequence; vegetarian guardrail applied; top-5 ranked
2. **Cross-turn memory** — Turn 1 stores vegetarian + Punjabi; Turn 2 provides only a city; agent applies remembered preferences without prompting
3. **Dietary conflict** — agent refuses non-vegetarian request after storing vegetarian; 0 recommendations; no tools called
4. **Honest no-match** — Jain-friendly Chinese in Jalandhar finds restaurants but none match; agent reports failure honestly