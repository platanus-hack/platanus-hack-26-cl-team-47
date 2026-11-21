"""Web simulada (web.test), puerto 8105.

    uvicorn services.web_sim.app:app --port 8105

GET /{ruta}                  -> 200 con la página | 404
PUT /_admin/pages/{ruta}     cuerpo = contenido  -> 200 {"path", "bytes"}   planta una página
GET /_admin/pages            -> 200 [rutas]

Todo en memoria. Las páginas iniciales (legítimas o con contenido no confiable)
se cargan desde una carpeta con load_seeds() o con la variable WEB_SIM_SEEDS:
cada archivo de la carpeta se sirve en su ruta relativa. «/» sirve index.html
si existe.
"""

from __future__ import annotations

import mimetypes
import os
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response


def _norm(path: str) -> str:
    p = path.strip("/")
    return p or "index.html"


class PageStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._pages: dict[str, bytes] = {}

    def put(self, path: str, content: bytes) -> str:
        key = _norm(path)
        with self._lock:
            self._pages[key] = content
        return key

    def get(self, path: str) -> bytes | None:
        with self._lock:
            return self._pages.get(_norm(path))

    def paths(self) -> list[str]:
        with self._lock:
            return sorted(self._pages)


def load_seeds(store: PageStore, folder: str | os.PathLike) -> int:
    """Planta cada archivo de la carpeta (recursivo) en su ruta relativa. Devuelve cuántos."""
    root = Path(folder)
    count = 0
    for f in sorted(p for p in root.rglob("*") if p.is_file()):
        store.put(f.relative_to(root).as_posix(), f.read_bytes())
        count += 1
    return count


def _content_type(path: str) -> str:
    ctype, _ = mimetypes.guess_type(path)
    if ctype is None:
        ctype = "text/html"
    if ctype.startswith("text/") or ctype in ("application/json", "application/javascript"):
        ctype += "; charset=utf-8"
    return ctype


def create_app(store: PageStore | None = None, seeds: str | os.PathLike | None = None) -> FastAPI:
    store = store if store is not None else PageStore()
    seeds = seeds if seeds is not None else os.environ.get("WEB_SIM_SEEDS")
    if seeds:
        load_seeds(store, seeds)

    app = FastAPI(title="web.test")
    app.state.store = store

    # Las rutas de administración van antes de la ruta comodín.
    @app.get("/_admin/pages")
    def list_pages():
        return store.paths()

    @app.put("/_admin/pages/{path:path}")
    async def plant(path: str, request: Request):
        if not path.strip("/"):
            raise HTTPException(status_code=400, detail="ruta vacía")
        key = store.put(path, await request.body())
        return {"path": key, "bytes": len(store.get(key) or b"")}

    @app.get("/{path:path}")
    def page(path: str):
        content = store.get(path)
        if content is None:
            raise HTTPException(status_code=404, detail="page not found")
        return Response(content=content, media_type=_content_type(_norm(path)))

    return app


app = create_app()
