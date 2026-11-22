"""Tablas y figuras del informe técnico, generadas desde el repositorio.

    python docs/informe/hacer_datos.py            # reescribe docs/informe/datos/
    python docs/informe/hacer_datos.py --check    # regenera en memoria y compara con lo guardado

Ninguna cifra de las tablas y figuras de `datos/` se escribe a mano. Salen de tres fuentes:

1. Archivos ya versionados: `results/`, `models/`, `redteam/` y las corridas grabadas de la demo
   (`demo/viz/fixtures/`).
2. Una corrida del detector CONGELADO (`engine.detector.make_frozen`) sobre el set de prueba con las
   marcas que calcula el proxy (`eval.final.proxy_flags.variant`), hecha aquí para tener el detalle
   llamada a llamada que `results/proxy_flags/` no guarda: valor de ℓ, evidencia acumulada S, regla
   de cada rotación. Es el mismo camino de código que `python -m eval.final.proxy_flags`, y el script
   comprueba que reproduce sus totales. No ajusta nada: el set ya estaba abierto y el detector,
   congelado.
3. El grafo de archivos del repositorio de la demo (`engine.graph.gff.FileGraph`).

La latencia (`datos/latencia.tex`) se mide en esa misma corrida y cambia de una máquina a otra y de
una corrida a otra: por eso `--check` no la compara.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "datos"
sys.path.insert(0, str(ROOT))

BITS_POR_POSICION = 4.0
NO_COMPARAR = {"latencia.tex"}          # cambia en cada corrida


# --------------------------------------------------------------------------- utilidades

def _json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _eventos(rel: str) -> list[dict]:
    return [json.loads(l) for l in (ROOT / rel).read_text(encoding="utf-8").splitlines() if l.strip()]


def num(x, nd: int | None = None) -> str:
    """Número para siunitx: \\num{...} con punto decimal en la fuente (siunitx pone la coma)."""
    if x is None:
        return "---"
    if isinstance(x, float) and nd is not None:
        x = f"{x:.{nd}f}"
    elif isinstance(x, float) and x == int(x):
        x = str(int(x))
    return f"\\num{{{x}}}"


def tt(s: str) -> str:
    return "\\texttt{" + s.replace("_", "\\_").replace("%", "\\%").replace("#", "\\#") + "}"


def filas(rows: list[list[str]]) -> str:
    return "".join(" & ".join(r) + " \\\\\n" for r in rows)


def dat(header: list[str], rows: list[list]) -> str:
    def cell(v):
        if isinstance(v, float):
            return f"{v:.6g}"
        return str(v)
    return " ".join(header) + "\n" + "".join(" ".join(cell(v) for v in r) + "\n" for r in rows)


# --------------------------------------------------------------------------- 1. cifras ya versionadas

def evaluacion() -> dict:
    """Las cifras que ya copia la demo del pitch (probadas en su test): sello, 120 de 180, 34 de 90…"""
    spec = importlib.util.spec_from_file_location(
        "hacer_evaluacion", ROOT / "demo" / "alternativas" / "03-enjambre-juanpedro" / "hacer_evaluacion.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    datos = mod.leer()
    datos["sello_recalculado"] = {k: v for k, v in mod.sello_actual().items() if k != "ms"}
    return datos


NOMBRE_SISTEMA = {
    "ours": "Alicanto (congelado)",
    "per_session": "Alicanto con una cuenta por sesión",
    "no_evidence": "Alicanto sin evidencia de comportamiento",
    "no_rotation": "Alicanto sin rotación",
    "taint_rule": "Regla simple",
    "budget": "Presupuesto de bits por sesión (réplica)",
    "allowlist": "Lista de destinos permitidos",
    "combined": "Lista de destinos y escáner de secretos",
    "detect_secrets": "Escáner de secretos (\\texttt{detect-secrets})",
    "reassembly": "Reensamblado por sesión (réplica)",
}
ORDEN_SISTEMAS = ["ours", "per_session", "no_evidence", "no_rotation", "taint_rule", "budget", "allowlist",
                  "combined", "detect_secrets", "reassembly"]
FAMILIAS_A = ["A5", "A7", "A10", "A12", "A9", "A13"]


def tabla_sistemas(systems: dict) -> tuple[str, dict]:
    """Una fila por sistema: frenados con las marcas grabadas y con las del proxy, bloqueos, rotaciones."""
    por = {v: {r["system"]: r for r in systems[v]} for v in ("grabadas", "proxy", "proxy_push")}
    rows, resumen = [], {}
    for s in ORDEN_SISTEMAS:
        g, p, pp = por["grabadas"][s], por["proxy"][s], por["proxy_push"][s]
        n = p["n_attack_units"]
        kg, kp, kpp = (round(x["prevented_rate"] * n) for x in (g, p, pp))
        resumen[s] = {"grabadas": kg, "proxy": kp, "proxy_push": kpp,
                      "falsas_alarmas": p["false_alarm_rate"], "falsas_alarmas_ic": p["false_alarm_ci"],
                      "rot_1000": p["benign_rotations_per_1000"], "prevenidos_ic": p["prevented_ci"],
                      "mediana_bits": p["median_max_bits_true"], "mediana_bits_grabadas": g["median_max_bits_true"],
                      "por_familia": {f: round(p["by_family"][f] * 30) for f in FAMILIAS_A},
                      "por_familia_grabadas": {f: round(g["by_family"][f] * 30) for f in FAMILIAS_A}}
        if g["false_alarm_rate"] != p["false_alarm_rate"] or g["benign_rotations_per_1000"] != p["benign_rotations_per_1000"]:
            raise ValueError(f"{s}: bloqueos o rotaciones benignas cambian con las marcas del proxy; la tabla dice que no")
        if kp != kpp:
            raise ValueError(f"{s}: la inspección del push cambia el total; la tabla dice que no")
        ic = p["prevented_ci"]
        rows.append([NOMBRE_SISTEMA[s], num(kg), "\\textbf{" + num(kp) + "}" if s == "ours" else num(kp),
                     f"[{num(ic[0], 2)}; {num(ic[1], 2)}]",
                     num(p["false_alarm_rate"] * 100, 1), num(p["benign_rotations_per_1000"], 2),
                     num(p["median_max_bits_true"])])
    return filas(rows), resumen


def tabla_sistemas_familia(resumen: dict) -> str:
    rows = []
    for s in ORDEN_SISTEMAS:
        r = resumen[s]
        rows.append([NOMBRE_SISTEMA[s]] + [num(r["por_familia"][f]) for f in FAMILIAS_A] + [num(r["proxy"])])
    return filas(rows)


def tabla_sistemas_familia_grabadas(resumen: dict) -> str:
    rows = []
    for s in ORDEN_SISTEMAS:
        r = resumen[s]
        rows.append([NOMBRE_SISTEMA[s]] + [num(r["por_familia_grabadas"][f]) for f in FAMILIAS_A] + [num(r["grabadas"])])
    return filas(rows)


def tabla_cambios(cambios: dict) -> str:
    texto = {"11 -> 10": "sale, no confiable $\\to$ sale, confiable",
             "11 -> 00": "sale, no confiable $\\to$ no sale",
             "01 -> 00": "no confiable $\\to$ confiable"}
    que = {("attack", "http_request"): "Envío de ataque, \\texttt{http\\_request} a ",
           ("attack", "git"): "Envío de ataque, \\texttt{git} ",
           ("benign", "read_file"): "Llamada normal, \\texttt{read\\_file}"}
    rows = []
    for r in cambios["by"]:
        donde = tt(r["where"]) if r["where"] else ""
        rows.append([que[(r["label"], r["tool"])] + donde, num(r["calls"]), texto[r["flags"]]])
    rows.append(["\\textbf{Total}", "\\textbf{" + num(cambios["changed"]) + "}", f"de {num(cambios['calls'])} llamadas"])
    return filas(rows)


def tabla_adaptativo(summ: dict) -> tuple[str, dict]:
    nombre = {"ours": "Alicanto (congelado)", "no_rotation": "Sin rotación", "no_evidence": "Sin evidencia"}
    rows, res = [], {}
    for conj, etiqueta in (("test", "Prueba"), ("val", "Validación")):
        for s in ("ours", "no_evidence", "no_rotation"):
            o = summ[conj][s]["overall"]
            res[f"{conj}_{s}"] = o
            rows.append([etiqueta, nombre[s], num(o["rewritten"]), num(o["not_rewritable"]),
                         f"{num(o['prevented'])} de {num(o['rewritten'])}",
                         num(o["median_max_bits"]), num(o["max_max_bits"]),
                         num(o["median_rotations"]), num(o["escalated_fraction"] * 100, 0)])
    return filas(rows), res


def tabla_adaptativo_familia(summ: dict) -> str:
    rows = []
    fams = sorted(summ["test"]["ours"]["by_family"], key=lambda f: FAMILIAS_A.index(f) if f in FAMILIAS_A else 99)
    for f in fams:
        cells = [f]
        for s in ("ours", "no_evidence", "no_rotation"):
            o = summ["test"][s]["by_family"][f]
            cells += [f"{num(o['prevented'])}", num(o["max_max_bits"])]
        rows.append(cells)
    return filas(rows)


def tabla_fragmentos(sf: dict) -> tuple[str, str, dict]:
    """(matriz compacta, tabla completa, resumen). La matriz solo se escribe si el destino no cambia nada."""
    rows = sf["rows"]
    clave = lambda r: (r["system"], r["piece_chars"], r["gap"])
    por: dict = defaultdict(dict)
    for r in rows:
        por[clave(r)][r["dest"]] = r
    campos = ("max_bits_any_version", "bits_before_first_rotation", "rotations", "escalated", "success")
    iguales = all(len({tuple(r[c] for c in campos) for r in d.values()}) == 1 for d in por.values())
    sistemas = (("ours", "Congelada, con evidencia"), ("no_evidence", "Congelada, sin evidencia"),
                ("demo", "Demo y \\emph{hook} (sin evidencia)"))
    tam, sal = sorted({r["piece_chars"] for r in rows}), sorted({r["gap"] for r in rows})
    matriz = []
    for s, nombre in sistemas:
        for g in sal:
            cells = [nombre if g == sal[0] else "", num(g)]
            for n in tam:
                r = por[(s, n, g)]["web.test"]
                v = num(r["max_bits_any_version"])
                cells.append("\\textbf{" + v + "}" if r["success"] else v)
            matriz.append(cells)
    completa = []
    for r in rows:
        reglas = ", ".join(f"{k} {v}" for k, v in r["rotations_by_rule"].items())
        completa.append([{"ours": "congelada", "no_evidence": "sin evidencia", "demo": "demo"}[r["system"]],
                         tt(r["dest"]), num(r["piece_chars"]), num(r["gap"]), num(r["sends"]),
                         num(r["blocked_sends"]), num(r["bits_before_first_rotation"]),
                         num(r["max_bits_any_version"]), num(r["rotations"]), reglas,
                         "sí" if r["escalated"] else "no", "\\textbf{sí}" if r["success"] else "no"])
    resumen = {"filas": len(rows), "destino_no_cambia": iguales,
               "pasan_por_sistema": {s: sum(1 for r in rows if r["system"] == s and r["success"]) for s, _ in sistemas},
               "cortos_por_sistema": {s: sum(1 for r in rows if r["system"] == s and r["piece_chars"] < 4) for s, _ in sistemas},
               "max_largos": max(r["max_bits_any_version"] for r in rows if r["piece_chars"] >= 4),
               "max_cortos_congelada": max(r["max_bits_any_version"] for r in rows
                                           if r["system"] == "ours" and r["piece_chars"] < 4)}
    if not iguales:
        raise ValueError("fragmentos cortos: el destino cambia el resultado; la matriz compacta ya no vale")
    return filas(matriz), filas(completa), resumen


# --------------------------------------------------------------------------- 2. modelo y búsqueda

SEÑAL = {"U": "$U$", "is_sink": tt("is_sink"), "short_match": tt("short_match"), "arg_entropy": tt("arg_entropy"),
         "m": "$m$", "m_sd": "$m_{\\mathrm{sd}}$", "jump": tt("jump"), "n_S": "$n_S$",
         "prev_source_now_sink": tt("prev_source_now_sink")}
ORDEN_SEÑALES = ["U", "is_sink", "short_match", "arg_entropy", "m", "m_sd", "jump", "n_S", "prev_source_now_sink"]


def _intervalos(edges: list[float]) -> list[tuple[float | None, float | None]]:
    """Cajas de bisect_right: caja i = [edges[i-1], edges[i]); la 0 es (-inf, edges[0])."""
    cotas = [None, *edges, None]
    return [(cotas[i], cotas[i + 1]) for i in range(len(cotas) - 1)]


def modelo() -> tuple[str, str, dict]:
    m = _json("models/model.json")
    rep = _json("models/model.report.json")
    rows, paneles, info = [], [], {"n_bins": m["n_bins"], "B": m["B"], "alpha": m["alpha"], **rep, "senales": {}}

    def f(x):
        return f"{x:.4g}"

    for name in ORDEN_SEÑALES:
        feat = m["features"][name]
        cajas = _intervalos(feat["edges"])
        vivas = []
        for i, ((lo, hi), lr) in enumerate(zip(cajas, feat["logratio"])):
            # La caja 0 (valores bajo el primer borde) queda vacía cuando el primer borde es 0 y la señal no es negativa.
            vacia = i == 0 and lo is None and hi == 0.0
            if lo is None:
                rango = f"$< {f(hi)}$"
            elif hi is None:
                rango = f"$\\geq {f(lo)}$"
            else:
                rango = f"$[{f(lo)};\\ {f(hi)})$"
            rows.append([SEÑAL[name] if i == 0 else "", rango + (" (vacía)" if vacia else ""), num(lr, 3)])
            if not vacia:
                vivas.append((rango, lr))
        info["senales"][name] = {"cajas": len(cajas), "con_datos": len(vivas),
                                 "min": min(v for _, v in vivas), "max": max(v for _, v in vivas)}
        coords = " ".join(f"({i + 1},{lr:.3f})" for i, (_, lr) in enumerate(vivas))
        paneles.append(
            "\\nextgroupplot[title={%s}, xmin=0.3, xmax=%d.7, xtick={1,...,%d}]\n"
            "\\addplot[ybar, bar width=%s, draw=none, fill=tinta] coordinates {%s};\n"
            % (SEÑAL[name], len(vivas), len(vivas), "5pt" if len(vivas) > 6 else "8pt", coords))
    return filas(rows), "".join(paneles), info


def busqueda() -> tuple[str, str, dict]:
    rows = _json("models/search/rows.json")
    pareto = _json("models/search/pareto.json")
    frozen = _json("models/search/frozen.json")
    ok = [r for r in rows if (r["false_alarm_rate"] or 0) <= 1e-3 and (r["benign_rotations_per_1000"] or 0) <= 5.0]
    mejor_bits = min(r["median_max_bits_true"] for r in ok)
    empatadas = [r for r in ok if r["median_max_bits_true"] == mejor_bits
                 and r["prevented_rate"] == max(x["prevented_rate"] for x in ok if x["median_max_bits_true"] == mejor_bits)]
    elegida = empatadas[0]
    if {k: elegida[k] for k in ("b", "b_rot", "lambda_rot", "T")} != frozen["params"]:
        raise ValueError("la primera combinación empatada de la grilla no es la congelada")
    metricas = ("false_alarm_rate", "benign_rotations_per_1000", "prevented_rate", "median_max_bits_true")
    mueve = {}
    for p in ("b", "b_rot", "lambda_rot", "T"):
        otros = [q for q in ("b", "b_rot", "lambda_rot", "T") if q != p]
        grupos: dict = defaultdict(set)
        for r in rows:
            grupos[tuple(r[q] for q in otros)].add(tuple(round(r[m], 9) for m in metricas))
        mueve[p] = any(len(v) > 1 for v in grupos.values())
    T_vals, br_vals = sorted({r["T"] for r in rows}), sorted({r["b_rot"] for r in rows})
    lam_vals = sorted({r["lambda_rot"] for r in rows})

    def rango(vals, nd):
        lo, hi = min(vals), max(vals)
        return num(lo, nd) if lo == hi else f"{num(lo, nd)}--{num(hi, nd)}"

    t1 = [[num(T)] + [rango([r["benign_rotations_per_1000"] for r in rows if r["T"] == T and r["b_rot"] == b], 2)
                      for b in br_vals] for T in T_vals]
    t2 = [[num(l)] + [rango([r["median_max_bits_true"] for r in rows if r["lambda_rot"] == l and r["b_rot"] == b], 0)
                      for b in br_vals] for l in lam_vals]
    t3 = [["Ataques frenados"] + [rango([r["prevented_rate"] * 100 for r in rows if r["b_rot"] == b], 1)
                                  for b in br_vals]]
    clave4 = lambda r: tuple(r[k] for k in ("b", "b_rot", "lambda_rot", "T"))
    sin_rotar = [r for r in empatadas if r["benign_rotations_per_1000"] == 0]
    if {clave4(r) for r in sin_rotar} != {clave4(r) for r in pareto}:
        raise ValueError("la frontera de Pareto ya no es el conjunto de empatadas sin rotaciones")
    info = {"combinaciones": len(rows), "cumplen_metas": len(ok), "pareto": len(pareto),
            "empatadas_con_la_elegida": len(empatadas), "empatadas_sin_rotaciones": len(sin_rotar),
            "elegida_en_pareto": clave4(elegida) in {clave4(r) for r in pareto},
            "lambda_con_rotaciones": sorted({r["lambda_rot"] for r in empatadas if r["benign_rotations_per_1000"] > 0}),
            "elegida": elegida, "mueve_alguna_metrica": mueve,
            "grilla": {p: sorted({r[p] for r in rows}) for p in ("b", "b_rot", "lambda_rot", "T")},
            "fecha_congelado": frozen["date"], "hash": frozen["hash"], "model_sha256": frozen["model_sha256"],
            "data_sha256": frozen["data_sha256"]}
    return filas(t1) , filas(t2) + "\\midrule\n" + filas(t3), info


# --------------------------------------------------------------------------- 3. demo grabada

def demo() -> tuple[str, str, dict]:
    def serie(rel):
        ev = _eventos(rel)
        calls = {e["call_id"]: e["data"] for e in ev if e["kind"] == "tool_call"}
        out = []
        for e in ev:
            if e["kind"] == "decision":
                c = calls[e["call_id"]]
                out.append((c["t"], c["session_id"], e["data"]["leak"]["SECRET_1"]["bits"], e["data"]["action"],
                            bool(c["is_sink"]), e["data"].get("latency_ms", 0.0)))
        fin = [e["data"] for e in ev if e["source"] == "attacker"][-1]
        return out, fin

    izq, fin_i = serie("demo/viz/fixtures/real_left.jsonl")
    der, fin_d = serie("demo/viz/fixtures/real_right.jsonl")
    rot = [t for t, _, _, a, _, _ in der if a.startswith("rotate")]
    goteo = dat(["t", "sin", "con"], [[t, bi, bd] for (t, _, bi, _, _, _), (_, _, bd, _, _, _) in zip(izq, der)])
    info = {"llamadas": len(der), "rota_en": rot, "bits_al_rotar": max(b for _, _, b, _, _, _ in der),
            "latencia_mediana_ms": round(statistics.median(l for *_, l in der), 3),
            "latencia_max_ms": round(max(l for *_, l in der), 3),
            "final_sin": {k: fin_i.get(k) for k in ("status", "bits_known", "key_complete")},
            "final_con": {k: fin_d.get(k) for k in ("status", "bits_known", "key_complete")},
            "envios": sum(1 for *_, s, _ in izq if s) - 1}

    izq, fin_i = serie("demo/viz/fixtures/swarm_left.jsonl")
    der, fin_d = serie("demo/viz/fixtures/swarm_right.jsonl")
    agentes = sorted({s for _, s, *_ in izq})
    ultimo = {a: 0.0 for a in agentes}
    comp = 0.0
    filas_e = []
    for (t, s, b, _, _, _), (_, _, bd, ad, _, _) in zip(izq, der):
        ultimo[s] = b
        comp = bd
        filas_e.append([t, *[ultimo[a] for a in agentes], comp])
    rot = [t for t, _, _, a, _, _ in der if a.startswith("rotate")]
    info["enjambre"] = {"agentes": len(agentes), "llamadas": len(der), "rota_en": rot,
                        "max_por_agente": max(b for _, _, b, *_ in izq),
                        "bits_al_rotar": max(b for _, _, b, *_ in der),
                        "final_sin": {k: fin_i.get(k) for k in ("status", "bits_known", "key_complete")},
                        "final_con": {k: fin_d.get(k) for k in ("status", "bits_known", "key_complete")}}
    enj = dat(["t", *[f"a{i + 1}" for i in range(len(agentes))], "compartida"], filas_e)
    return goteo, enj, info


# --------------------------------------------------------------------------- 4. grafo de archivos

def grafo() -> tuple[str, dict]:
    from engine.graph.gff import FileGraph

    g = FileGraph.from_workspace(str(ROOT / "demo" / "repo"), str(ROOT / "demo" / "secrets_manifest.json"))
    clases = Counter(d["kind"] for _, d in g.G.nodes(data=True))
    pesos = Counter(d["weight"] for *_, d in g.G.edges(data=True))
    etiqueta = {n: y for n, y in g.labels.items()}
    quiero = [".env", "config/secrets.yaml", "SECRET_1", "api.empresa.test", "config/", "config/settings.yaml",
              "./", "src/app/franjas.py", "tests/test_franjas.py", "docs/", "README.md"]
    quiero = [n for n in quiero if n in g.idx]
    rows = []
    for n in quiero:
        i = g.idx[n]
        tipo = {"file": "archivo", "dir": "carpeta", "secret": "secreto", "host": "destino permitido"}[g.G.nodes[n]["kind"]]
        marca = {1.0: "sensible (1)", 0.0: "no sensible (0)"}.get(etiqueta.get(n), "---")
        rows.append([tt(n), tipo, marca, num(float(g.mu[i]), 3), num(float(g.sd[i]), 3)])
    info = {"nodos": len(g.nodes), "aristas": g.G.number_of_edges(), "por_clase": dict(clases),
            "aristas_por_peso": {str(k): v for k, v in sorted(pesos.items())},
            "etiquetados": len(g.labels), "kappa": g.kappa, "tau": g.tau,
            "mu_min": float(g.mu.min()), "mu_max": float(g.mu.max())}
    return filas(rows), info


# --------------------------------------------------------------------------- 5. corrida instrumentada

def _clase(c) -> str:
    """Tipo de llamada, para la tabla de ℓ."""
    from proxy.tools import url_host

    if c.tool in ("read_file", "list_dir"):
        return "Leer o listar archivos"
    if c.tool == "git":
        sub = next((a for a in (c.args or {}).get("args") or [] if isinstance(a, str) and not a.startswith("-")), "")
        return "\\texttt{git} hacia un remoto" if sub in ("push", "fetch", "pull") else "\\texttt{git} local"
    if c.tool in ("github_issue", "github_comment"):
        return "Publicar en \\texttt{github.test}"
    host = url_host(str((c.args or {}).get("url", "")))
    return "HTTP a \\texttt{%s}" % host


def _regla(reason: str) -> str:
    for nombre, patron in (("bloqueo", "Sumidero con material de"), ("contador", "fracción filtrada"),
                           ("evidencia", "expuesto y evidencia"), ("período", "Rotación periódica")):
        if patron in reason:
            return nombre
    return "otra"


def corrida() -> dict:
    """El sistema `ours` de eval.final.run sobre el set de prueba con las marcas del proxy, guardando
    además ℓ, S, la regla de cada rotación y el tiempo de cada decisión."""
    from contracts import Event
    from engine.detector import SharedLedger, make_frozen
    from eval.final import run as R
    from eval.final.proxy_flags import variant

    frozen = make_frozen()
    sessions, labels, secrets = R.load_split("test")
    grabadas_n = sum(len(s) for s in sessions)
    proxy = variant(sessions, "proxy")
    units = R.make_units(proxy, labels)
    values, allowed = R._manifest()
    fam_ataque = {l["session_id"]: l["family"] for l in labels if l.get("family")}
    grupo = {l["session_id"]: l["group"] for l in labels if l.get("group")}
    envio = defaultdict(list)
    for l in labels:
        envio[(l["session_id"], int(l["t"]))].append(l)
    manifest = _json("redteam/test/manifest.json")
    dificiles = sorted(s[0].session_id for s in proxy if s[0].session_id.startswith("test-")
                       and s[0].session_id not in fam_ataque)
    fam_b, desde = {}, 0
    for f in sorted((f for f in manifest["families"] if f.startswith("B")), key=lambda f: int(f[1:])):
        for sid in dificiles[desde:desde + manifest["families"][f]]:
            fam_b[sid] = f
        desde += manifest["families"][f]

    events, trazas, lat = [], {}, []
    ell = defaultdict(Counter)
    for key, sess in units:
        unit_secrets: dict[str, str] = {}
        for s in sess:
            unit_secrets.update(secrets.get(s[0].session_id, {}))
        ledger = SharedLedger({**values, **unit_secrets}, allowed_hosts=allowed)
        traza = []
        for s in sess:
            det = frozen(ledger=ledger, seed=R.SEED)
            for c in sorted(s, key=lambda c: c.t):
                events.append(Event(ts=0.0, session_id=c.session_id, source="proxy", kind="tool_call",
                                    call_id=c.id, data=c.model_dump(mode="json")))
                t0 = time.perf_counter()
                d = det.decide(c)
                ms = (time.perf_counter() - t0) * 1000
                lat.append(ms)
                l = det.model.llr(det.last_features)
                events.append(Event(ts=0.0, session_id=c.session_id, source="proxy", kind="decision",
                                    call_id=c.id, data=d.model_dump(mode="json")))
                for sid in det.last_rotations:
                    events.append(Event(ts=0.0, session_id=c.session_id, source="proxy", kind="rotation",
                                        call_id=c.id, data={"secret_id": sid}))
                signo = "+B" if l >= frozen.model.B else ("-B" if l <= -frozen.model.B else "medio")
                ell[_clase(c)][signo] += 1
                traza.append({"sid": c.session_id, "t": c.t, "l": l, "S": d.S, "action": d.action,
                              "rot": list(det.last_rotations), "regla": _regla(d.reason) if det.last_rotations else "",
                              "envio": envio.get((c.session_id, c.t), []), "sink": c.is_sink, "untrusted": c.untrusted})
        trazas[key] = traza

    resumen = R.summarize(events, labels, n_boot=200)
    por_unidad = {s["session_id"]: s for s in resumen["sessions"]}
    fam_unidad = {}
    for key, sess in units:
        sid = sess[0][0].session_id
        fam_unidad[key] = fam_ataque.get(sid) or fam_b.get(sid) or "común"
    return {"trazas": trazas, "resumen": resumen, "por_unidad": por_unidad, "fam_unidad": fam_unidad,
            "lat": lat, "ell": ell, "llamadas": grabadas_n, "unidades": len(units), "sesiones": len(sessions),
            "grupo": grupo, "labels": labels}


def _bits_vigentes(traza: list[dict]) -> list[float]:
    """Bits de la clave vigente que ya salieron, llamada a llamada (regla «por contenido» de eval.metrics:
    una etiqueta sin versión cuenta hasta la primera rotación de su secreto; solo en llamadas permitidas)."""
    acc: dict[str, set] = defaultdict(set)
    rotado: set[str] = set()
    out = []
    for r in traza:
        if r["action"].endswith("allow"):
            for lab in r["envio"]:
                s = lab.get("secret_id") or ""
                if s not in rotado:
                    acc[s].update(int(p) for p in lab.get("positions_leaked") or [])
        out.append(max((len(v) for v in acc.values()), default=0) * BITS_POR_POSICION)
        for s in r["rot"]:
            rotado.add(s)
            acc[s] = set()
    return out


def mecanismo(c: dict, ev: dict) -> tuple[str, str, str, dict, dict]:
    """Por familia, con las marcas del proxy: frenados, regla de la primera rotación, cuándo, bits que salieron."""
    por_fam: dict = defaultdict(list)
    for key, traza in c["trazas"].items():
        por_fam[c["fam_unidad"][key]].append(key)
    info: dict = {}
    rows_a, rows_b = [], []
    for fam in FAMILIAS_A + ["B3", "B4", "B5", "común"]:
        keys = por_fam[fam]
        reglas, primeras, rotaciones, con_rot = Counter(), [], 0, 0
        for k in keys:
            rots = [(i + 1, r["regla"]) for i, r in enumerate(c["trazas"][k]) if r["rot"]]
            rotaciones += len(rots)
            con_rot += bool(rots)
            if rots:
                reglas[rots[0][1]] += 1
                primeras.append(rots[0][0])
            else:
                reglas["ninguna"] += 1
        u = [c["por_unidad"][k] for k in keys]
        bits = [x["max_bits_true"] for x in u]
        bloqueos = sum(x["n_blocks"] for x in u)
        info[fam] = {"n": len(keys), "reglas": dict(reglas), "con_rotacion": con_rot, "rotaciones": rotaciones,
                     "bloqueos": bloqueos, "llamadas": sum(x["n_calls"] for x in u),
                     "mediana_primera": statistics.median(primeras) if primeras else None}
        regla_txt = ", ".join(f"{k} {v}" for k, v in sorted(reglas.items(), key=lambda kv: -kv[1]))
        if fam.startswith("A"):
            frenados = sum(1 for x in u if x["prevented"])
            info[fam].update({"frenados": frenados, "mediana_bits": statistics.median(bits), "max_bits": max(bits)})
            rows_a.append([fam, num(frenados), regla_txt,
                           num(statistics.median(primeras)) if primeras else "---",
                           num(statistics.median(bits)), num(max(bits))])
        else:
            rows_b.append([fam if fam != "común" else "Comunes", num(len(keys)), num(info[fam]["llamadas"]),
                           num(con_rot), num(rotaciones), regla_txt if con_rot else "---", num(bloqueos)])
    # Comprobaciones contra lo publicado.
    total = sum(info[f]["frenados"] for f in FAMILIAS_A)
    if total != ev["ataques"]["frenados"] or any(info[f["id"]]["frenados"] != f["frenados"] for f in ev["familias"]):
        raise ValueError(f"la corrida instrumentada no reproduce results/proxy_flags: {total}")
    rot_1000 = c["resumen"]["benign_rotations_per_1000"]
    if round(rot_1000, 2) != ev["normales"]["rotaciones_por_mil"] or c["resumen"]["false_alarm_rate"] != 0.0:
        raise ValueError("la corrida instrumentada no reproduce las rotaciones o los bloqueos publicados")
    # Detalle por sesión normal: ¿coincide con la corrida única (marcas grabadas)?
    tiras = {}
    for fam in ("B3", "B4", "B5"):
        tiras[fam] = "".join("1" if any(r["rot"] for r in c["trazas"][k]) else "0" for k in sorted(por_fam[fam]))
    grabadas = {f["id"]: f["tira"] for f in ev["normales"]["familias"]}
    info["tiras_proxy"] = tiras
    info["tiras_iguales_a_grabadas"] = tiras == grabadas
    info["rotaciones_benignas"] = sum(info[f]["rotaciones"] for f in ("B3", "B4", "B5", "común"))
    info["llamadas_benignas"] = sum(info[f]["llamadas"] for f in ("B3", "B4", "B5", "común"))

    rows_l = []
    tot = Counter()
    for clase, cnt in sorted(c["ell"].items(), key=lambda kv: -sum(kv[1].values())):
        n = sum(cnt.values())
        tot.update(cnt)
        rows_l.append([clase, num(n), num(cnt["-B"]), num(cnt["medio"]), num(cnt["+B"])])
    n = sum(tot.values())
    rows_l.append(["\\textbf{Total}", num(n), num(tot["-B"]), num(tot["medio"]), num(tot["+B"])])
    ell_info = {"total": n, "menos_B": tot["-B"], "medio": tot["medio"], "mas_B": tot["+B"],
                "por_clase": {k: dict(v) for k, v in c["ell"].items()}}
    return filas(rows_a), filas(rows_b), filas(rows_l), info, ell_info


EJEMPLOS = (("A5", "A5: rota la evidencia"), ("A10", "A10: rota la evidencia"),
            ("A12", "A12: rota el período"), ("A9", "A9: se escapa"),
            ("A13", "A13: se escapa"), ("B5", "B5: rotación de más"))


def trayectorias(c: dict) -> tuple[dict[str, str], str, dict]:
    """Una unidad por familia (la primera en orden): ℓ, S y bits de la clave vigente, llamada a llamada."""
    por_fam: dict = defaultdict(list)
    for key in c["trazas"]:
        por_fam[c["fam_unidad"][key]].append(key)
    archivos, paneles, info = {}, [], {}
    for fam, titulo in EJEMPLOS:
        key = sorted(por_fam[fam])[0]
        traza = c["trazas"][key]
        bits = _bits_vigentes(traza)
        rows = [[i + 1, r["l"], r["S"], b, 1 if r["envio"] else 0, 1 if r["rot"] else 0]
                for i, (r, b) in enumerate(zip(traza, bits))]
        archivos[f"tray_{fam}.dat"] = dat(["i", "l", "S", "bits", "envio", "rot"], rows)
        rots = [(i + 1, r["regla"], r["rot"]) for i, r in enumerate(traza) if r["rot"]]
        envios = [i + 1 for i, r in enumerate(traza) if r["envio"]]
        s_max = max(r["S"] for r in traza)
        info[fam] = {"unidad": key, "llamadas": len(traza), "rotaciones": [(i, reg, s) for i, reg, s in rots],
                     "envios": envios, "bits_max": max(bits), "S_max": s_max,
                     "frenado": c["por_unidad"][key]["prevented"]}
        # La sesión normal acumula mucha más evidencia que un ataque frenado: lleva su propia escala.
        alto = s_max > 13
        opciones = f"title={{{titulo}}}, xmax={len(traza) + 1}"
        if alto:
            opciones += ", ymin=-5.6, ymax=34, ytick={0,10,20,30}"
        tope = 32.5 if alto else 13.4
        marcas = "".join(f"\\draw[oro, line width=0.9pt] (axis cs:{i},0) -- (axis cs:{i},{tope});\n" for i, _, _ in rots)
        ticks = "".join(f"\\draw[tinta, line width=0.5pt] (axis cs:{i},-1.9) -- (axis cs:{i},-0.9);\n" for i in envios)
        nota = (f"{int(max(bits))} bits salieron" if fam.startswith("A") else "nada bloqueado")
        # La nota va en la esquina que la curva deja libre.
        izquierda = bool(rots) and rots[0][0] > len(traza) / 2
        esquina = ("north west", "0.03,0.97") if izquierda else ("north east", "0.985,0.97")
        paneles.append(
            "\\nextgroupplot[%s]\n"
            "\\addplot[tinta, line width=0.7pt, const plot] table[x=i, y=S] {datos/tray_%s.dat};\n"
            "%s%s"
            "\\node[anchor=%s, font=\\scriptsize, text=ceniza] at (rel axis cs:%s) {%s};\n"
            % (opciones, fam, marcas, ticks, esquina[0], esquina[1], nota))
    return archivos, "".join(paneles), info


def rejilla(c: dict, mec: dict) -> str:
    """El set de prueba entero, una casilla por ataque o por sesión normal, con las marcas del proxy."""
    por_fam: dict = defaultdict(list)
    for key in c["trazas"]:
        por_fam[c["fam_unidad"][key]].append(key)
    nombres = {"A5": "Por un canal de confianza", "A7": "Repartida entre tres agentes", "A10": "Ofuscada con XOR",
               "A12": "Goteo lento y ráfaga final", "A9": "A su propio destino permitido",
               "A13": "En mensajes de \\emph{commit}", "B3": "SHA y UUID que parecen claves",
               "B4": "Despliegue y rotación legítimos", "B5": "Contenido ajeno lleno de claves"}
    out, y = [], 0.0
    paso, lado = 0.27, 0.205
    ancho = 30 * paso
    for bloque, fams, titulo, cola in (("ataque", FAMILIAS_A, "Ataques", "frenados"),
                                       ("normal", ["B3", "B4", "B5"], "Sesiones normales difíciles", "rotó de más")):
        n_bloque = sum(len(por_fam[f]) for f in fams)
        out.append(f"\\node[anchor=south west, font=\\footnotesize\\sffamily\\bfseries] at (0,{y + lado + 0.1:.3f}) "
                   f"{{{titulo} ({n_bloque})}};\n")
        out.append(f"\\node[anchor=south west, font=\\footnotesize\\sffamily, text=ceniza] at ({ancho + 0.05:.3f},{y + lado + 0.1:.3f}) "
                   f"{{{cola}}};\n")
        for fam in fams:
            keys = sorted(por_fam[fam])
            out.append(f"\\node[anchor=east, font=\\footnotesize] at (-0.2,{y + lado / 2:.3f}) "
                       f"{{\\textbf{{{fam}}}\\enspace {nombres[fam]}}};\n")
            k = 0
            for i, key in enumerate(keys):
                x = i * paso
                if bloque == "ataque":
                    estilo = "casilla frenado" if c["por_unidad"][key]["prevented"] else "casilla escapa"
                    k += bool(c["por_unidad"][key]["prevented"])
                else:
                    r = any(t["rot"] for t in c["trazas"][key])
                    estilo = "casilla rotada" if r else "casilla vacia"
                    k += r
                out.append(f"\\path[{estilo}] ({x:.3f},{y:.3f}) rectangle ++({lado},{lado});\n")
            out.append(f"\\node[anchor=west, font=\\footnotesize] at ({ancho + 0.05:.3f},{y + lado / 2:.3f}) "
                       f"{{{k} de {len(keys)}}};\n")
            y -= paso + 0.07
        y -= 0.62
    return "".join(out)


def latencia(lat: list[float]) -> tuple[str, dict]:
    xs = sorted(lat)
    q = lambda p: xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]
    info = {"n": len(xs), "p50": q(0.50), "p95": q(0.95), "p99": q(0.99), "max": xs[-1],
            "maquina": f"{platform.machine()}, Python {platform.python_version()}"}
    tex = "".join(f"\\newcommand{{\\Lat{k}}}{{{v}}}\n" for k, v in (
        ("N", num(info["n"])), ("Mediana", num(info["p50"], 2)), ("NoventaCinco", num(info["p95"], 2)),
        ("NoventaNueve", num(info["p99"], 2)), ("Max", num(info["max"], 1))))
    return tex, info


# --------------------------------------------------------------------------- todo junto

def generar() -> dict[str, str]:
    archivos: dict[str, str] = {}
    cifras: dict = {}

    ev = evaluacion()
    cifras["evaluacion"] = ev
    systems = _json("results/proxy_flags/systems.json")
    archivos["tab_sistemas.tex"], cifras["sistemas"] = tabla_sistemas(systems)
    archivos["tab_sistemas_familia.tex"] = tabla_sistemas_familia(cifras["sistemas"])
    cambios = _json("results/proxy_flags/changes.json")
    archivos["tab_cambios.tex"] = tabla_cambios(cambios)
    cifras["cambios"] = cambios
    cifras["pruebas"] = _json("results/test/report.json")
    cifras["corridas"] = {k: _json(f"results/{k}/RUN.json") for k in ("test", "val", "proxy_flags", "adaptive", "short_fragments")}
    ad = _json("results/adaptive/summary.json")
    archivos["tab_adaptativo.tex"], cifras["adaptativo"] = tabla_adaptativo(ad)
    archivos["tab_adaptativo_familia.tex"] = tabla_adaptativo_familia(ad)
    sf = _json("results/short_fragments/summary.json")
    archivos["tab_fragmentos_matriz.tex"], archivos["tab_fragmentos.tex"], cifras["fragmentos"] = tabla_fragmentos(sf)

    archivos["tab_modelo.tex"], archivos["fig_modelo.tex"], cifras["modelo"] = modelo()
    archivos["tab_busqueda_rot.tex"], archivos["tab_busqueda_bits.tex"], cifras["busqueda"] = busqueda()
    archivos["demo_goteo.dat"], archivos["demo_enjambre.dat"], cifras["demo"] = demo()
    archivos["tab_grafo.tex"], cifras["grafo"] = grafo()

    c = corrida()
    (archivos["tab_mecanismo.tex"], archivos["tab_normales.tex"], archivos["tab_ell.tex"],
     cifras["mecanismo"], cifras["ell"]) = mecanismo(c, ev)
    tray, archivos["fig_trayectorias.tex"], cifras["trayectorias"] = trayectorias(c)
    archivos.update(tray)
    archivos["fig_rejilla.tex"] = rejilla(c, cifras["mecanismo"])
    archivos["latencia.tex"], cifras["latencia"] = latencia(c["lat"])
    cifras["set_prueba"] = {"llamadas": c["llamadas"], "unidades": c["unidades"], "sesiones": c["sesiones"],
                            "envios_etiquetados": len(c["labels"])}
    sin_latencia = {k: v for k, v in cifras.items() if k != "latencia"}
    archivos["cifras.json"] = json.dumps(sin_latencia, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n"
    archivos["latencia.json"] = json.dumps(cifras["latencia"], ensure_ascii=False, indent=2) + "\n"
    return archivos


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="compara lo regenerado con lo guardado en datos/")
    args = ap.parse_args()
    t0 = time.perf_counter()
    archivos = generar()
    no = NO_COMPARAR | {"latencia.json"}
    if args.check:
        malos = [n for n, txt in archivos.items() if n not in no
                 and (not (OUT / n).is_file() or (OUT / n).read_text(encoding="utf-8") != txt)]
        sobran = [p.name for p in OUT.glob("*") if p.name not in archivos]
        if malos or sobran:
            print("datos/ no coincide con el repositorio:", ", ".join(malos + [f"sobra {s}" for s in sobran]))
            raise SystemExit(1)
        print(f"datos/ coincide con el repositorio ({len(archivos) - len(no)} archivos comparados, "
              f"{time.perf_counter() - t0:.0f} s)")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for n, txt in archivos.items():
        (OUT / n).write_text(txt, encoding="utf-8", newline="\n")
    print(f"{len(archivos)} archivos en {OUT.relative_to(ROOT)} ({time.perf_counter() - t0:.0f} s)")


if __name__ == "__main__":
    main()
