"""Hook PreToolUse de Claude Code: el contador de bits de Alicanto sobre Bash, WebFetch y Read (#169).

    PYTHONPATH=/ruta/a/alicanto SECRETS_MANIFEST=/ruta/a/secretos.json python3 -m integrations.claude_code.hook

Claude Code escribe en stdin un JSON por llamada (session_id, cwd, hook_event_name, tool_name, tool_input).
El hook decide antes de que la herramienta se ejecute:
  - permitir: código 0 y nada en stdout;
  - negar:    código 0 y {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                          "permissionDecisionReason": "Alicanto: <motivo>"}} en stdout.

Claude Code lanza un proceso por llamada: nada queda en memoria. La cuenta por clave vive en
<ALICANTO_STATE_DIR>/ledger.json (el mismo mecanismo que LEDGER_PATH en el proxy en vivo, importado de
proxy/live.py: SharedLedger, ledger_lock, la sincronización con el gestor y vault_rotator). Lo que el
detector guarda por sesión y la cuenta no conserva (modo escalado, último pedido de rotación, contador de
llamadas) va en <ALICANTO_STATE_DIR>/sesiones/<session_id>.json. Cada llamada queda en hook.jsonl, sin
valores de secretos ni el texto completo de los comandos.

Variables: SECRETS_MANIFEST (obligatoria), ALICANTO_STATE_DIR (por defecto <cwd>/.alicanto), VAULT_URL
(opcional: con ella rota en el gestor; sin ella no hay con qué rotar y, al llegar al umbral, niega).

Usa los parámetros por defecto del detector (el contador de bits, con rotación al 30 % de la clave) y la
regla directa de abajo; no el modelo de evidencia de la evaluación.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from contracts import ToolCall

MAX_READ_CHARS = 200_000
LOG_PREFIX_CHARS = 80
UNKNOWN_URL = "http://desconocido.invalid/"
URL_RE = re.compile(r"https?://[^\s'\"<>|;)]+", re.IGNORECASE)
NET_RE = re.compile(r"\b(curl|wget|nc|ncat|ssh|scp|sftp|ftp|telnet)\b|\bgit\s+push\b", re.IGNORECASE)
SINK_TOOLS = ("WebFetch",)


# --------------------------------------------------------------------------- manifiesto

def load_manifest(path: str | None) -> dict:
    if not path:
        raise ValueError("falta SECRETS_MANIFEST")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data.get("secrets"), list) or not data["secrets"]:
        raise ValueError(f"{path}: el manifiesto no trae «secrets»")
    return data


def manifest_files(manifest: dict) -> list[str]:
    out: list[str] = []
    for s in manifest["secrets"]:
        for f in s.get("files", []):
            if f not in out:
                out.append(f)
    return out


def allowed_hosts(manifest: dict) -> set[str]:
    return {h.lower() for s in manifest["secrets"] for h in s.get("allowed_hosts", [])}


# --------------------------------------------------------------------------- de Claude Code a ToolCall

def bash_goes_out(command: str) -> bool:
    return bool(URL_RE.search(command) or NET_RE.search(command))


def named_files(command: str, manifest: dict) -> list[str]:
    return [f for f in manifest_files(manifest) if f and f in command]


def _host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def to_toolcall(payload: dict, manifest: dict, t: int = 1) -> ToolCall | None:
    """La llamada de Claude Code como ToolCall (tabla del issue #169). None si la herramienta no se mira."""
    tool = payload.get("tool_name") or ""
    inp = payload.get("tool_input") or {}
    if not isinstance(inp, dict):
        inp = {}
    sid = str(payload.get("session_id") or "sesion")
    cwd = str(payload.get("cwd") or ".")
    base = dict(id=f"{sid}-{t:05d}", t=t, session_id=sid, label=None, output=None)

    if tool == "Read":
        fp = str(inp.get("file_path") or "")
        try:
            rel = os.path.relpath(fp, cwd) if fp else ""
        except ValueError:          # otra unidad en Windows
            rel = fp
        rel = rel.replace("\\", "/")
        return ToolCall(tool="read_file", args={"path": rel}, resources=[rel] if rel else [], is_sink=False,
                        untrusted=False, **base)
    if tool == "WebFetch":
        url = str(inp.get("url") or "")
        return ToolCall(tool="http_request", args={"method": "GET", "url": url, "body": str(inp.get("prompt") or "")},
                        resources=[_host(url)], is_sink=True, untrusted=True, **base)
    if tool == "Bash":
        command = str(inp.get("command") or "")
        files = named_files(command, manifest)
        if bash_goes_out(command):
            m = URL_RE.search(command)
            url = m.group(0) if m else UNKNOWN_URL
            host = _host(url)
            return ToolCall(tool="http_request", args={"method": "SHELL", "url": url, "body": command},
                            resources=[host, *files], is_sink=True,
                            untrusted=host not in allowed_hosts(manifest), **base)
        return ToolCall(tool="read_file", args={"path": files[0] if files else "", "command": command},
                        resources=files, is_sink=False, untrusted=False, **base)
    return None


def read_output(payload: dict) -> str:
    """Salida de un Read: el hook corre antes de ejecutarlo, así que lee el archivo él mismo."""
    fp = str((payload.get("tool_input") or {}).get("file_path") or "")
    try:
        with open(fp, encoding="utf-8", errors="replace") as f:
            return f.read(MAX_READ_CHARS)
    except (OSError, ValueError):
        return ""


# --------------------------------------------------------------------------- estado por sesión

def _session_file(state_dir: Path, session_id: str) -> Path:
    name = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:24]
    return state_dir / "sesiones" / f"{name}.json"


class Engine:
    """Detector con la cuenta compartida en disco. Un objeto por proceso; con persist=True (el hook real)
    vuelve a cargar y guarda todo en cada llamada, así un proceso por llamada decide igual que uno solo."""

    def __init__(self, manifest_path: str, state_dir: str | Path, vault_url: str | None = None, client=None):
        from engine.detector import Detector, SharedLedger
        from proxy.live import vault_rotator, _vault_value, vault_timeout

        self.manifest_path = manifest_path
        self.manifest = load_manifest(manifest_path)
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_path = str(self.state_dir / "ledger.json")
        empty = self.state_dir / "grafo-vacio"   # el grafo de archivos solo alimenta el modelo, que aquí no se usa
        empty.mkdir(exist_ok=True)
        self.ledger = SharedLedger.from_manifest(manifest_path)
        self.client = client
        if vault_url and client is None:
            import httpx

            self.client = httpx.Client(base_url=vault_url.rstrip("/"), timeout=vault_timeout())
        if self.client is not None:
            rotate = vault_rotator(vault_url or "http://vault.test", client=self.client)
            self.value_of = lambda sid: _vault_value(self.client, sid)
        else:
            rotate = self._no_vault
            self.value_of = self._no_vault
        self.detector = Detector(str(empty), manifest_path, ledger=self.ledger, rotate=rotate)
        self.sessions: dict[str, dict] = {}

    @staticmethod
    def _no_vault(secret_id: str) -> str:
        from proxy.live import RotationError

        raise RotationError(secret_id, "no hay gestor de secretos configurado (VAULT_URL)")

    # -- estado por sesión que el ledger no guarda
    def _load_session(self, sid: str) -> dict:
        if sid not in self.sessions:
            f = _session_file(self.state_dir, sid)
            try:
                self.sessions[sid] = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self.sessions[sid] = {"t": 0, "escalated": {}, "last_request": {}}
        st = self.sessions[sid]
        d = self.detector
        for k in d.escalated:
            d.escalated[k] = bool(st["escalated"].get(k, False))
            d._last_request[k] = int(st["last_request"].get(k, -10**9))
        return st

    def _save_session(self, sid: str, st: dict) -> None:
        d = self.detector
        st["escalated"] = {k: bool(v) for k, v in d.escalated.items()}
        st["last_request"] = {k: int(v) for k, v in d._last_request.items()}
        f = _session_file(self.state_dir, sid)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(st), encoding="utf-8")

    def decide(self, payload: dict) -> tuple[str, str, dict[str, float]]:
        """(allow | deny, motivo, bits por secreto). Read nunca se niega."""
        from proxy.live import RotationError, _sync_from_file, ledger_lock

        tool = payload.get("tool_name") or ""
        inp = payload.get("tool_input") or {}
        command = str(inp.get("command") or "") if isinstance(inp, dict) else ""
        if tool == "Bash" and bash_goes_out(command) and named_files(command, self.manifest):
            return "deny", f"el comando saca {', '.join(named_files(command, self.manifest))} hacia la red", {}

        sid = str(payload.get("session_id") or "sesion")
        with ledger_lock(self.ledger_path):
            _sync_from_file(self.ledger, self.ledger_path, self.value_of)
            st = self._load_session(sid)
            st["t"] += 1
            call = to_toolcall(payload, self.manifest, st["t"])
            if call is None:
                return "allow", "", {}
            try:
                dec = self.detector.decide(call)
                verdict = self._verdict(dec)
                bits = {k: v.bits for k, v in dec.leak.items() if v.bits}
            except RotationError as e:
                # Pidió rotar y no hay con qué (o el gestor falló): lo medido ya quedó en el ledger.
                state = self.ledger.bits.state()
                v = state.get(e.secret_id, {"bits": 0.0, "candidate_bits": 0.0})
                n = v["bits"] + v["candidate_bits"]
                verdict = ("allow", "") if not call.is_sink else \
                    ("deny", f"{n:.0f} bits de {e.secret_id} ya salieron: rota la clave ({e.reason})")
                bits = {k: v["bits"] + v["candidate_bits"] for k, v in state.items() if v["bits"] + v["candidate_bits"]}
            if tool == "Read":
                self.detector.set_output(call.id, read_output(payload))
                verdict = ("allow", "")
            self.ledger.save(self.ledger_path)
            self._save_session(sid, st)
        return verdict[0], verdict[1], bits

    def _verdict(self, dec) -> tuple[str, str]:
        if dec.action == "allow":
            return "allow", ""
        if dec.action.endswith("block"):
            return "deny", dec.reason or dec.action
        # rotate+allow: permitir solo si la rotación se hizo de verdad
        if self.detector.last_rotations:
            return "allow", ""
        sid, leak = max(dec.leak.items(), key=lambda kv: kv[1].bits)
        return "deny", f"{leak.bits:.0f} bits de {sid} ya salieron: rota la clave"


# --------------------------------------------------------------------------- registro y salida

def _safe_prefix(command: str, manifest: dict) -> str:
    """Los primeros 80 caracteres del comando, salvo que contengan un fragmento de un secreto."""
    head = command[:LOG_PREFIX_CHARS]
    for s in manifest.get("secrets", []):
        v = str(s.get("value") or "")
        if any(v[i:i + 4] in head for i in range(max(0, len(v) - 3))):
            return "[omitido: contiene un fragmento de un secreto]"
    return head


def log(state_dir: Path, payload: dict, verdict: str, reason: str, bits: dict, manifest: dict | None) -> None:
    inp = payload.get("tool_input") or {}
    entry: dict[str, Any] = {"ts": time.time(), "session_id": payload.get("session_id"),
                             "tool": payload.get("tool_name"), "decision": verdict, "reason": reason, "bits": bits}
    if payload.get("tool_name") == "Bash" and isinstance(inp, dict):
        entry["command"] = _safe_prefix(str(inp.get("command") or ""), manifest or {})
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        with open(state_dir / "hook.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def deny_json(reason: str) -> str:
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                              "permissionDecisionReason": f"Alicanto: {reason}"}},
                      ensure_ascii=False)


def is_sink_payload(payload: dict) -> bool:
    tool = payload.get("tool_name")
    if tool in SINK_TOOLS:
        return True
    inp = payload.get("tool_input") or {}
    return tool == "Bash" and isinstance(inp, dict) and bash_goes_out(str(inp.get("command") or ""))


def run_hook(stdin_text: str, env: dict | None = None, client=None) -> str:
    """Lo que el hook escribe en stdout ("" = permitir). No lanza: si algo falla, falla cerrado."""
    env = dict(os.environ if env is None else env)
    try:
        payload = json.loads(stdin_text or "{}")
        if not isinstance(payload, dict):
            raise ValueError("la entrada no es un objeto JSON")
    except ValueError:
        return ""   # no se entiende la entrada: no hay nada que mirar; no se cae
    if payload.get("hook_event_name", "PreToolUse") != "PreToolUse" or \
            payload.get("tool_name") not in ("Bash", "WebFetch", "Read"):
        return ""
    state_dir = Path(env.get("ALICANTO_STATE_DIR") or Path(str(payload.get("cwd") or ".")) / ".alicanto")
    manifest = None
    try:
        engine = Engine(env.get("SECRETS_MANIFEST") or "", state_dir, env.get("VAULT_URL") or None, client=client)
        manifest = engine.manifest
        verdict, reason, bits = engine.decide(payload)
    except Exception as e:  # noqa: BLE001 - falla cerrado, como fail_safe del proxy
        bits = {}
        if is_sink_payload(payload):
            verdict, reason = "deny", f"no se pudo decidir ({type(e).__name__}: {e}); se niega por seguridad"
        else:
            verdict, reason = "allow", ""
    log(state_dir, payload, verdict, reason, bits, manifest)
    return deny_json(reason) if verdict == "deny" else ""


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    out = run_hook(sys.stdin.read())
    if out:
        sys.stdout.write(out)
    sys.exit(0)


if __name__ == "__main__":
    main()
