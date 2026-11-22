"""Los datos del tablero «Cómo lo probamos» (`pruebas.html`).

    python demo/alternativas/03-enjambre-juanpedro/hacer_pruebas.py            # reescribe pruebas.json
    python demo/alternativas/03-enjambre-juanpedro/hacer_pruebas.py --suite    # corre la suite y anota el resultado

No mide nada: junta en `pruebas.json` cifras que ya están versionadas, para que la página (que en la
web es un sitio estático) las pueda leer de un solo archivo.

- `docs/informe/datos/cifras.json`: lo que `docs/informe/hacer_datos.py` saca de `results/`,
  `models/` y `redteam/`, más el detalle por familia de la corrida con las marcas del proxy. Ese
  script comprueba que sus totales sean los publicados.
- `results/short_fragments/summary.json` y `results/adaptive/summary.json`: las dos mediciones
  posteriores, fila por fila.
- `suite.json`: cuántos tests tiene la suite y cuándo se corrió por última vez (`--suite`).

El test `test_terminales.py` regenera `pruebas.json` y lo compara con el guardado.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "pruebas.json"
SUITE = HERE / "suite.json"
CIFRAS = ROOT / "docs" / "informe" / "datos" / "cifras.json"
LATENCIA = ROOT / "docs" / "informe" / "datos" / "latencia.json"

SISTEMAS = ("ours", "per_session", "taint_rule", "budget", "allowlist", "combined", "no_evidence",
            "no_rotation", "detect_secrets", "reassembly")
ATAQUES = ("A5", "A7", "A10", "A12", "A9", "A13")
NORMALES = ("B3", "B4", "B5", "común")
SANTIAGO = datetime.timezone(datetime.timedelta(hours=-3))   # hora de verano de Chile, la del 21 de noviembre
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre")


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def hora(iso: str) -> str:
    """Una fecha ISO en UTC, como hora de Santiago."""
    return datetime.datetime.fromisoformat(iso).astimezone(SANTIAGO).strftime("%H:%M")


def dia_y_hora(iso: str) -> str:
    """Una fecha ISO, como «22 de noviembre a las 00:45», hora de Santiago."""
    d = datetime.datetime.fromisoformat(iso).astimezone(SANTIAGO)
    return f"{d.day} de {MESES[d.month - 1]} a las {d:%H:%M}"


def _suite() -> dict | None:
    if not SUITE.is_file():
        return None
    s = _json(SUITE)
    return {**s, "cuando": dia_y_hora(s["fecha"])}


def _fragmentos() -> dict:
    sf = _json(ROOT / "results" / "short_fragments" / "summary.json")
    filas = [r for r in sf["rows"] if r["dest"] == "web.test"]
    otras = {(r["system"], r["piece_chars"], r["gap"]): r for r in sf["rows"] if r["dest"] != "web.test"}
    for r in filas:      # la tabla muestra un destino: solo vale si el otro da lo mismo
        o = otras[(r["system"], r["piece_chars"], r["gap"])]
        if (o["max_bits_any_version"], o["success"]) != (r["max_bits_any_version"], r["success"]):
            raise ValueError("fragmentos cortos: el destino cambia el resultado")
    tam = sorted({r["piece_chars"] for r in filas})
    ritmos = sorted({r["gap"] for r in filas})
    por = {(r["system"], r["gap"], r["piece_chars"]): r for r in filas}
    return {
        "tamanos": tam, "ritmos": ritmos, "limite": sf["limit_bits"], "llamadas": sf["calls_per_session"],
        "sistemas": {s: [[{"bits": por[(s, g, n)]["max_bits_any_version"], "pasa": por[(s, g, n)]["success"]}
                          for n in tam] for g in ritmos] for s in ("ours", "no_evidence", "demo")},
    }


def _adaptativo(c: dict) -> dict:
    ad = _json(ROOT / "results" / "adaptive" / "summary.json")
    campos = ("rewritten", "not_rewritable", "prevented", "median_max_bits", "max_max_bits", "median_rotations",
              "escalated_fraction", "blocked_after_escalation")
    out = {conj: {s: {k: ad[conj][s]["overall"][k] for k in campos} for s in ("ours", "no_evidence", "no_rotation")}
           for conj in ("test", "val")}
    out["familias"] = {f: {s: {"frenados": ad["test"][s]["by_family"][f]["prevented"],
                               "max_bits": ad["test"][s]["by_family"][f]["max_max_bits"]}
                           for s in ("ours", "no_evidence", "no_rotation")} for f in ATAQUES}
    return out


def leer() -> dict:
    c = _json(CIFRAS)
    ev, sis, mec, corr = c["evaluacion"], c["sistemas"], c["mecanismo"], c["corridas"]
    sistemas = [{"id": s, "grabadas": sis[s]["grabadas"], "proxy": sis[s]["proxy"], "ic": sis[s]["prevenidos_ic"],
                 "bloqueadas_pct": round(sis[s]["falsas_alarmas"] * 100, 1), "rot_1000": round(sis[s]["rot_1000"], 2),
                 "mediana_bits": sis[s]["mediana_bits"], "por_familia": sis[s]["por_familia"]} for s in SISTEMAS]
    ataques = {f: {k: mec[f][k] for k in ("n", "frenados", "reglas", "mediana_primera", "mediana_bits", "max_bits")}
               for f in ATAQUES}
    normales = {f: {k: mec[f][k] for k in ("n", "llamadas", "con_rotacion", "rotaciones", "reglas", "bloqueos")}
                for f in NORMALES}
    t = c["pruebas"]["tests"]
    tiempo = [
        {"hora": ev["sello"]["hora"], "quien": "rojo", "que": "sella el set de prueba",
         "huella": ev["sello"]["sha256"], "commit": ev["sello"]["commit"]},
        {"hora": hora(c["busqueda"]["fecha_congelado"]), "quien": "azul", "que": "congela el detector",
         "huella": ev["congelado"]["hash"], "commit": ev["sello"]["commit_congelado"]},
        {"hora": hora(corr["test"]["started"]), "quien": "morado", "que": "abre el set, comprueba el sello y corre la evaluación una sola vez",
         "huella": "", "commit": corr["test"]["commit"][:7]},
        {"hora": hora(corr["adaptive"]["date"]), "quien": "", "que": "atacante que se adapta, medido aparte",
         "huella": "", "commit": corr["adaptive"]["commit"][:7]},
        {"hora": hora(corr["proxy_flags"]["date"]), "quien": "", "que": "la misma evaluación con las marcas que calcula el proxy",
         "huella": "", "commit": corr["proxy_flags"]["commit"][:7]},
        {"hora": hora(corr["short_fragments"]["date"]), "quien": "", "que": "pedazos más cortos que el mínimo que cuenta el contador",
         "huella": "", "commit": corr["short_fragments"]["commit"][:7]},
    ]
    return {
        "nota": "Generado por hacer_pruebas.py. No se edita a mano: sale de docs/informe/datos/cifras.json y de results/.",
        "evaluacion": {k: ev[k] for k in ("sello", "congelado", "medicion", "ataques", "familias", "normales")},
        "sistemas": sistemas,
        "ataques": ataques,
        "normales": normales,
        "set": {**c["set_prueba"], "llamadas_normales": mec["llamadas_benignas"], "rotaciones_de_mas": mec["rotaciones_benignas"],
                "segundos": corr["test"]["seconds"], "cambios": c["cambios"]["by"]},
        "pruebas": {"T1": {k: t["T1"][k] for k in ("k", "n", "ci", "target", "pass")},
                    "T2": {k: t["T2"][k] for k in ("k", "n", "ci", "target", "pass")},
                    "T3": {k: t["T3"][k] for k in ("b", "c", "n_pairs")},
                    "T4": {k: t["T4"][k] for k in ("attack_success_with", "attack_success_without", "n_with",
                                                   "median_bits_with", "median_bits_without")}},
        "tiempo": tiempo,
        "adaptativo": _adaptativo(c),
        "fragmentos": _fragmentos(),
        "busqueda": {k: c["busqueda"][k] for k in ("combinaciones", "cumplen_metas", "pareto", "empatadas_con_la_elegida",
                                                   "empatadas_sin_rotaciones", "elegida_en_pareto")},
        "latencia": _json(LATENCIA) if LATENCIA.is_file() else None,
        "suite": _suite(),
    }


def texto(datos: dict) -> str:
    return json.dumps(datos, ensure_ascii=False, indent=1) + "\n"


def correr_suite() -> dict:
    """Corre la suite completa del repositorio y anota cuántos tests pasaron."""
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rfE", "--tb=short"], cwd=ROOT,
                       capture_output=True, text=True)
    lineas = r.stdout.strip().splitlines() or [""]
    cola = lineas[-1]
    m = re.search(r"(\d+) passed", cola)
    if not m or r.returncode != 0 or "failed" in cola or "error" in cola:
        (HERE / "suite_fallida.txt").write_text(r.stdout + r.stderr, encoding="utf-8")     # no se versiona
        cuales = [l for l in lineas if l.startswith(("FAILED", "ERROR"))]
        raise SystemExit("La suite no pasó entera: " + (cola or r.stderr[-300:]) + "\n" + "\n".join(cuales)
                         + f"\nSalida completa en {HERE / 'suite_fallida.txt'}")
    seg = re.search(r"in ([\d.]+)s", cola)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    out = {"tests": int(m.group(1)), "segundos": float(seg.group(1)) if seg else None,
           "saltados": int(s.group(1)) if (s := re.search(r"(\d+) skipped", cola)) else 0,
           "commit": commit, "fecha": datetime.datetime.now().astimezone().isoformat(timespec="minutes"),
           "comando": "python -m pytest -q"}
    SUITE.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--suite", action="store_true", help="corre la suite completa y anota el resultado en suite.json")
    args = ap.parse_args()
    if args.suite:
        s = correr_suite()
        print(f"suite: {s['tests']} tests pasan ({s['segundos']} s, commit {s['commit']})")
    datos = leer()
    OUT.write_text(texto(datos), encoding="utf-8", newline="\n")
    a = datos["evaluacion"]["ataques"]
    print(f"{OUT.relative_to(ROOT)}: {a['frenados']} de {a['n']} ataques frenados; {len(datos['sistemas'])} sistemas; "
          f"{sum(len(f) for f in datos['fragmentos']['sistemas'].values()) * len(datos['fragmentos']['tamanos'])} celdas de fragmentos")


if __name__ == "__main__":
    main()
