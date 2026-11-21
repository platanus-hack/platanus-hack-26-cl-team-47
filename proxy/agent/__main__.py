"""python -m proxy.agent --task "<texto>" --mcp "python -m proxy.server" [--max-steps 30]"""

from __future__ import annotations

import argparse
import asyncio

from .llm import AnthropicLLM
from .loop import run_agent


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m proxy.agent")
    ap.add_argument("--task", required=True)
    ap.add_argument("--mcp", default="python -m proxy.server", help="comando del servidor MCP (stdio)")
    ap.add_argument("--max-steps", type=int, default=30)
    ap.add_argument("--session-id", default=None, help="por defecto SESSION_ID o uno nuevo")
    args = ap.parse_args()

    result = asyncio.run(run_agent(args.task, args.mcp, AnthropicLLM(), args.max_steps, args.session_id))
    print(f"[sesión {result.session_id}] {result.stopped} en {result.steps} pasos")
    print(result.final_text)


if __name__ == "__main__":
    main()
