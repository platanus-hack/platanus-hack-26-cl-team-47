"""GitHub simulado (github.test), puerto 8104.

    uvicorn services.github_sim.app:app --port 8104

POST /repos/{owner}/{repo}/issues                    {"title","body"} -> 201 {"number","title","body"}
GET  /repos/{owner}/{repo}/issues                    -> 200 [issue]
GET  /repos/{owner}/{repo}/issues/{number}           -> 200 issue | 404
POST /repos/{owner}/{repo}/issues/{number}/comments  {"body"} -> 201 {"id","body"}
GET  /repos/{owner}/{repo}/issues/{number}/comments  -> 200 [comment]

GET  /_admin/published                               -> 200 lo que se escribió (no las semillas)

Todo en memoria. Las semillas (issues y comentarios iniciales, legítimos o
envenenados) se cargan desde una carpeta con load_seeds() o con la variable
GITHUB_SIM_SEEDS. Lo que se escribe queda guardado: es un sumidero, y
/_admin/published permite leer después qué publicó el agente.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


@dataclass
class _Comment:
    id: int
    body: str
    seeded: bool
    created_at: float

    def public(self) -> dict:
        return {"id": self.id, "body": self.body}


@dataclass
class _Issue:
    number: int
    title: str
    body: str
    seeded: bool
    created_at: float
    comments: list[_Comment] = field(default_factory=list)

    def public(self) -> dict:
        return {"number": self.number, "title": self.title, "body": self.body}


class GitHubStore:
    """Issues por repositorio (numeración propia de cada repo, desde 1) y sus comentarios."""

    def __init__(self):
        self._lock = threading.Lock()
        self._repos: dict[str, list[_Issue]] = {}
        self._next_comment_id = 1

    @staticmethod
    def _key(owner: str, repo: str) -> str:
        return f"{owner}/{repo}"

    def create_issue(self, owner: str, repo: str, title: str, body: str, seeded: bool = False) -> _Issue:
        with self._lock:
            issues = self._repos.setdefault(self._key(owner, repo), [])
            issue = _Issue(number=len(issues) + 1, title=title, body=body, seeded=seeded, created_at=time.time())
            issues.append(issue)
            return issue

    def list_issues(self, owner: str, repo: str) -> list[_Issue]:
        with self._lock:
            return list(self._repos.get(self._key(owner, repo), []))

    def get_issue(self, owner: str, repo: str, number: int) -> _Issue | None:
        with self._lock:
            issues = self._repos.get(self._key(owner, repo), [])
            return issues[number - 1] if 1 <= number <= len(issues) else None

    def add_comment(self, owner: str, repo: str, number: int, body: str, seeded: bool = False) -> _Comment | None:
        with self._lock:
            issues = self._repos.get(self._key(owner, repo), [])
            if not 1 <= number <= len(issues):
                return None
            comment = _Comment(id=self._next_comment_id, body=body, seeded=seeded, created_at=time.time())
            self._next_comment_id += 1
            issues[number - 1].comments.append(comment)
            return comment

    def published(self) -> dict:
        """Issues y comentarios escritos por clientes (no las semillas), en orden de creación."""
        with self._lock:
            issues, comments = [], []
            for repo, items in self._repos.items():
                for it in items:
                    if not it.seeded:
                        issues.append({"repo": repo, **it.public(), "created_at": it.created_at})
                    for c in it.comments:
                        if not c.seeded:
                            comments.append({"repo": repo, "number": it.number, **c.public(),
                                             "created_at": c.created_at})
            issues.sort(key=lambda x: x["created_at"])
            comments.sort(key=lambda x: x["created_at"])
            return {"issues": issues, "comments": comments}


def load_seeds(store: GitHubStore, folder: str | os.PathLike) -> int:
    """Carga semillas desde los *.json de la carpeta (en orden de nombre). Formato de cada archivo:

        {"repo": "empresa/servicio",
         "issues": [{"title": "...", "body": "...", "comments": ["...", ...]}, ...]}

    Devuelve cuántos issues cargó. Los números de issue siguen el orden de carga.
    """
    count = 0
    for path in sorted(Path(folder).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        owner, _, repo = str(data["repo"]).partition("/")
        if not owner or not repo:
            raise ValueError(f"{path}: 'repo' debe ser owner/repo")
        for item in data.get("issues", []):
            issue = store.create_issue(owner, repo, item.get("title", ""), item.get("body", ""), seeded=True)
            for body in item.get("comments", []):
                store.add_comment(owner, repo, issue.number, body, seeded=True)
            count += 1
    return count


class IssueIn(BaseModel):
    title: str
    body: str = ""


class CommentIn(BaseModel):
    body: str


def create_app(store: GitHubStore | None = None, seeds: str | os.PathLike | None = None) -> FastAPI:
    store = store if store is not None else GitHubStore()
    seeds = seeds if seeds is not None else os.environ.get("GITHUB_SIM_SEEDS")
    if seeds:
        load_seeds(store, seeds)

    app = FastAPI(title="github.test")
    app.state.store = store

    @app.get("/_admin/published")
    def published():
        return store.published()

    @app.post("/repos/{owner}/{repo}/issues", status_code=201)
    def create_issue(owner: str, repo: str, req: IssueIn):
        return store.create_issue(owner, repo, req.title, req.body).public()

    @app.get("/repos/{owner}/{repo}/issues")
    def list_issues(owner: str, repo: str):
        return [i.public() for i in store.list_issues(owner, repo)]

    @app.get("/repos/{owner}/{repo}/issues/{number}")
    def get_issue(owner: str, repo: str, number: int):
        issue = store.get_issue(owner, repo, number)
        if issue is None:
            raise HTTPException(status_code=404, detail="issue not found")
        return issue.public()

    @app.post("/repos/{owner}/{repo}/issues/{number}/comments", status_code=201)
    def add_comment(owner: str, repo: str, number: int, req: CommentIn):
        comment = store.add_comment(owner, repo, number, req.body)
        if comment is None:
            raise HTTPException(status_code=404, detail="issue not found")
        return comment.public()

    @app.get("/repos/{owner}/{repo}/issues/{number}/comments")
    def list_comments(owner: str, repo: str, number: int):
        issue = store.get_issue(owner, repo, number)
        if issue is None:
            raise HTTPException(status_code=404, detail="issue not found")
        return [c.public() for c in issue.comments]

    return app


app = create_app()
