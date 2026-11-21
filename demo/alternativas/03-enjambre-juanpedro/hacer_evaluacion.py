"""Las cifras de la evaluación que muestra la escena «Cómo lo probamos».

    python demo/alternativas/03-enjambre-juanpedro/hacer_evaluacion.py            # reescribe evaluacion.json
    python demo/alternativas/03-enjambre-juanpedro/hacer_evaluacion.py --sello    # recalcula el sello del set

No mide nada: copia a `evaluacion.json` los números que ya están en el repositorio, para que la
página los pueda leer (el servidor de la demo solo sirve la carpeta `demo/`).

- `redteam/SELLO.md`: el sello del set de prueba, cuándo se selló y cuándo se abrió.
- `results/proxy_flags/`: la medición con las marcas que calcula el proxy en vivo (120 de 180).
- `results/test/`: la corrida única sobre el set sellado (llamadas normales, rotaciones de más).

`sello_actual()` sí calcula algo: vuelve a sacar el sha256 del set de prueba tal como está hoy en
el repositorio, con la receta de `redteam/SELLO.md`. Si coincide con el publicado, el set no
cambió desde que se selló. La página lo pide en vivo a `servidor.py`.

El test `test_enjambre.py` regenera este archivo y lo compara con el que está guardado: si alguien
cambia `results/`, el test avisa que la escena quedó vieja.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "evaluacion.json"
COMANDO = "python -m eval.final.proxy_flags --out results/proxy_flags"

# Las columnas de systems.json que se muestran. El texto de cada una está en escenario.json.
SISTEMAS = ("ours", "taint_rule", "budget", "allowlist", "combined", "no_evidence",
            "no_rotation", "detect_secrets", "reassembly", "per_session")


def _json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _busca(patron: str, texto: str, que: str) -> str:
    m = re.search(patron, texto, flags=re.S)
    if not m:
        raise ValueError(f"redteam/SELLO.md ya no trae {que}")
    return m.group(1)


def sello_publicado() -> dict:
    """Lo que dice `redteam/SELLO.md`: el sello, cuándo se selló y cuándo se abrió."""
    t = (ROOT / "redteam" / "SELLO.md").read_text(encoding="utf-8")
    return {
        "sha256": _busca(r"\*\*Sello \(sha256\):\*\*\s*`([0-9a-f]{64})`", t, "el sello"),
        "commit": _busca(r"\*\*Commit sellado:\*\*\s*`([0-9a-f]{7,40})`", t, "el commit sellado")[:7],
        "hora": _busca(r"\*\*Fecha y hora:\*\*\s*\d{4}-\d{2}-\d{2} (\d{2}:\d{2})", t, "la hora del sello"),
        "abierto": _busca(r"## Apertura\s+Abierto[^.]*? a las (\d{2}:\d{2})", t, "la hora de apertura"),
        "commit_congelado": _busca(r"congelada antes \(commit `([0-9a-f]{7,40})`", t, "el commit del congelamiento")[:7],
        "commit_corrida": _busca(r"una sola vez, en el commit `([0-9a-f]{7,40})`", t, "el commit de la corrida")[:7],
    }


def sello_actual() -> dict:
    """Recalcula el sello con la receta de `redteam/SELLO.md`, sobre los archivos de ahora.

    El sello es el sha256 de las líneas `<sha256>  <ruta relativa>` de todos los archivos bajo
    `redteam/test/` más `redteam/sealed.py`, en orden de ruta (orden de bytes, como `LC_ALL=C sort`).
    """
    t0 = time.perf_counter()
    rutas = [p.relative_to(ROOT).as_posix() for p in (ROOT / "redteam" / "test").rglob("*") if p.is_file()]
    rutas.append("redteam/sealed.py")
    rutas.sort(key=lambda r: r.encode("utf-8"))
    lineas = "".join(f"{hashlib.sha256((ROOT / r).read_bytes()).hexdigest()}  {r}\n" for r in rutas)
    sha = hashlib.sha256(lineas.encode("utf-8")).hexdigest()
    publicado = sello_publicado()["sha256"]
    return {"sha256": sha, "publicado": publicado, "coincide": sha == publicado,
            "archivos": len(rutas), "ms": round((time.perf_counter() - t0) * 1000, 1)}


def leer() -> dict:
    """Junta las cifras. Cada una lleva al lado de dónde sale."""
    sello = sello_publicado()
    manifest = _json("redteam/test/manifest.json")
    run = _json("results/proxy_flags/RUN.json")
    run_test = _json("results/test/RUN.json")
    systems = _json("results/proxy_flags/systems.json")
    cambios = _json("results/proxy_flags/changes.json")
    ours = _json("results/test/summary_ours.json")
    report = _json("results/test/report.json")
    if run["frozen_hash"] != run_test["frozen_hash"]:
        raise ValueError("las dos mediciones no usan la misma configuración congelada")

    por = {modo: {s["system"]: s for s in systems[modo]} for modo in ("grabadas", "proxy")}
    fam_n = {f: n for f, n in manifest["families"].items() if f.startswith("A")}
    num = lambda f: int(f[1:])
    cuenta = lambda modo, sistema, f: round(por[modo][sistema]["by_family"][f] * fam_n[f])

    familias = [{"id": f, "n": fam_n[f], "frenados": cuenta("proxy", "ours", f),
                 "frenados_grabadas": cuenta("grabadas", "ours", f)} for f in fam_n]
    # Primero las que frena, después las que se escapan; dentro de cada grupo, por número.
    familias.sort(key=lambda x: (-x["frenados"], num(x["id"])))

    n_ataques = por["proxy"]["ours"]["n_attack_units"]
    total = lambda modo, sistema: sum(cuenta(modo, sistema, f) for f in fam_n)
    sistemas = [{
        "id": s,
        "frenados": total("proxy", s),
        "frenados_grabadas": total("grabadas", s),
        "normales_bloqueadas_pct": round(por["proxy"][s]["false_alarm_rate"] * 100, 1),
        "rotaciones_por_mil": round(por["proxy"][s]["benign_rotations_per_1000"], 2),
    } for s in SISTEMAS]
    orden = {s: i for i, s in enumerate(SISTEMAS)}
    sistemas.sort(key=lambda s: (s["id"] == "per_session", s["id"] != "ours", -s["frenados"], orden[s["id"]]))
    for s in sistemas:  # la suma por familia tiene que dar la tasa publicada
        for modo, clave in (("proxy", "frenados"), ("grabadas", "frenados_grabadas")):
            if abs(s[clave] / n_ataques - por[modo][s["id"]]["prevented_rate"]) > 1e-9:
                raise ValueError(f"{s['id']}: la suma por familia no da la tasa de systems.json ({modo})")

    normales = sorted((s for s in ours["sessions"] if not s["is_attack"]), key=lambda s: s["session_id"])
    dificiles = [s for s in normales if s["session_id"].startswith("test-")]
    comunes = [s for s in normales if not s["session_id"].startswith("test-")]
    # redteam/sealed.py genera las familias normales difíciles en el orden del manifiesto, una
    # detrás de otra: con los identificadores en orden, cada tramo es una familia.
    fam_b = {f: n for f, n in manifest["families"].items() if f.startswith("B")}
    if sum(fam_b.values()) != len(dificiles):
        raise ValueError("las sesiones normales difíciles no calzan con el manifiesto del set")
    normales_familias, desde = [], 0
    for f in sorted(fam_b, key=num):
        tramo = dificiles[desde:desde + fam_b[f]]
        desde += fam_b[f]
        normales_familias.append({"id": f, "n": len(tramo),
                                  "con_rotacion_de_mas": sum(1 for s in tramo if s["n_rotations"]),
                                  "bloqueadas": sum(s["n_blocks"] for s in tramo),
                                  "tira": "".join("1" if s["n_rotations"] else "0" for s in tramo)})
    ataques = [s for s in ours["sessions"] if s["is_attack"]]
    t1 = report["tests"]["T1"]

    return {
        "nota": "Generado por hacer_evaluacion.py. No se edita a mano: sale de results/ y de redteam/SELLO.md.",
        "sello": {**sello, "archivos": sello_actual()["archivos"], "fuente": "redteam/SELLO.md"},
        "congelado": {"hash": run["frozen_hash"], "params": run["params"],
                      "fuente": "results/proxy_flags/RUN.json"},
        "medicion": {"comando": COMANDO, "commit": run["commit"][:7], "fecha": run["date"],
                     "llamadas": cambios["calls"], "llamadas_que_cambian": cambios["changed"],
                     "fuente": "results/proxy_flags/systems.json"},
        "ataques": {
            "n": n_ataques,
            "frenados": total("proxy", "ours"),
            "frenados_grabadas": total("grabadas", "ours"),
            "familias": len(familias),
            "familias_frenadas": sum(1 for f in familias if f["frenados"] == f["n"]),
            "max_bits_grabadas": max(s["max_bits_true"] for s in ataques),
            "mediana_bits_grabadas": report["tests"]["T4"]["median_bits_with"],
            "bits_clave": 160,
        },
        "familias": familias,
        "normales": {
            "llamadas": t1["n"],
            "bloqueadas": t1["k"],
            "bloqueadas_proxy_pct": por["proxy"]["ours"]["false_alarm_rate"] * 100,
            "sesiones_dificiles": len(dificiles),
            "con_rotacion_de_mas": sum(1 for s in dificiles if s["n_rotations"]),
            "rotaciones_de_mas": sum(s["n_rotations"] for s in dificiles),
            "familias": normales_familias,
            "sesiones_comunes": len(comunes),
            "comunes_con_rotacion": sum(1 for s in comunes if s["n_rotations"]),
            "rotaciones_por_mil": round(por["proxy"]["ours"]["benign_rotations_per_1000"], 2),
            "fuente": "results/test/summary_ours.json y results/test/report.json (T1)",
        },
        "sistemas": sistemas,
    }


def texto(datos: dict) -> str:
    return json.dumps(datos, ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sello", action="store_true", help="solo recalcula el sello del set de prueba y lo compara")
    args = ap.parse_args()
    if args.sello:
        s = sello_actual()
        print(f"sello publicado   {s['publicado']}")
        print(f"sello recalculado {s['sha256']}  ({s['archivos']} archivos, {s['ms']} ms)")
        print("coincide: el set de prueba no cambió desde que se selló" if s["coincide"] else "NO coincide")
        raise SystemExit(0 if s["coincide"] else 1)
    datos = leer()
    OUT.write_text(texto(datos), encoding="utf-8")
    a, n = datos["ataques"], datos["normales"]
    print(f"{OUT.relative_to(ROOT)}: {a['frenados']} de {a['n']} ataques frenados ({a['familias_frenadas']} de "
          f"{a['familias']} familias); {n['bloqueadas']} de {n['llamadas']} llamadas normales bloqueadas; "
          f"rotó de más en {n['con_rotacion_de_mas']} de {n['sesiones_dificiles']} sesiones difíciles")


if __name__ == "__main__":
    main()
