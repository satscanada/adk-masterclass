from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_registry import AGENTS_FILE, get_agent, list_agents


def main() -> None:
    payload = json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
    expected_agents = payload["agents"]

    registered_agents = list_agents()

    assert len(registered_agents) == len(expected_agents), registered_agents

    for expected in expected_agents:
        registered = get_agent(expected["key"])
        assert registered.title == expected["title"], registered
        assert registered.description == expected["description"], registered
        assert registered.prompt_hint == expected.get("prompt_hint", ""), registered
        assert registered.supports_streaming == bool(expected.get("supports_streaming", False)), registered

    try:
        get_agent("does_not_exist")
    except KeyError:
        pass
    else:
        raise AssertionError("Expected KeyError for an unknown agent key.")

    print("Agent registry smoke test passed.")
    print(f"Loaded agents from: {AGENTS_FILE}")
    for agent in registered_agents:
        print(f"- {agent.key}: {agent.title}")


if __name__ == "__main__":
    main()
