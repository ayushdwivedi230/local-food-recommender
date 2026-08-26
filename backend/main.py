"""CLI bridge for the API server and an executable notebook-friendly agent."""

from __future__ import annotations

import json
import sys

from agent import run_agent
from memory import clear_memory, get_memory


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    action = payload.get("action", "chat")
    session_id = str(payload.get("sessionId", "demo-session"))
    if action == "memory":
        result = get_memory(session_id)
    elif action == "clear":
        result = clear_memory(session_id)
    else:
        message = str(payload.get("message", "")).strip()
        result = run_agent(session_id, message)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()