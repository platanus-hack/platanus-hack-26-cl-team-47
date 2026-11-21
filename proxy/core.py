"""Núcleo del proxy: ToolCall -> decide -> registro -> ejecutar o bloquear."""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from contracts import Decision, Event, ToolCall, load_hosts, write_event

from . import tools as T
from .decide import allow_all

DEFAULT_WORKSPACE = "demo/repo"
TOOL_NAMES = ("read_file", "list_dir", "http_request", "git", "github_issue", "github_comment")

DecideFn = Callable[[ToolCall], Decision]


def default_workspace() -> str:
    return os.environ.get("AGENT_WORKSPACE", DEFAULT_WORKSPACE)


class Proxy:
    def __init__(
        self,
        workspace: str | None = None,
        decide: DecideFn = allow_all,
        session_id: str | None = None,
        hosts: dict[str, str] | None = None,
    ):
        self.workspace = str(Path(workspace or default_workspace()).resolve())
        self.decide = decide
        self.session_id = session_id or os.environ.get("SESSION_ID") or uuid.uuid4().hex[:12]
        self.hosts = hosts if hosts is not None else load_hosts()
        self.t = 0

    # --- Metadatos del ToolCall ---------------------------------------

    def _resources(self, tool: str, args: dict[str, Any]) -> list[str]:
        if tool in ("read_file", "list_dir"):
            try:
                return [T.workspace_relative(self.workspace, str(args.get("path", ".")))]
            except T.ToolError:
                return [str(args.get("path", ""))]
        if tool == "http_request":
            return [T.url_host(str(args.get("url", "")))]
        if tool in ("github_issue", "github_comment"):
            return [T.GITHUB_HOST]
        if tool == "git":
            return ["git"]
        return []

    @staticmethod
    def _is_sink(tool: str, args: dict[str, Any]) -> bool:
        if tool in ("http_request", "github_issue", "github_comment"):
            return True
        if tool == "git":
            return "push" in (args.get("args") or [])
        return False

    def _untrusted(self, tool: str, args: dict[str, Any]) -> bool:
        if tool == "http_request":
            return T.url_host(str(args.get("url", ""))) in T.UNTRUSTED_HOSTS
        return tool in ("github_issue", "github_comment")

    # --- Ejecución ----------------------------------------------------

    def _execute(self, tool: str, args: dict[str, Any]) -> str:
        if tool == "read_file":
            return T.read_file(self.workspace, args["path"])
        if tool == "list_dir":
            return T.list_dir(self.workspace, args.get("path", "."))
        if tool == "http_request":
            return T.http_request(self.hosts, args.get("method", "GET"), args["url"],
                                  args.get("headers") or {}, args.get("body") or "")
        if tool == "git":
            return T.git(self.workspace, args.get("args") or [])
        if tool == "github_issue":
            return T.github_issue(self.hosts, args["repo"], args["title"], args["body"])
        if tool == "github_comment":
            return T.github_comment(self.hosts, args["repo"], args["number"], args["body"])
        raise T.ToolError(f"herramienta desconocida: {tool}")

    def _log(self, kind: str, call_id: str, data: Any) -> None:
        write_event(Event(ts=time.time(), session_id=self.session_id, source="proxy",
                          kind=kind, call_id=call_id, data=data))

    def handle(self, tool: str, args: dict[str, Any]) -> tuple[str, Decision]:
        self.t += 1
        call = ToolCall(
            id=f"{self.session_id}-{self.t:04d}", t=self.t, tool=tool, args=dict(args),
            output=None, resources=self._resources(tool, args),
            is_sink=self._is_sink(tool, args), untrusted=self._untrusted(tool, args),
            session_id=self.session_id, label=None,
        )
        t0 = time.perf_counter()
        decision = self.decide(call)
        decision = decision.model_copy(update={"latency_ms": (time.perf_counter() - t0) * 1000})
        self._log("tool_call", call.id, call.model_dump())
        self._log("decision", call.id, decision.model_dump())

        if not decision.allowed:
            return f"BLOQUEADA por el proxy: {decision.reason or decision.action}", decision
        try:
            output = self._execute(tool, args)
        except T.ToolError as e:
            output = f"ERROR: {e}"
        except (KeyError, TypeError, ValueError) as e:
            output = f"ERROR: argumentos inválidos para {tool}: {e}"
        return output, decision
