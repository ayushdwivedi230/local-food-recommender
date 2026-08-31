# LocalFood AI

A single-agent, agentic local-food recommendation system built for the **T13 "Local Food Recommender" course assessment**.

LocalFood AI demonstrates an explicit **Plan → Act → Observe → Decide** agent loop using real Python tool functions, persistent session memory, hard safety guardrails, transparent ranking, and explainable recommendations.

The system accepts natural-language food requests such as:

> "I'm vegetarian, I want spicy Chinese food in Phagwara under ₹500."

It extracts the user's preferences, remembers them across turns, searches the local restaurant dataset, filters the results, applies hard constraints, ranks the remaining safe candidates, and explains why the recommendation was selected.

---

## 🎯 Project Objective

The objective of LocalFood AI is to demonstrate how an **agentic AI system** can solve a recommendation problem by maintaining state, deciding what action to take, observing tool results, applying constraints, and making a final decision.

Unlike a simple static recommendation function, the system:

- Understands natural-language requests
- Maintains user preferences across conversation turns
- Decides when restaurant tools are required
- Calls tools at runtime
- Uses the result of one tool as the input state for the next tool
- Applies hard dietary and dislike constraints
- Ranks only safe candidates
- Provides transparent explanations
- Handles missing data and tool failures honestly
- Produces an observable agent trace for demonstration and viva

---

# 🧠 Agent Architecture

The core architecture follows:

```text
                    User Message
                         │
                         ▼
                ┌─────────────────┐
                │ Intent Detection│
                └────────┬────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
       Conversation             Food Request
              │                     │
              ▼                     ▼
       Greeting / Help        Read Session Memory
                                      │
                                      ▼
                            Extract Preferences
                                      │
                                      ▼
                                    PLAN
                                      │
                                      ▼
                         find_restaurants(city)
                                      │
                                      ▼
                                   OBSERVE
                                      │
                                      ▼
                         filter_by_cuisine(type)
                                      │
                                      ▼
                                   OBSERVE
                                      │
                                      ▼
                       Disliked Cuisine Guardrail
                                      │
                                      ▼
                         Dietary Guardrail
                                      │
                                      ▼
                                   RANK
                                      │
                                      ▼
                                  DECIDE
                                      │
                                      ▼
                         Recommendation + Trace
                                      │
                                      ▼
                              Save Memory

The agent therefore does not simply return a hard-coded restaurant.

It performs a sequence of state-dependent actions and uses the observations from those actions to determine the next step.

🔄 Plan → Act → Observe → Decide Loop

For a typical request:

"I'm vegetarian and I want Chinese food in Phagwara under ₹500."

the agent performs the following process.

1. Read Memory

The agent retrieves the current session state from the JSON-backed memory store.

Example:

diet = vegetarian
preferredCuisine = Chinese
budget = 500
location = Phagwara
2. Extract New Preferences

The latest message is analysed for:

Diet
Cuisine
Disliked cuisine
Spice preference
Budget
Location

Only information present in the user's request is updated.

Previously remembered preferences remain available for later turns.

3. PLAN

The agent creates a plan based on the current state.

For example:

Search Phagwara
→ Filter Chinese
→ Enforce vegetarian requirement
→ Enforce budget
→ Rank safe candidates

If the user has explicitly disliked a cuisine, the plan also includes that exclusion.

4. ACT — find_restaurants(city)

The first required tool searches the restaurant dataset for the requested city.

find_restaurants(city)

Example:

find_restaurants("Phagwara")

returns the restaurants indexed for Phagwara.

5. OBSERVE

The agent inspects the result returned by the tool.

It does not assume that restaurants exist.

If zero restaurants are returned, the agent reports that honestly.

6. ACT — filter_by_cuisine(type)

If a cuisine was requested, the agent calls:

filter_by_cuisine(type)

This tool operates on the previous restaurant-search observation.

Therefore the intended tool sequence is:

find_restaurants(city)
        ↓
observation
        ↓
filter_by_cuisine(type)
        ↓
observation

This demonstrates a real tool-dependent agent workflow rather than two unrelated function calls.

7. Apply Hard Guardrails

Before ranking, the agent removes restaurants that violate hard constraints.

Dietary Guardrail

Supported dietary preferences include:

vegetarian
vegan-friendly
Jain-friendly
non-vegetarian

For example:

User: I am vegetarian.

A restaurant that does not satisfy the vegetarian requirement cannot become the final recommendation merely because it has a higher rating.

8. Disliked Cuisine Guardrail

Explicit negative preferences are also enforced.

For example:

User: I don't like Chinese food.

The agent stores:

dislikedCuisine = Chinese

and excludes Chinese restaurants from the recommendation set.

This prevents a previous positive preference from overriding an explicit negative preference.

For example:

Turn 1:
I like Chinese.

Turn 2:
I don't like Chinese anymore.

The explicit negative preference takes priority.

9. Decide and Rank

Only candidates that survive the hard constraints are ranked.

The ranking considers:

Cuisine match
Dietary compatibility
Rating
Budget
Spice preference
Distance

A transparent score breakdown is returned with every recommendation.

🛡️ Safety and Guardrails

LocalFood AI separates hard constraints from ranking preferences.

Hard constraints are enforced before ranking.

This is important because a restaurant should not receive a high recommendation score if it violates a user's dietary requirement or explicit exclusion.

The main guardrails are:

Dietary Safety
Vegetarian
Vegan
Jain
Non-vegetarian
Cuisine Exclusion
"I don't like Chinese."
"I hate Mughlai."
"Don't recommend Punjabi."

These explicit negative preferences remove matching cuisines from the candidate set.

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