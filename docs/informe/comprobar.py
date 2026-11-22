"""Comprueba el texto del informe contra los datos y contra las reglas de redacción del equipo.

    python docs/informe/comprobar.py

Tres cosas:

1. Las cifras escritas en la prosa son las de `datos/cifras.json` (que `hacer_datos.py` saca de
   `results/`, `models/` y `redteam/`). Si los resultados cambian, este script dice qué frase quedó vieja.
2. «180 de 180» nunca aparece sin decir, en el mismo párrafo, que es con las marcas de las grabaciones
   o del generador. Y no aparecen las frases que el equipo acordó no decir.
3. El LaTeX no trae lo que rompe pdfLaTeX dentro de \\cod{...}.

Sale con código 1 si algo falla.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEX = (sorted((HERE / "secciones").glob("*.tex")) + sorted((HERE / "figuras").glob("*.tex"))
       + [HERE / "README.md"])
# La misma regla de los textos públicos del repositorio (demo/viz/tests/test_results.py, #180).
CON_SU_SALVEDAD = re.compile(r"(marcas|banderas).*?(grabaciones|generador)|(grabaciones|generador).*?(marcas|banderas)",
                             re.IGNORECASE | re.DOTALL)

NO_DECIR = (
    "agente comprometido",          # vocabulario que el equipo evita
    "otro equipo de personas",      # el rojo fue una sesión aparte, no otro grupo
    "equipo independiente",
    "frenó a un modelo real",       # ningún modelo siguió la instrucción
    "detiene el 100",
    "\\qty{100}{\\percent} de los ataques",
    "casos independientes,",        # son 30 réplicas de seis plantillas
    "sin costo en el uso normal",
)


def miles(n) -> str:
    return f"\\num{{{n}}}"


def esperadas(c: dict) -> list[tuple[str, str]]:
    """(de qué cifra se trata, texto que debe aparecer tal cual en la prosa)."""
    ev, sis, b = c["evaluacion"], c["sistemas"], c["busqueda"]
    a, n, m, mec = ev["ataques"], ev["normales"], ev["medicion"], c["mecanismo"]
    ad, fr, demo, mod = c["adaptativo"], c["fragmentos"], c["demo"], c["modelo"]
    ell = c["ell"]["por_clase"]["HTTP a \\texttt{attacker.test}"]
    t = c["pruebas"]["tests"]
    el = b["elegida"]
    coma = lambda x: str(x).replace(".", ",")
    return [
        ("ataques frenados con las marcas del proxy", f"{a['frenados']} de {a['n']}"),
        ("familias frenadas", {4: "cuatro", 6: "seis"}[a["familias_frenadas"]] + " de las seis familias"),
        ("llamadas normales expuestas", miles(n["llamadas"])),
        ("sesiones normales con rotación de más", f"{n['con_rotacion_de_mas']} de las {n['sesiones_dificiles']}"),
        ("rotaciones de más", f"{n['rotaciones_de_mas']}, en {n['con_rotacion_de_mas']} de las"),
        ("rotaciones por mil", coma(n["rotaciones_por_mil"]) + " por cada"),
        ("llamadas del set", miles(m["llamadas"])),
        ("llamadas cuyas marcas cambian", f"{m['llamadas_que_cambian']} de las {miles(m['llamadas'])}"),
        ("sello del set", ev["sello"]["sha256"]),
        ("archivos del sello", f"{ev['sello']['archivos']}\n    archivos"),
        ("hash de la configuración congelada", ev["congelado"]["hash"]),
        ("regla simple, marcas del proxy", f"frena {sis['ours']['proxy']} y la regla {sis['taint_rule']['proxy']}"),
        ("rotaciones por mil de la regla simple", coma(f"{sis['taint_rule']['rot_1000']:.2f}") + " contra"),
        ("sin evidencia", f"Frena {sis['no_evidence']['proxy']}:"),
        ("combinaciones de la grilla", f"grilla de {b['combinaciones']} combinaciones"),
        ("combinaciones que cumplen las metas", f"Cumplen {b['cumplen_metas']} de las {b['combinaciones']}"),
        ("empatadas con la elegida", f"Hay {b['empatadas_con_la_elegida']} combinaciones que empatan"),
        ("empatadas sin rotaciones", f"De esas {b['empatadas_con_la_elegida']}, {b['empatadas_sin_rotaciones']} no rotaron"),
        ("frontera de Pareto", f"Hay {b['pareto']} combinaciones con las"),
        ("umbrales elegidos", f"$b = {el['b']}$, $\\brot = {el['b_rot']}$, $\\lrot = \\num{{{el['lambda_rot']}}}$, $T = {el['T']}$"),
        ("A12: por evidencia y por período",
         f"En {mec['A12']['reglas']['evidencia']} sesiones la evidencia rota"),
        ("A12: por período", f"En las otras {mec['A12']['reglas']['período']}"),
        ("B5: rotaciones", f"({mec['B5']['rotaciones']} rotaciones)"),
        ("B3 y B4: rotaciones", f"({mec['B3']['rotaciones'] + mec['B4']['rotaciones']} rotaciones)"),
        ("A9: bits que salen", f"Salen {int(mec['A9']['max_bits'])} bits de la primera clave"),
        ("llamadas a attacker.test con el tope", f"a {ell['+B']} de los {ell['+B'] + ell['medio']} envíos"),
        ("llamadas en sesiones normales", miles(mec["llamadas_benignas"])),
        ("envíos etiquetados", miles(c["set_prueba"]["envios_etiquetados"])),
        ("adaptativo: máximo y mediana",
         f"el máximo observado es {int(ad['test_ours']['max_max_bits'])} y la mediana, {int(ad['test_ours']['median_max_bits'])}"),
        ("adaptativo: bloqueos tras escalar", f"bloquea {ad['test_ours']['blocked_after_escalation']} envíos"),
        ("fragmentos: máximo de los largos", f"El máximo, {int(fr['max_largos'])} bits"),
        ("fragmentos: máximo de los cortos", f"A lo más {int(fr['max_cortos_congelada'])} bits"),
        ("fragmentos: sin evidencia",
         f"{fr['pasan_por_sistema']['no_evidence']} de {fr['cortos_por_sistema']['no_evidence']} combinaciones"),
        ("fragmentos: demo", f"\\esp{{hook}}, {fr['pasan_por_sistema']['demo']} de {fr['cortos_por_sistema']['demo']}"),
        ("demo: llamada en que rota", f"rota en la llamada {demo['rota_en'][0]}, con {int(demo['bits_al_rotar'])} bits"),
        ("enjambre: llamada en que rota", f"rota en la llamada {demo['enjambre']['rota_en'][0]}"),
        ("enjambre: máximo por agente", f"ningún agente pasa de {int(demo['enjambre']['max_por_agente'])}"),
        ("ajuste: llamadas normales", miles(mod["n_benign_calls"])),
        ("ajuste: envíos de ataque", f"los {mod['n_attack_calls']} envíos etiquetados"),
        ("ajuste: saturación", f"\\qty{{{mod['clip_fraction'] * 100:.2f}}}{{\\percent}}"),
        ("grafo de la demo", f"{c['grafo']['nodos']} nodos"),
        ("T3", f"{t['T3']['b']} ataques que Alicanto frena"),
        ("T2: cota inferior", f"\\num{{{t['T2']['ci'][0]:.4f}}}"),
    ]


def parrafos(texto: str) -> list[str]:
    return [p for p in re.split(r"\n\s*\n", texto) if p.strip()]


def cod_args(texto: str) -> list[tuple[str, int]]:
    out = []
    for m in re.finditer(r"\\cod\{", texto):
        i = j = m.end()
        nivel = 1
        while nivel and j < len(texto):
            nivel += {"{": 1, "}": -1}.get(texto[j], 0)
            j += 1
        out.append((texto[i:j - 1], texto.count("\n", 0, m.start()) + 1))
    return out


def main() -> int:
    cifras = json.loads((HERE / "datos" / "cifras.json").read_text(encoding="utf-8"))
    textos = {p: p.read_text(encoding="utf-8") for p in TEX}
    todo = "\n\n".join(textos.values())
    fallas: list[str] = []

    for que, frase in esperadas(cifras):
        if frase not in todo:
            fallas.append(f"cifra: «{que}» debería aparecer como {frase!r}")

    for p, t in textos.items():
        for par in parrafos(t):
            if "180 de 180" in par and not CON_SU_SALVEDAD.search(par):
                fallas.append(f"{p.name}: «180 de 180» sin su salvedad: {' '.join(par.split())[:90]}…")
        plano = " ".join(t.split()).lower()
        for frase in NO_DECIR:
            if frase.lower() in plano:
                fallas.append(f"{p.name}: frase que no se dice: «{frase}»")
        for arg, linea in cod_args(t):
            if any(ord(ch) > 127 for ch in arg) or re.search(r"(?<!\\)[%$#]", arg) or "\n" in arg:
                fallas.append(f"{p.name}:{linea}: \\cod{{{arg[:50]}}} rompe pdfLaTeX")

    for f in fallas:
        print("FALLA", f)
    print(f"{len(esperadas(cifras))} cifras, {sum(len(parrafos(t)) for t in textos.values())} párrafos y "
          f"{sum(len(cod_args(t)) for t in textos.values())} fragmentos de código revisados: "
          + ("todo en orden" if not fallas else f"{len(fallas)} fallas"))
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
