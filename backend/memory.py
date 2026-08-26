"""Small JSON-backed session memory for the LocalFood AI demonstration."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any

MEMORY_PATH = os.path.join(os.path.dirname(__file__), "data", "sessions.json")
EMPTY_MEMORY = {
    "diet": None,
    "preferredCuisine": None,
    "dislikedCuisine": None,
    "spicePreference": None,
    "budget": None,
    "location": None,
    "updatedAt": datetime.now(timezone.utc).isoformat(),
}


def _read_all() -> dict[str, dict[str, Any]]:
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_all(data: dict[str, dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix="sessions-", suffix=".json", dir=os.path.dirname(MEMORY_PATH))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(temp_path, MEMORY_PATH)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def get_memory(session_id: str) -> dict[str, Any]:
    memory = dict(EMPTY_MEMORY)
    memory.update(_read_all().get(session_id, {}))
    return memory


def save_memory(session_id: str, memory: dict[str, Any]) -> dict[str, Any]:
    memory = dict(EMPTY_MEMORY, **memory)
    memory["updatedAt"] = datetime.now(timezone.utc).isoformat()
    all_memory = _read_all()
    all_memory[session_id] = memory
    _write_all(all_memory)
    return memory


def clear_memory(session_id: str) -> dict[str, Any]:
    all_memory = _read_all()
    all_memory.pop(session_id, None)
    _write_all(all_memory)
    return dict(EMPTY_MEMORY)