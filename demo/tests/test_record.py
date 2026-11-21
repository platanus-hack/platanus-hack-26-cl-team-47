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


def test_ffmpeg_solo_con_libx264(tmp_path):
    bueno = fake(tmp_path, "bin/ffmpeg")
    pw = fake(tmp_path, "Library/Caches/ms-playwright/ffmpeg-1011/ffmpeg-mac")
    ok = {str(bueno)}
    check = lambda p: str(p) in ok
    assert record.find_ffmpeg(env={"FFMPEG_BIN": str(bueno)}, home=tmp_path, which=lambda n: None, check=check) == bueno
    assert record.find_ffmpeg(env={}, home=tmp_path, which=lambda n: str(bueno), check=check) == bueno
    with pytest.raises(record.MissingBinary, match="Falta ffmpeg con libx264.*ffmpeg-mac.*FFMPEG_BIN"):
        record.find_ffmpeg(env={}, home=tmp_path, which=lambda n: None, check=check)
    with pytest.raises(record.MissingBinary, match="no trae libx264"):
        record.find_ffmpeg(env={"FFMPEG_BIN": str(pw)}, home=tmp_path, which=lambda n: None, check=check)


def test_comando_de_ffmpeg():
    cmd = record.ffmpeg_cmd(Path("ffmpeg"), Path("/f"), 10, Path("o.mp4"))
    j = " ".join(cmd)
    assert "-framerate 3" in j and "libx264" in j and "-pix_fmt yuv420p" in j and "-an" in j
    assert "stop_duration=6" in j


def test_mensaje_y_salida_si_falta_un_binario(tmp_path):
    env = {**os.environ, "CHROME_BIN": str(tmp_path / "no-existe")}
    r = subprocess.run([sys.executable, str(ROOT / "demo" / "record.py"), "--demo", "goteo",
                        "--out", str(tmp_path / "v.mp4")], capture_output=True, text=True, encoding="utf-8", env=env)
    assert r.returncode != 0 and "CHROME_BIN" in r.stderr


def _binarios():
    try:
        record.find_chrome()
        record.find_ffmpeg()
        return True
    except record.MissingBinary:
        return False


@pytest.mark.skipif(not _binarios(), reason="falta un navegador o un ffmpeg con libx264")
def test_graba_goteo(tmp_path):
    out = tmp_path / "respaldo_goteo.mp4"
    r = subprocess.run([sys.executable, str(ROOT / "demo" / "record.py"), "--demo", "goteo", "--every", "20",
                        "--out", str(out)], capture_output=True, text=True, encoding="utf-8", timeout=600)
    assert r.returncode == 0, r.stderr
    assert out.is_file() and out.stat().st_size > 10 * 1024
