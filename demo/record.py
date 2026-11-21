"""Video de respaldo de la demo (tarea 15m), generado por script y reproducible.

    python demo/record.py --demo goteo    --out demo/out/respaldo_goteo.mp4
    python demo/record.py --demo enjambre --out demo/out/respaldo_enjambre.mp4
    python demo/record.py --demo base64   --out demo/out/respaldo_base64.mp4
        [--frames-dir <carpeta>] [--every <k>]

Levanta un servidor estático temporal sobre demo/viz (127.0.0.1, puerto libre), captura
split.html?…&t=<n> para cada t con un Chrome sin interfaz a 1280×720 y une los cuadros
con ffmpeg (3 cuadros por segundo, el último sostenido 6 s, H.264 yuv420p, sin audio).

Binarios: CHROME_BIN, o chrome-headless-shell de la caché de Playwright, o Chrome,
Chromium o Edge instalados. FFMPEG_BIN, o ffmpeg del PATH, o el de la caché de
Playwright. Con libx264 graba MP4 (H.264); si el ffmpeg solo trae libvpx (el de
Playwright), graba WebM con VP8 y cambia la extensión de salida a .webm, avisando.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
VIZ = ROOT / "demo" / "viz"
FPS, HOLD_S, SIZE = 3, 6, (1280, 720)

DEMOS = {
    "goteo": {"query": "", "fixture": "fixtures/real_right.jsonl"},
    "enjambre": {"query": "demo=enjambre", "fixture": "fixtures/swarm_right.jsonl"},
    "base64": {"query": "left=fixtures/enc_base64_left.jsonl&right=fixtures/enc_base64_right.jsonl",
               "fixture": "fixtures/enc_base64_right.jsonl"},
}


class MissingBinary(RuntimeError):
    pass


# ------------------------------------------------------------------ URL y cuadros


def frame_url(base: str, demo: str, t) -> str:
    """URL de split.html para la demo en la posición t (un entero o "end")."""
    q = DEMOS[demo]["query"]
    return f"{base}/split.html?{q + '&' if q else ''}t={quote(str(t))}"


def times(demo: str, viz: Path = VIZ) -> list[int]:
    """Valores de t de la demo, de 1 al final, leídos del fixture versionado."""
    ts = set()
    for line in (viz / DEMOS[demo]["fixture"]).read_text(encoding="utf-8").splitlines():
        if line.strip():
            ev = json.loads(line)
            if ev.get("kind") == "tool_call":
                ts.add(int(ev["data"]["t"]))
    return sorted(ts)


def sample(ts: list[int], every: int) -> list[int]:
    """Uno de cada k cuadros, siempre con el último (el del 200 y el 401)."""
    out = ts[::max(1, every)]
    if ts and out[-1] != ts[-1]:
        out.append(ts[-1])
    return out


# ------------------------------------------------------------------ binarios


def _playwright_caches(env=os.environ, home: Path | None = None) -> list[Path]:
    home = home or Path.home()
    dirs = [home / "Library" / "Caches" / "ms-playwright", home / ".cache" / "ms-playwright"]
    if env.get("LOCALAPPDATA"):
        dirs.append(Path(env["LOCALAPPDATA"]) / "ms-playwright")
    return dirs


def _globs(dirs: list[Path], patterns: list[str]) -> list[Path]:
    found = []
    for d in dirs:
        if d.is_dir():
            for pat in patterns:
                found += sorted(d.glob(pat), reverse=True)  # la versión más nueva primero
    return [p for p in found if p.is_file()]


SYSTEM_BROWSERS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]
BROWSER_NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"]


def find_chrome(env=os.environ, home: Path | None = None, which=shutil.which) -> tuple[Path, bool]:
    """(ruta, es_headless_shell). Orden: CHROME_BIN, caché de Playwright, navegadores instalados."""
    if env.get("CHROME_BIN"):
        p = Path(env["CHROME_BIN"])
        if not p.is_file():
            raise MissingBinary(f"CHROME_BIN apunta a {p}, que no existe.")
        return p, "headless-shell" in p.name or "headless_shell" in p.name
    shells = _globs(_playwright_caches(env, home), [
        "chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell",
        "chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell.exe",
        "chromium_headless_shell-*/chrome-*/headless_shell", "chromium_headless_shell-*/chrome-*/headless_shell.exe"])
    if shells:
        return shells[0], True
    for cand in SYSTEM_BROWSERS:
        if Path(cand).is_file():
            return Path(cand), False
    for name in BROWSER_NAMES:
        if which(name):
            return Path(which(name)), False
    raise MissingBinary("Falta el navegador: no encontré Chrome, Chromium, Edge ni chrome-headless-shell. "
                        "Instala uno o indica la ruta con CHROME_BIN=/ruta/al/chrome.")


def encoders(ffmpeg: Path) -> str:
    """Salida de `ffmpeg -encoders` ("" si no se puede ejecutar)."""
    try:
        r = subprocess.run([str(ffmpeg), "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return r.stdout


def codec_of(listing: str) -> str | None:
    """libx264 si está; si no, libvpx (VP8, WebM); si no, None."""
    for codec in ("libx264", "libvpx"):
        if codec in listing.split():
            return codec
    return None


def find_ffmpeg(env=os.environ, home: Path | None = None, which=shutil.which, probe=encoders) -> tuple[Path, str]:
    """(ruta, códec). Orden: FFMPEG_BIN, PATH, caché de Playwright. Prefiere uno con libx264;
    si ninguno lo tiene, el primero con libvpx."""
    if env.get("FFMPEG_BIN"):
        p = Path(env["FFMPEG_BIN"])
        if not p.is_file():
            raise MissingBinary(f"FFMPEG_BIN apunta a {p}, que no existe.")
        codec = codec_of(probe(p))
        if not codec:
            raise MissingBinary(f"FFMPEG_BIN={p} no trae libx264 ni libvpx.")
        return p, codec
    cands = [Path(which("ffmpeg"))] if which("ffmpeg") else []
    cands += [p for p in _globs(_playwright_caches(env, home), ["ffmpeg-*/ffmpeg*"]) if p.suffix in ("", ".exe")]
    found = [(p, codec_of(probe(p))) for p in cands]
    for want in ("libx264", "libvpx"):
        for p, codec in found:
            if codec == want:
                return p, codec
    extra = f" Probé sin libx264 ni libvpx: {', '.join(str(p) for p in cands)}." if cands else ""
    raise MissingBinary("Falta ffmpeg (con libx264 para MP4, o al menos libvpx para WebM)." + extra +
                        " Instálalo (brew install ffmpeg, apt install ffmpeg) o indica la ruta con "
                        "FFMPEG_BIN=/ruta/al/ffmpeg.")


# ------------------------------------------------------------------ servidor y grabación


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(directory: Path):
    """Servidor estático en 127.0.0.1 y un puerto libre. Devuelve (httpd, base_url)."""
    handler = functools.partial(_Quiet, directory=str(directory))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def chrome_cmd(chrome: Path, shell: bool, png: Path, url: str) -> list[str]:
    cmd = [str(chrome)]
    if not shell:
        cmd.append("--headless=new")
    cmd += ["--disable-gpu", "--hide-scrollbars", f"--window-size={SIZE[0]},{SIZE[1]}",
            "--virtual-time-budget=4000", f"--screenshot={png}", url]
    return cmd


def webm_cmd(ffmpeg: Path, out: Path) -> list[str]:
    """VP8 en WebM leyendo JPEG por la entrada estándar (el ffmpeg de Playwright no lee PNG
    ni archivos sueltos: solo image2pipe con mjpeg). El final se sostiene repitiendo el cuadro."""
    return [str(ffmpeg), "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg",
            "-i", "pipe:0", "-c:v", "libvpx", "-b:v", "1M", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an", str(out)]


def output_path(out: Path, codec: str) -> Path:
    return out.with_suffix(".webm") if codec == "libvpx" and out.suffix != ".webm" else out


def ffmpeg_cmd(ffmpeg: Path, frames: Path, n: int, out: Path) -> list[str]:
    """Cuadros f00001.png… a 3 por segundo; el último se sostiene 6 s (tpad clona el final)."""
    return [str(ffmpeg), "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "f%05d.png"),
            "-vf", f"tpad=stop_mode=clone:stop_duration={HOLD_S},scale={SIZE[0]}:{SIZE[1]}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an", str(out)]


def record(demo: str, out: Path, frames_dir: Path | None = None, every: int = 1) -> Path:
    chrome, shell = find_chrome()
    ffmpeg, codec = find_ffmpeg()
    webm = codec == "libvpx"
    if webm:
        new = output_path(out, codec)
        print(f"aviso: {ffmpeg} no trae libx264; grabo WebM (VP8) en {new}", file=sys.stderr)
        out = new
    ext = "jpeg" if webm else "png"
    ts = sample(times(demo), every)
    tmp = None
    if frames_dir is None:
        tmp = tempfile.TemporaryDirectory(prefix="respaldo_")
        frames_dir = Path(tmp.name)
    frames_dir.mkdir(parents=True, exist_ok=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    httpd, base = serve(VIZ)
    try:
        with tempfile.TemporaryDirectory(prefix="chrome_") as profile:
            for i, t in enumerate(ts, 1):
                png = frames_dir / f"f{i:05d}.{ext}"
                url = frame_url(base, demo, "end" if t == ts[-1] else t)
                cmd = chrome_cmd(chrome, shell, png, url)
                cmd.insert(1, f"--user-data-dir={profile}")
                subprocess.run(cmd, capture_output=True, timeout=60)
                if not png.is_file():
                    raise RuntimeError(f"El navegador no generó el cuadro t={t} ({url}).")
                print(f"\r{demo}: cuadro {i}/{len(ts)}", end="", file=sys.stderr, flush=True)
        print(file=sys.stderr)
        if webm:
            imgs = [frames_dir / f"f{i:05d}.jpeg" for i in range(1, len(ts) + 1)]
            imgs += [imgs[-1]] * (HOLD_S * FPS)  # el último cuadro, sostenido 6 s
            data = b"".join(p.read_bytes() for p in imgs)
            r = subprocess.run(webm_cmd(ffmpeg, out), input=data, capture_output=True)
            err = r.stderr.decode("utf-8", "replace")
        else:
            r = subprocess.run(ffmpeg_cmd(ffmpeg, frames_dir, len(ts), out), capture_output=True, text=True)
            err = r.stderr
        if r.returncode != 0 or not out.is_file():
            raise RuntimeError(f"ffmpeg falló: {err.strip()}")
    finally:
        httpd.shutdown()
        httpd.server_close()
        if tmp is not None:
            tmp.cleanup()
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python demo/record.py")
    ap.add_argument("--demo", choices=sorted(DEMOS), required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--frames-dir", type=Path, default=None, help="conserva los PNG en esta carpeta")
    ap.add_argument("--every", type=int, default=1, help="captura uno de cada k cuadros (por defecto 1)")
    args = ap.parse_args(argv)
    try:
        out = record(args.demo, args.out, args.frames_dir, args.every)
    except MissingBinary as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"{out}: {out.stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
