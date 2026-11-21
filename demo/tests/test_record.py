"""Tests de demo/record.py (tarea 15m). Sin navegador salvo el test marcado."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "demo"))
import record  # noqa: E402


def test_urls_de_cada_demo():
    b = "http://127.0.0.1:1"
    assert record.frame_url(b, "goteo", 5) == f"{b}/split.html?t=5"
    assert record.frame_url(b, "enjambre", "end") == f"{b}/split.html?demo=enjambre&t=end"
    assert record.frame_url(b, "base64", 3) == (
        f"{b}/split.html?left=fixtures/enc_base64_left.jsonl&right=fixtures/enc_base64_right.jsonl&t=3")


def test_tiempos_de_1_al_final_y_muestreo():
    assert record.times("goteo") == list(range(1, 89))
    assert record.times("enjambre") == list(range(1, 91))
    s = record.sample(list(range(1, 89)), 20)
    assert s[0] == 1 and s[-1] == 88 and len(s) == 6


def fake(tmp_path, rel):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("")
    return p


def test_chrome_bin_manda(tmp_path):
    p = fake(tmp_path, "bin/mi-chrome")
    assert record.find_chrome(env={"CHROME_BIN": str(p)}, home=tmp_path, which=lambda n: None) == (p, False)
    with pytest.raises(record.MissingBinary, match="CHROME_BIN"):
        record.find_chrome(env={"CHROME_BIN": str(tmp_path / "no")}, home=tmp_path, which=lambda n: None)


def test_chrome_headless_shell_de_playwright(tmp_path, monkeypatch):
    monkeypatch.setattr(record, "SYSTEM_BROWSERS", [])
    p = fake(tmp_path, ".cache/ms-playwright/chromium_headless_shell-1200/chrome-headless-shell-linux64/chrome-headless-shell")
    assert record.find_chrome(env={}, home=tmp_path, which=lambda n: None) == (p, True)
    cmd = record.chrome_cmd(p, True, tmp_path / "f.png", "http://x")
    assert "--headless=new" not in cmd and "--window-size=1280,720" in cmd and "--virtual-time-budget=4000" in cmd
    assert "--headless=new" in record.chrome_cmd(p, False, tmp_path / "f.png", "http://x")


def test_falta_el_navegador(tmp_path, monkeypatch):
    monkeypatch.setattr(record, "SYSTEM_BROWSERS", [])
    with pytest.raises(record.MissingBinary, match="Falta el navegador.*CHROME_BIN"):
        record.find_chrome(env={}, home=tmp_path, which=lambda n: None)


X264 = " V....D libx264  libx264 H.264\n V....D libvpx  libvpx VP8"
VP8 = " V....D libvpx  libvpx VP8"


def test_codec_de_la_lista_de_encoders():
    assert record.codec_of(X264) == "libx264"
    assert record.codec_of(VP8) == "libvpx"
    assert record.codec_of(" V..... mjpeg") is None


# Líneas literales del ffmpeg de Playwright: ffmpeg-1011 (VP8) y ffmpeg-1013 (solo VP9).
LINEA_VP8 = " V....D libvpx               libvpx VP8 (codec vp8)"
LINEA_VP9 = " V....D libvpx-vp9           libvpx VP9 (codec vp9)"
LINEA_X264 = " V....D libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (codec h264)"
CABECERA = "Encoders:\n V..... = Video\n A..... = Audio\n ------\n"


def test_codec_mira_el_nombre_y_no_la_descripcion():
    # «libvpx» aparece en la descripción de libvpx-vp9: no por eso hay VP8.
    assert record.codec_of(CABECERA + LINEA_VP9) == "libvpx-vp9"
    assert record.codec_of(CABECERA + LINEA_VP8) == "libvpx"
    assert record.codec_of(CABECERA + LINEA_X264) == "libx264"
    assert record.codec_of(CABECERA + " V....D mjpeg                MJPEG (Motion JPEG)") is None
    assert record.codec_of("") is None
    # Orden de preferencia cuando hay varios.
    assert record.codec_of("\n".join([LINEA_VP9, LINEA_VP8])) == "libvpx"
    assert record.codec_of("\n".join([LINEA_VP9, LINEA_VP8, LINEA_X264])) == "libx264"


def test_ffmpeg_elige_el_mejor_codec_entre_candidatos(tmp_path):
    sistema = fake(tmp_path, "bin/ffmpeg")
    nuevo = fake(tmp_path, ".cache/ms-playwright/ffmpeg-1013/ffmpeg-linux")
    viejo = fake(tmp_path, ".cache/ms-playwright/ffmpeg-1011/ffmpeg-linux")
    listas = {str(sistema): " V....D mjpeg   MJPEG", str(nuevo): LINEA_VP9, str(viejo): LINEA_VP8}
    probe = lambda p: listas.get(str(p), "")
    assert record.find_ffmpeg(env={}, home=tmp_path, which=lambda n: str(sistema), probe=probe) == (viejo, "libvpx")
    listas[str(viejo)] = ""
    assert record.find_ffmpeg(env={}, home=tmp_path, which=lambda n: str(sistema), probe=probe) == (nuevo, "libvpx-vp9")
    assert record.find_ffmpeg(env={"FFMPEG_BIN": str(nuevo)}, home=tmp_path, which=lambda n: None,
                              probe=probe) == (nuevo, "libvpx-vp9")


def test_vp9_graba_webm():
    assert record.output_path(Path("demo/out/v.mp4"), "libvpx-vp9") == Path("demo/out/v.webm")
    j = " ".join(record.webm_cmd(Path("ffmpeg"), Path("o.webm"), "libvpx-vp9"))
    assert "-c:v libvpx-vp9" in j and "image2pipe" in j and "pipe:0" in j


def test_ffmpeg_prefiere_libx264_y_si_no_webm(tmp_path):
    bueno = fake(tmp_path, "bin/ffmpeg")
    pw = fake(tmp_path, "Library/Caches/ms-playwright/ffmpeg-1011/ffmpeg-mac")
    listas = {str(bueno): X264, str(pw): VP8}
    probe = lambda p: listas.get(str(p), "")
    assert record.find_ffmpeg(env={"FFMPEG_BIN": str(bueno)}, home=tmp_path, which=lambda n: None,
                              probe=probe) == (bueno, "libx264")
    assert record.find_ffmpeg(env={}, home=tmp_path, which=lambda n: str(bueno), probe=probe) == (bueno, "libx264")
    # Sin libx264 en ningún lado: el de Playwright, en WebM.
    assert record.find_ffmpeg(env={}, home=tmp_path, which=lambda n: None, probe=probe) == (pw, "libvpx")
    assert record.output_path(Path("demo/out/v.mp4"), "libvpx") == Path("demo/out/v.webm")
    assert record.output_path(Path("demo/out/v.mp4"), "libx264") == Path("demo/out/v.mp4")


def test_falta_ffmpeg(tmp_path):
    fake(tmp_path, "Library/Caches/ms-playwright/ffmpeg-1011/ffmpeg-mac")
    with pytest.raises(record.MissingBinary, match="Falta ffmpeg.*ffmpeg-mac.*FFMPEG_BIN"):
        record.find_ffmpeg(env={}, home=tmp_path, which=lambda n: None, probe=lambda p: " V..... mjpeg")
    with pytest.raises(record.MissingBinary, match="no trae libx264 ni libvpx"):
        record.find_ffmpeg(env={"FFMPEG_BIN": str(fake(tmp_path, "x/ffmpeg"))}, home=tmp_path,
                           which=lambda n: None, probe=lambda p: "")


def test_comando_webm():
    j = " ".join(record.webm_cmd(Path("ffmpeg"), Path("o.webm")))
    assert "image2pipe" in j and "-c:v mjpeg" in j and "-c:v libvpx" in j and "-an" in j and "pipe:0" in j


def test_comando_de_ffmpeg():
    cmd = record.ffmpeg_cmd(Path("ffmpeg"), Path("/f"), 10, Path("o.mp4"))
    j = " ".join(cmd)
    assert "-framerate 3" in j and "libx264" in j and "-pix_fmt yuv420p" in j and "-an" in j
    assert "stop_duration=6" in j


def _run(args, env=None, **kw):
    """El grabador como subproceso, en UTF-8 y leyendo con errors="replace" (Windows usa cp1252)."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})}
    return subprocess.run([sys.executable, str(ROOT / "demo" / "record.py"), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", env=env, **kw)


def test_mensaje_y_salida_si_falta_un_binario(tmp_path):
    r = _run(["--demo", "goteo", "--out", str(tmp_path / "v.mp4")], env={"CHROME_BIN": str(tmp_path / "no-existe")})
    assert r.returncode != 0 and "CHROME_BIN" in r.stderr


def test_lee_la_salida_de_una_consola_cp1252(tmp_path):
    # Lo que falló en Windows: el grabador escribe en cp1252 («ó» es el byte 0xf3) y el test leía
    # UTF-8 estricto. Con errors="replace" se lee igual y el resultado se puede comprobar.
    r = _run(["--demo", "goteo", "--out", str(tmp_path / "v.mp4")],
             env={"CHROME_BIN": str(tmp_path / "navegación"), "PYTHONIOENCODING": "cp1252"})
    assert r.returncode == 2 and "CHROME_BIN" in r.stderr and "Traceback" not in r.stderr


def test_safe_console_no_deja_que_imprimir_tumbe_el_grabador(monkeypatch):
    import io

    out = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", out)
    with pytest.raises(UnicodeEncodeError):
        print("v→.webm")  # sin el arreglo, «→» tumba el print en cp1252
    record.safe_console()
    print("v→.webm: 12 KB")
    out.flush()
    assert out.buffer.getvalue().rstrip() == b"v?.webm: 12 KB"


def _binarios():
    try:
        record.find_chrome()
        record.find_ffmpeg()
        return True
    except record.MissingBinary:
        return False


@pytest.mark.skipif(not _binarios(), reason="falta un navegador o un ffmpeg con libx264, libvpx o libvpx-vp9")
def test_graba_goteo(tmp_path):
    out = tmp_path / "respaldo_goteo.mp4"
    r = _run(["--demo", "goteo", "--every", "20", "--out", str(out)], timeout=600)
    assert r.returncode == 0, r.stderr
    hecho = out if out.is_file() else out.with_suffix(".webm")  # sin libx264 sale en WebM
    assert hecho.is_file() and hecho.stat().st_size > 10 * 1024
