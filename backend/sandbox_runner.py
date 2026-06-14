"""
Sandbox runner — entrypoint for the Docker agent sandbox container.

This script is COPY-ed into the sandbox image and runs as the container's
CMD.  It reads the game-state JSON from stdin, loads the user's agent script
(mounted at /sandbox/agent.py), and writes the chosen move as JSON to stdout.

Supported agent interfaces
--------------------------
Style A — stdin/stdout script (most common):
    The agent calls sys.stdin.read() itself and prints JSON to stdout.
    When we detect the agent has its own ``if __name__ == "__main__"`` block,
    we exec the script via subprocess so it gets a clean stdin.

Style B — functional interface:
    The agent exposes one of:
        get_move(game_state: dict) -> str
        get_move(game_state: dict) -> dict   # {"move": "..."}
    We import the module, call get_move, and emit the result ourselves.

Output on success:   {"move": "<move_string>"}
Output on error:     {"error": "<message>"}   (exit code 1)
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys

AGENT_PATH = os.environ.get("AGENT_PATH", "/sandbox/agent.py")


def _read_stdin() -> dict:
    raw = sys.stdin.buffer.read()
    if not raw:
        raise ValueError("No input received on stdin")
    return json.loads(raw)


def _run_style_a(agent_path: str, payload: dict) -> dict:
    """
    Run the agent as a subprocess so it owns stdin.
    Only used when the agent script explicitly reads stdin itself.
    """
    import subprocess

    proc = subprocess.run(
        [sys.executable, agent_path],
        input=json.dumps(payload).encode(),
        capture_output=True,
        timeout=8.0,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode(errors="replace")
        raise RuntimeError(f"Agent exited with code {proc.returncode}: {stderr[:200]}")

    output = proc.stdout.decode(errors="replace").strip()
    if not output:
        raise RuntimeError("Agent produced no output")

    return json.loads(output)


def _run_style_b(agent_path: str, payload: dict) -> dict:
    """Import the agent module and call get_move(game_state)."""
    spec = importlib.util.spec_from_file_location("_user_agent", agent_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {agent_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    if not hasattr(module, "get_move"):
        raise AttributeError("Agent does not define get_move(state)")

    result = module.get_move(payload)

    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        return {"move": result}
    raise TypeError(f"get_move returned unexpected type: {type(result)}")


def main() -> None:
    try:
        payload = _read_stdin()
    except Exception as exc:
        print(json.dumps({"error": f"stdin parse error: {exc}"}))
        sys.exit(1)

    if not os.path.isfile(AGENT_PATH):
        print(json.dumps({"error": f"Agent not found at {AGENT_PATH}"}))
        sys.exit(1)

    # Detect which interface style the agent uses
    try:
        with open(AGENT_PATH, encoding="utf-8") as fh:
            source = fh.read()
    except Exception as exc:
        print(json.dumps({"error": f"Cannot read agent: {exc}"}))
        sys.exit(1)

    uses_stdin = "stdin" in source or '__name__ == "__main__"' in source or "__main__" in source

    try:
        if uses_stdin:
            result = _run_style_a(AGENT_PATH, payload)
        else:
            result = _run_style_b(AGENT_PATH, payload)

        if "move" not in result:
            raise ValueError(f"Agent response missing 'move' key: {result}")

        print(json.dumps(result))

    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
