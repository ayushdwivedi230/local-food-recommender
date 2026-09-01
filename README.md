# LocalFood AI

LocalFood AI is a stateful, tool-using restaurant recommendation agent built around a transparent Plan → Act → Observe → Decide loop. The project is designed to demonstrate how a small but real agent can understand natural-language food requests, persist user preferences across turns, call tools at runtime, apply hard guardrails, rank safe options, and explain its reasoning.

It is built for a local food recommendation use case and uses a deterministic restaurant dataset instead of relying on external API calls for the demo. The system is intentionally explainable, robust, and easy to evaluate in a viva or classroom setting.

## Why this project matters

This project shows the practical difference between a static recommendation script and a genuine agent:

- it understands user intent from natural language
- it remembers previous preferences in session memory
- it chooses which tools to call at runtime
- it observes tool results before deciding on the next step
- it enforces safety constraints before ranking
- it explains why a recommendation was selected

## Project highlights

- Single-agent architecture in Python
- Real runtime tool calls: `find_restaurants(city)` and `filter_by_cuisine(type)`
- Session-based memory across multiple turns
- Dietary, spice, budget, cuisine, and location handling
- Hard constraint enforcement before ranking
- Explicit dislike and exclusion logic
- Explainable outputs with score breakdowns and reasons
- Honest failure behavior when no safe match exists
- Frontend + API integration ready for local use and deployment

---

## Architecture

The agent follows a clear decision cycle:

1. Detect intent
2. Read session memory
3. Extract preferences from the latest message
4. Plan the required actions
5. Call the relevant tools
6. Observe tool results
7. Apply hard guardrails
8. Rank the remaining matches
9. Return the final recommendation and trace

```text
User Message
    ↓
Intent Classification
    ↓
Session Memory Load
    ↓
Preference Extraction
    ↓
PLAN
    ↓
find_restaurants(city)
    ↓
OBSERVE
    ↓
filter_by_cuisine(type)
    ↓
OBSERVE
    ↓
Guardrails + Validation
    ↓
RANK
    ↓
DECIDE
    ↓
Recommendation + Explanation + Trace
```

This keeps the logic transparent and demonstrates true agentic behavior rather than a hard-coded list of restaurants.

---

## Core features

### Preference understanding

The agent can understand and maintain preferences such as:

- vegetarian / vegan / Jain / non-vegetarian
- preferred cuisine
- disliked cuisine
- spice preference (mild, medium, spicy)
- budget limit
- city or location

### Guardrails

Hard constraints are enforced before ranking, including:

- dietary compatibility
- explicit dislikes
- required cuisine exclusions
- no fabricated restaurants when data is missing

### Explainability

Each recommendation includes:

- restaurant name
- cuisine
- diet compatibility
- rating
- price range
- distance
- score
- score breakdown
- explicit reason for recommendation

### Multi-turn memory

The system stores preferences in session memory so the user does not need to repeat the same constraints every turn.

### Honest failure handling

If a city is unknown, no restaurants match, or constraints are incompatible, the agent reports the issue clearly instead of making up a recommendation.

---

## Tech stack

### Backend

- Python
- JSON-backed session memory
- deterministic restaurant dataset
- tool-based recommendation logic

### API layer

- TypeScript
- Express
- API routes for chat and memory interactions

### Frontend

- React
- Vite
- TypeScript
- Tailwind-based UI components

### Package management

- pnpm

---

## Repository structure

```text
LocalFood-AI-Agent/
├── backend/
│   ├── agent.py
│   ├── memory.py
│   ├── tools.py
│   ├── main.py
│   └── data/
│       ├── restaurants.json
│       └── sessions.json
├── artifacts/
│   ├── api-server/
│   └── localfood-ai/
├── demo.ipynb
├── IMPROVEMENT_SUMMARY.md
├── package.json
├── pnpm-lock.yaml
├── pnpm-workspace.yaml
├── README.md
├── RENDER_DEPLOYMENT.md
├── requirements.txt
├── tsconfig.base.json
├── tsconfig.json
└── ...
```

---

## Local setup

### Prerequisites

- Python 3.9+
- Node.js
- pnpm

### Install dependencies

```bash
pnpm install
```

### Start the backend API

```bash
pnpm --filter @workspace/api-server run dev
```

### Start the frontend

```bash
pnpm --filter @workspace/localfood-ai run dev
```

### Optional: run the Python agent directly

```bash
python backend/main.py
```

---

## Testing

The project includes a dedicated unit suite and end-to-end integration checks.

### Run unit tests

```bash
python backend/test_agent.py
```

### Run integration tests

```bash
python backend/integration_test.py
```

These tests cover:

- greetings and capability requests
- preference extraction
- multi-turn memory
- budget and cuisine filtering
- dislike handling
- dietary conflicts
- no-result scenarios
- backward compatibility and schema validation

---

## Example conversation flows

### Example 1

> I am vegetarian and I want Punjabi food in Phagwara under 400 rupees.

The agent will:

- detect city: Phagwara
- detect cuisine: Punjabi
- detect dietary preference: vegetarian
- detect budget: 400
- search restaurants
- filter results by cuisine
- enforce dietary and budget constraints
- rank candidates
- return the best match with an explanation

### Example 2

> Actually, I don't like too much spice.

The agent will:

- update the remembered spice preference to mild
- preserve existing constraints
- recommend accordingly

### Example 3

> I don't like Chinese food anymore.

The agent will:

- remove Chinese from the candidate pool
- continue using prior preferences
- recommend a safe alternative

---

## Deployment

This project is configured for deployment through Render. See [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) for deployment details.

The production flow is conceptually:

```text
Browser
  ↓
React Frontend
  ↓
Express API
  ↓
Python Agent
  ↓
Restaurant Data + Tools
```

---

## Viva-ready summary

This project demonstrates a real, transparent agentic workflow that is appropriate for discussion in a technical assessment:

- The system has a single agent
- It makes runtime tool calls
- It keeps memory across turns
- It follows a visible reasoning loop
- It applies hard constraints before ranking
- It explains its recommendations
- It avoids fabricating answers when constraints are impossible

This makes the project stronger than a simple recommendation function because it shows actual agent behavior, not just a lookup result.

---

## License

This project is intended for educational and demonstration purposes within the local food recommender assignment.

---

## Contact / contribution

This repository is a demonstration project and is suitable for local experimentation and academic review. Contributions and improvements are welcome as long as they preserve the project’s focus on transparency, correctness, and explainability.

Spice Negation

The agent distinguishes between:

"I like spicy food."

and:

"I don't like spicy food."

The first produces:

spicePreference = spicy

while the second produces:

spicePreference = mild

This prevents the word spicy from being incorrectly interpreted as a positive preference when it occurs inside a negative statement.

🧠 Persistent Session Memory

LocalFood AI uses a small JSON-backed session memory implementation.

The memory module is located at:

backend/memory.py

The stored session fields are:

Field	Purpose
diet	Dietary requirement
preferredCuisine	Preferred cuisine
dislikedCuisine	Cuisine to avoid
spicePreference	Mild or spicy
budget	Maximum preferred meal price
location	Last known/search city
updatedAt	Last memory update timestamp

Memory is associated with a session_id.

Therefore different conversations can maintain independent preference states.

💬 Multi-Turn Conversation

One of the main demonstrations of the project is cross-turn memory.

Example:

Turn 1:
I am vegetarian and I like Punjabi food in Phagwara.

The agent stores:

diet = vegetarian
preferredCuisine = Punjabi
location = Phagwara

Then the user says:

Turn 2:
Suggest something.

The agent can reuse the remembered preferences instead of asking the user to repeat them.

Another example:

Turn 1:
I want Chinese food in Phagwara under ₹500.

Turn 2:
I don't like spicy food.

Turn 3:
Suggest something.

The final recommendation can use the combined session state:

location = Phagwara
cuisine = Chinese
budget = ₹500
spicePreference = mild
🧩 Two Required Tools

The project intentionally uses two simple Python tools.

They are implemented in:

backend/tools.py
Tool 1 — find_restaurants
find_restaurants(city: str) -> list
Role

Searches the local restaurant dataset for a city.

Example:

find_restaurants("Phagwara")

The function reads:

backend/data/restaurants.json

and returns matching restaurant records.

Tool 2 — filter_by_cuisine
filter_by_cuisine(type: str) -> list
Role

Filters the previous restaurant-search observation by cuisine.

Example:

filter_by_cuisine("Chinese")

The tool operates on the result produced by:

find_restaurants(city)

This establishes a meaningful dependency between tool calls.

🍽️ Restaurant Dataset

The project uses a local structured restaurant dataset.

Each restaurant contains information such as:

id
name
city
cuisine
diet
rating
average_price
price_range
spice_level
distance_km
description

This allows the agent to perform deterministic filtering and ranking without fabricating external restaurant information.

The dataset is intentionally local so the course demonstration can be:

Reproducible
Fast
Deterministic
Independent of external restaurant APIs
📊 Recommendation Ranking

After hard constraints are applied, remaining restaurants are scored.

The ranking considers:

Cuisine       → 30%
Diet          → 30%
Rating        → 15%
Budget        → 10%
Taste/Spice   → 10%
Distance      → 5%

The exact score is exposed through:

score
scoreBreakdown

This makes the recommendation explainable.

For example:

Cuisine: 0.300
Diet:    0.300
Rating:  0.141
Budget:  0.100
Taste:   0.100
Distance:0.043

The final score is converted into a value out of 100.

🔍 Explainable Recommendations

The agent does not only return a restaurant name.

It also provides a reason such as:

Recommended because it matches your Chinese preference,
is compatible with a vegetarian diet,
has a 4.1 rating,
fits your ₹500 budget,
and it's only 3.1 km away.

This makes the recommendation easier to understand during both normal use and the course demonstration.

🗺️ Supported Locations

The current local dataset supports:

Jalandhar
Phagwara
Ludhiana
Amritsar
Chandigarh
Delhi
Bengaluru

Common aliases are also supported.

For example:

Bangalore → Bengaluru
Koramangala → Bengaluru
Indiranagar → Bengaluru

Unknown locations are not fabricated.

🍜 Supported Cuisines

The current supported cuisine vocabulary includes:

Punjabi
North Indian
South Indian
Chinese
Italian
Mughlai
Street Food
Fast Food
Cafe
Jain

Common natural-language forms such as:

Chinese food
Punjabi food
Italian food
North Indian food

are normalized to the supported cuisine names.

💰 Budget Understanding

The agent understands common budget expressions such as:

under ₹500
below ₹500
less than ₹500
up to ₹500
within ₹500
budget ₹500

The extracted budget is stored in session memory and contributes to ranking.

🌶️ Spice Preference

The agent supports positive and negative spice preferences.

Positive
I like spicy food.
I want something hot.
I want spicy food.

Stored as:

spicePreference = spicy
Negative
I don't like spicy food.
I want less spicy food.
I don't want too much spice.

Stored as:

spicePreference = mild

This distinction is handled before positive keyword matching.

👋 Conversation Handling

The system first determines whether the message requires the restaurant agent.

Greetings

Examples:

Hi
Hello
Hey
Namaste
Good morning

These receive a conversational response without unnecessary restaurant tool calls.

Capability Requests

Examples:

What can you do?
How do you work?
Help
What are your features?

The agent explains:

Available tools
Memory
Guardrails
Ranking
Recommendation process
Food Requests

Examples:

I am hungry.
Find vegetarian food in Delhi.
I want Chinese food in Phagwara.
Suggest something spicy under ₹500.

These enter the full agentic loop.

❌ Honest Failure Handling

The agent is designed not to fabricate results.

1. Unknown City

If the dataset contains no restaurant entries for a city:

I couldn't find restaurants in <city>.

The agent does not invent a restaurant.

2. No Safe Match

If restaurants exist but none satisfy the hard requirements, the agent reports the failure.

Example:

I found restaurants in Jalandhar,
but none matched Chinese while satisfying
your Jain-friendly requirement.

The system does not silently weaken the dietary requirement.

3. Dietary Conflict

If the session remembers:

diet = vegetarian

and a later request asks for:

non-vegetarian food

the agent detects the conflict before making an unsafe recommendation.

It asks the user whether the dietary preference should be changed.

4. Tool Failure

The restaurant tool contains a demonstration error path for:

simulate tool error

If the tool raises an exception, the agent returns a safe failure message rather than fabricating restaurant data.

This provides a useful viva demonstration of error handling.

🔬 Agent Trace

The API response contains an observable execution trace.

Important trace stages include:

Intent
Memory
Plan
Tool Call
Tool Result
Guardrail
Ranking
Final Recommendation

The frontend displays this as Agent Activity.

This allows the user and evaluator to see what the agent did rather than only seeing the final answer.

🖥️ Frontend

The project includes a React/Vite frontend.

The frontend displays:

Chat conversation
Restaurant recommendations
Match score
Rating
Price
Distance
Cuisine
Dietary information
Recommendation explanation
Agent activity
Execution trace

The frontend communicates with the API server through the application's API routes.

🏗️ Project Structure
LocalFood-AI-Agent/
│
├── backend/
│   ├── agent.py
│   ├── memory.py
│   ├── tools.py
│   │
│   └── data/
│       ├── restaurants.json
│       └── sessions.json
│
├── artifacts/
│   ├── api-server/
│   └── localfood-ai/
│
├── demo.ipynb
├── package.json
├── pnpm-workspace.yaml
├── pnpm-lock.yaml
├── RENDER_DEPLOYMENT.md
└── README.md
⚙️ Technology Stack
Backend
Python
JSON-backed session memory
Deterministic restaurant tools
API Layer
Node.js
Express
TypeScript
Frontend
React
Vite
TypeScript
Package Management
pnpm
Deployment
Render
🚀 Running the Project Locally

Install dependencies:

pnpm install

Start the API server:

pnpm --filter @workspace/api-server run dev

Start the frontend:

pnpm --filter @workspace/localfood-ai run dev

Python 3 is required for the agent bridge.

If Python is installed under a different executable name, configure:

LOCALFOOD_PYTHON
🌐 Deployment

The project is configured for deployment through Render.

Deployment documentation:

RENDER_DEPLOYMENT.md

The production architecture is:

Browser
   ↓
React Frontend
   ↓
Express API
   ↓
Python Agent
   ↓
Restaurant Tools
   ↓
Local JSON Dataset

The deployed application therefore uses the same core agent logic as the local demonstration.

🧪 Testing Scenarios

The following scenarios can be used to demonstrate the system.

Test 1 — Basic Recommendation
I want vegetarian food in Phagwara.

Expected:

Restaurant search
→ dietary filtering
→ ranking
→ recommendation
Test 2 — Cuisine Filtering
I want Chinese food in Phagwara.

Expected:

find_restaurants()
→ filter_by_cuisine("Chinese")
→ rank
Test 3 — Cross-Turn Memory
Turn 1:
I am vegetarian and I like Punjabi food in Phagwara.

Turn 2:
Suggest something.

Expected:

The agent reuses the remembered preferences.

Test 4 — Budget
I want vegetarian Chinese food in Phagwara under ₹500.

Expected:

Budget contributes to the ranking and recommendations.

Test 5 — Negative Spice
I don't like spicy food.

Expected:

spicePreference = mild
Test 6 — Disliked Cuisine
I don't like Chinese food.

Expected:

Chinese restaurants are excluded from recommendations.

Test 7 — Combined Preferences
I'm vegetarian and I want Chinese food in Phagwara under ₹500.
I don't like spicy food.

Expected remembered state:

diet = vegetarian
preferredCuisine = Chinese
spicePreference = mild
budget = ₹500
location = Phagwara
Test 8 — Unknown City
I want food in Mumbai.

Expected:

No fabricated restaurant is returned.

Test 9 — Tool Error
simulate tool error

Expected:

The tool error is handled safely without fabricated data.

📓 Notebook Demonstration

The project includes:

demo.ipynb

Run:

jupyter notebook demo.ipynb

or open the notebook in JupyterLab.

The notebook can demonstrate:

Full recommendation flow
Cross-turn memory
Dietary conflict handling
Honest no-match behavior

The notebook provides an additional way to demonstrate the agent independently of the web interface.

🎓 Viva Explanation

A concise explanation of the project is:

LocalFood AI is a single-agent local food recommender that follows a Plan → Act → Observe → Decide architecture. It reads persistent session memory, extracts user preferences, plans the required actions, calls find_restaurants() and filter_by_cuisine() at runtime, observes their results, applies hard dietary and dislike guardrails, ranks only safe candidates, and returns an explainable recommendation.

Why is it agentic?

Because the system does not execute one fixed recommendation function.

The next action depends on the current state and the observation produced by the previous action.

For example:

If city is known
    → search restaurants

If cuisine is known
    → filter the observation

If dietary restrictions exist
    → enforce them

If safe candidates remain
    → rank them

Otherwise
    → report the failure honestly
What is the role of memory?

Memory allows preferences from previous turns to influence future decisions.

What are the hard constraints?

Dietary requirements and explicitly disliked cuisines are enforced before ranking.

Why use a local dataset?

It makes the course demonstration deterministic, reproducible, fast, and resistant to fabricated external data.

Why expose the agent trace?

It makes the reasoning process observable and demonstrates that tools were actually called at runtime.

🔐 API Keys and Security

The deterministic demonstration mode does not require an external AI API key.

If an external provider is configured for future experimentation, credentials should be stored in environment variables.

Never put API keys in:

Frontend source code
GitHub
README files
Restaurant dataset
Client-side JavaScript

Never commit:

.env

or other files containing secrets.

📌 Design Principles

The project follows several important design principles:

1. Tool Grounding

Recommendations are based on the local restaurant dataset rather than fabricated restaurants.

2. Statefulness

Preferences persist across turns through session memory.

3. Hard Constraints

Safety-related requirements are applied before ranking.

4. Explainability

Recommendations contain reasons and score breakdowns.

5. Honest Failure

When no safe answer exists, the system says so.

6. Observable Agent Behavior

The execution trace exposes the agent's decisions and tool calls.

7. Deterministic Demonstration

The course version does not depend on unpredictable external restaurant APIs.

📈 Future Improvements

Possible future extensions include:

Larger restaurant datasets
Real restaurant APIs
Real-time availability
Geographic distance calculations
User authentication
Database-backed memory
More sophisticated natural-language understanding
LLM-based planning
Personalized recommendation learning
Restaurant opening-hours awareness
Real-time pricing
Multilingual food queries

These are potential extensions and are not required for the current deterministic course demonstration.

👨‍💻 Assessment Summary

LocalFood AI demonstrates the following core concepts:

Requirement	Implementation
Single agent	backend/agent.py
Agentic loop	Plan → Act → Observe → Decide
Runtime tools	find_restaurants() and filter_by_cuisine()
Persistent memory	backend/memory.py
Structured dataset	restaurants.json
Dietary guardrail	Hard filtering before ranking
Negative preference handling	dislikedCuisine exclusion
Preference handling	Diet, cuisine, spice, budget, location
Explainability	Reasons + score breakdown
Failure handling	Unknown city, no match, conflict, tool error
Multi-turn behavior	JSON-backed session memory
Observable execution	Agent activity + trace
Web interface	React/Vite frontend
API	Express/TypeScript
Deployment	Render
🏁 Conclusion

LocalFood AI demonstrates how a small recommendation problem can be implemented as an agentic system rather than a simple lookup application.

The agent maintains state, chooses actions, invokes tools, observes results, enforces constraints, evaluates candidates, and makes a final recommendation.

The combination of:

Memory
+
Planning
+
Runtime Tools
+
Observation
+
Guardrails
+
Ranking
+
Explainability

forms the core of the LocalFood AI demonstration.

LocalFood AI

A transparent, stateful, tool-using local food recommendation agent.


### One correction I deliberately made

I **didn't claim that Gemini/OpenAI is currently powering the recommendation**, because your actual `agent.py`, `memory.py`, and `tools.py` show a deterministic Python agent. Your existing README also explicitly says no API key is required for Demo Mode.

That is actually **better for the viva**: if your teacher asks *"Where is the AI?"*, you can explain the agentic architecture instead of getting trapped trying to prove that an LLM generated the recommendations.

### To replace your README

Save the above as:

```text
README.md