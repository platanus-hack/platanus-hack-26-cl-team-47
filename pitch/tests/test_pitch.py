"""Tests del esqueleto del pitch (tarea 16a). Sin navegador ni dependencias externas."""

import re
from html.parser import HTMLParser
from pathlib import Path

PITCH = Path(__file__).resolve().parents[1]
HTML = (PITCH / "index.html").read_text(encoding="utf-8")

QUOTE_4 = "«No adivinamos la intención del atacante. Medimos cuánto sabe, y hacemos que robar despacio no sirva.»"


class Slides(HTMLParser):
    """Separa cada <section class="slide">: título (h1/h2), cuerpo, citas y marcadores pendiente."""

    def __init__(self):
        super().__init__()
        self.slides, self.cur, self.stack = [], None, []

    def handle_starttag(self, tag, attrs):
        cls = (dict(attrs).get("class") or "").split()
        if tag == "section" and "slide" in cls:
            self.cur = {"title": "", "body": "", "quote": "", "pendientes": 0, "pend_text": "", "text": "", "table": ""}
            self.slides.append(self.cur)
        if self.cur is not None:
            if "pendiente" in cls:
                self.cur["pendientes"] += 1
            # «table» y «nota-pie» (cita de fuente) van aparte: no cuentan como cuerpo.
            self.stack.append((tag if "nota-pie" not in cls else "table", "cita" in cls, "pendiente" in cls))

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()
        if tag == "section":
            self.cur = None

    def handle_data(self, data):
        if self.cur is None or not self.stack:
            return
        self.cur["text"] += data + " "
        tags = [t for t, _, _ in self.stack]
        if "h1" in tags or "h2" in tags:
            self.cur["title"] += data
        elif "table" in tags and not any(p for _, _, p in self.stack):
            self.cur["table"] += data + " "  # datos de una tabla: no cuentan como cuerpo
        elif any(p for _, _, p in self.stack):
            self.cur["pend_text"] += data + " "
        elif any(c for _, c, _ in self.stack):
            self.cur["quote"] += data
        else:
            self.cur["body"] += data + " "


def parse():
    p = Slides()
    p.feed(HTML)
    return p.slides


def slide(titulo):
    """La lámina cuyo título contiene `titulo` (sin importar mayúsculas)."""
    for sl in parse():
        if titulo.lower() in sl["title"].lower():
            return sl
    raise AssertionError(f"no hay lámina con título {titulo!r}")


def idx(titulo):
    return parse().index(slide(titulo))


def words(s):
    return [w for w in re.split(r"\s+", s) if re.search(r"\w", w)]


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def test_catorce_laminas():
    assert len(parse()) == 16


def test_sin_internet():
    assert not re.search(r"https?://", HTML)  # las URL de fuentes van en PREGUNTAS.md
    for ref in re.findall(r'(?:src|href)="([^"]+)"', HTML):
        assert not ref.startswith("/")


def test_resultados_con_las_cifras_de_la_evaluacion_final_y_sus_limites():
    """16f: la lámina 10 lleva las cifras reales del set sellado y sus dos límites, en la misma lámina."""
    s10 = slide("180 ataques")
    assert s10["pendientes"] == 0
    assert norm(s10["title"]) == "180 ataques de seis familias nuevas: ninguno sacó más de 32 de 160 bits"
    for cifra in ("180", "32", "150", "34 de 90", "5.879", "16,7 % (30)", "38,9 % (70)"):
        assert cifra in s10["text"], cifra
    assert "Costo: rotó de más en 34 de 90 sesiones benignas difíciles; no bloqueó ninguna llamada benigna." in norm(s10["body"])
    assert ("Ataques grabados. Contra un atacante simulado que se adapta: 180 de 180, deteniendo las salidas "
            "tras tres rotaciones.") in norm(s10["body"])
    for col in ("Alicanto", "Sin rotación", "Presupuesto de bits (réplica)"):
        assert col in s10["text"], col


def test_citas_literales():
    assert norm(slide("La idea")["quote"]) == QUOTE_4


def test_maximo_cuarenta_palabras_de_cuerpo():
    """Cuerpo = todo menos el título, los marcadores PENDIENTE (no son texto final) y los datos
    de las tablas y las notas al pie de fuente (lámina 8 del enjambre, 16c; lámina 9 de competidores, 16d)."""
    for n, s in enumerate(parse(), 1):
        body = words(s["body"])
        quote = words(s["quote"])
        total = len(body) + len(quote)
        assert total <= 40, f"lámina {n}: {total} palabras"


def test_demo_enlaza_la_pantalla_dividida():
    assert 'href="../demo/viz/split.html"' in HTML
    assert (PITCH.parent / "demo" / "viz" / "split.html").is_file()


def test_guion_cinco_bloques_y_pendientes():
    guion = (PITCH / "GUION.md").read_text(encoding="utf-8")
    secciones = re.findall(r"^## (\d+)\. ", guion, flags=re.M)
    assert secciones == [str(i) for i in range(1, 6)]
    assert re.search(r"^## Pendientes", guion, flags=re.M)
    for falta in ("T1", "T2", "T3", "T4", "qué pedimos"):  # el escenario ya se decidió (15j)
        assert falta in guion


# ------------------------------------------------ tarea 16b

PREGUNTAS = (PITCH / "PREGUNTAS.md").read_text(encoding="utf-8")
GUION = (PITCH / "GUION.md").read_text(encoding="utf-8")


def test_preguntas_tiene_las_diez_hospital_y_enjambre():
    titulos = re.findall(r"^## \d+\. (.+)$", PREGUNTAS, flags=re.M)
    assert len(titulos) == 21
    claves = ("permisos de Claude Code", "falsos positivos", "clasificador o un LLM", "comprometen el proxy",
              "instala", "CaMeL y FIDES", "Chauhan y Revankar", "OCELOT", "detect-secrets", "Pipelock", "broker de credenciales",
              "Dónde está la IA", "Qué no detectan", "Rotar no rompe producción", "Son los primeros",
              "resultados son reales", "Por qué un hospital", "varios agentes", "se adapta a la rotación",
              "momentos aleatorios", "se llama Alicanto")
    for clave, titulo in zip(claves, titulos):
        assert clave in titulo, f"falta la pregunta sobre {clave!r}"


def test_cada_respuesta_cita_su_fuente():
    secciones = re.split(r"^## \d+\. ", PREGUNTAS, flags=re.M)[1:]
    assert all("Fuente:" in sec for sec in secciones)


def _sin_pregunta_que_lo_niega(texto):
    return re.sub(r"^## \d+\. ¿Son los primeros\?.*?(?=^## |\Z)", "", texto, flags=re.M | re.S)


def test_frases_prohibidas():
    for nombre, texto in (("index.html", HTML), ("GUION.md", GUION), ("PREGUNTAS.md", PREGUNTAS)):
        t = _sin_pregunta_que_lo_niega(texto).lower()
        assert "somos los primeros" not in t, nombre
        assert "90 %" not in t and "90%" not in t, nombre
        assert "persistente entre sesiones" not in t, nombre


def test_lamina_9_dice_hasta_donde_encontramos():
    s9 = slide("Qué hace cada uno")
    assert "hasta donde encontramos" in s9["body"].lower()


def test_lamina_de_la_ia_dice_el_resultado_con_modelos_reales():
    assert slide("Dónde está la IA")["pendientes"] == 0
    assert "ninguno obedeció" in slide("Dónde está la IA")["body"]


# ------------------------------------------------ escenario del hospital (15j)

def test_escenario_en_el_pitch():
    assert "PENDIENTE: contar el escenario" not in GUION
    assert "Tres Cóndores" in GUION
    assert "Tres Cóndores" in (PITCH / "slides.js").read_text(encoding="utf-8")
    assert "ficticio" in (PITCH / "slides.js").read_text(encoding="utf-8")


def test_nada_prohibido_del_escenario_en_pitch():
    for f in PITCH.rglob("*"):
        if f.is_file() and f.suffix in (".md", ".html", ".js", ".css") and "tests" not in f.parts:
            text = f.read_text(encoding="utf-8")
            assert "1 de diciembre de 2026" not in text, f.name
            assert "Hospital Clínico" not in text, f.name


def test_pregunta_del_hospital_solo_con_datos_verificados_y_url():
    sec = PREGUNTAS.split("¿Por qué un hospital?")[1].split("\n## ")[0]
    urls = re.findall(r"https://\S+?(?=\)|\s|$)", sec)
    assert set(urls) <= {"https://www.suseso.gob.cl/612/w3-propertyvalue-130626.html",
                         "https://www.cariola.cl/app/uploads/2025/03/Alerta-Legal_04.03.2025.pdf"}
    assert len(urls) >= 2


# ------------------------------------------------ enjambre (16c)

ANTHROPIC = "https://www.anthropic.com/news/disrupting-AI-espionage"
GTIG = "https://cloud.google.com/blog/topics/threat-intelligence/agentic-threat-activity-crosses-a-significant-threshold"


def test_lamina_del_enjambre_tras_la_demo():
    slides = parse()
    demo = next(k for k, sl in enumerate(slides) if "Demo" in sl["text"] and not sl["title"])
    assert 'href="../demo/viz/split.html"' in HTML
    s = slides[demo + 1]
    assert "enjambre" in s["title"].lower()
    for cifra in ("32", "200", "401"):
        assert cifra in s["text"], cifra
    assert "La cuenta es por clave, no por agente." in s["body"]
    assert "Cinco agentes se reparten la fuga: cada uno saca solo dos fragmentos." in s["body"]
    assert 'href="../demo/viz/split.html?demo=enjambre"' in HTML


def test_cifras_del_enjambre_salen_de_la_corrida_versionada():
    import json
    fx = PITCH.parent / "demo" / "viz" / "fixtures"
    left = [json.loads(x) for x in (fx / "swarm_left.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    right = [json.loads(x) for x in (fx / "swarm_right.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    assert not [e for e in left if e["kind"] == "rotation"] and left[-1]["data"]["status"] == 200
    per_agent = {}
    for e in left:
        if e["kind"] == "decision":
            b = e["data"]["leak"].get("SECRET_1", {}).get("bits", 0.0)
            per_agent[e["session_id"]] = max(per_agent.get(e["session_id"], 0.0), b)
    assert max(per_agent.values()) == 32
    rot = [e for e in right if e["kind"] == "rotation"]
    t_of = {e["call_id"]: e["data"]["t"] for e in right if e["kind"] == "tool_call"}
    assert len(rot) == 1 and t_of[rot[0]["call_id"]] == 32 and right[-1]["data"]["status"] == 401


def test_pregunta_del_enjambre_con_fuentes():
    assert "¿Y si el atacante reparte la fuga entre varios agentes?" in PREGUNTAS
    sec = PREGUNTAS.split("¿Y si el atacante reparte la fuga entre varios agentes?")[1]
    assert ANTHROPIC in sec and GTIG in sec
    assert "misma máquina" in sec and "trabajo futuro" in sec


def test_guion_usa_alicanto_y_dice_el_tiempo_total():
    assert "Alicanto" in GUION
    assert not re.search(r"\b(?:con|contra) el medidor\b", GUION)
    assert re.search(r"Tiempo total: \d+ min", GUION)
    assert re.search(r"^## 3\. El enjambre", GUION, flags=re.M)


def _pitch_files():
    for f in PITCH.rglob("*"):
        if f.is_file() and f.suffix in (".md", ".html", ".js", ".css") and "tests" not in f.parts:
            yield f


def test_sin_esteganografia_ni_primeros():
    niega = re.compile(r"\b(no|ni|sin)\b", re.I)
    for f in _pitch_files():
        text = f.read_text(encoding="utf-8")
        for frase in re.split(r"(?<=[.!?»])\s+", text):
            if "esteganograf" in frase.lower():
                assert niega.search(frase), f"{f.name}: {frase!r}"
        assert "somos los primeros" not in _sin_pregunta_que_lo_niega(text).lower(), f.name


def test_anthropic_no_fue_un_enjambre():
    for f in _pitch_files():
        t = f.read_text(encoding="utf-8").lower()
        assert not re.search(r"anthropic[^.]{0,120}\benjambre\b(?![»\"])", t) or "no fue un «enjambre»" in t, f.name


# ------------------------------------------------ guion a 3 minutos (15m)

def _texto_hablado(guion):
    """Las secciones numeradas (## N. …), sin «Si sobra tiempo o preguntan» ni las tablas."""
    partes = re.split(r"^(## .*)$", guion, flags=re.M)
    return " ".join(cuerpo for titulo, cuerpo in zip(partes[1::2], partes[2::2])
                    if re.match(r"## \d+\. ", titulo))


def test_texto_hablado_cabe_en_tres_minutos():
    assert "## Si sobra tiempo o preguntan" in GUION
    assert len(words(_texto_hablado(GUION))) <= 450


def test_tabla_de_tiempos_con_total():
    assert re.search(r"^## Tiempos", GUION, flags=re.M)
    m = re.search(r"\*\*Total\*\* \| \*\*(\d+)\*\* \| \*\*(\d+) min (\d+) s", GUION)
    assert m and int(m.group(2)) * 60 + int(m.group(3)) <= 180
    for clave in ("problema", "Alicanto", "200", "401", "enjambre", "Límites"):
        assert clave in _texto_hablado(GUION) or clave in GUION, clave


# ------------------------------------------------ novedad corregida (16d)

FRASE_NOVEDAD = ("Hasta donde encontramos, nadie usa la fuga parcial medida de una credencial (en bits, sumada "
                 "entre llamadas, codificaciones y agentes) para rotarla antes de que se complete.")


def test_frases_desmentidas_fuera_de_pitch():
    for f in _pitch_files():
        t = f.read_text(encoding="utf-8")
        for frase in ("ninguna cuenta fragmentos", "ningún filtro", "6,64", "Paubox", "21.719",
                      "PENDIENTE: nombre del escenario", "nadie junta fragmentos", "No encontramos ningún trabajo",
                      "marcados como rotables"):
            assert frase.lower() not in t.lower(), f"{f.name}: {frase}"


def test_preguntas_nombran_competidores():
    for clave in ("Pipelock", "AgentBrake", "2607.07368", "2605.31593", "tarea o trayectoria",
                  "https://pipelab.org/blog/cross-request-exfiltration/", "https://github.com/Ujjwaljain16/AgentBrake",
                  "3 rotaciones por secreto en 200 llamadas",
                  "La familia de sustitución propia quedó en validación, no en el set de prueba"):
        assert clave in PREGUNTAS, clave
    titulos = re.findall(r"^## (\d+)\. (.+)$", PREGUNTAS, flags=re.M)
    i = next(k for k, (_, t) in enumerate(titulos) if "pasarela MCP" in t)
    assert "Pipelock ya reensambla fragmentos" in titulos[i + 1][1]
    assert [int(n) for n, _ in titulos] == list(range(1, len(titulos) + 1))


def test_lamina_de_competidores():
    s = slide("Qué hace cada uno")
    assert "Pipelock" in s["text"] and "AgentBrake" in s["text"] and "Alicanto" in s["text"]
    assert FRASE_NOVEDAD in norm(s["body"])
    assert "Según la documentación pública de cada proyecto, leída el 21 de noviembre de 2026" in norm(s["text"])


def test_lamina_final_con_pedido():
    s = slide("Usuario y cierre")
    assert s["pendientes"] == 0 and "piloto" in s["body"]
    assert idx("Usuario y cierre") < idx("Respaldo")   # el pedido va en el pitch, no en el respaldo
    assert "para que lo confirme una persona del equipo" in GUION


def test_demo_dice_que_decide_solo_el_contador():
    assert "la demo usa solo el contador de bits; la configuración evaluada suma la evidencia acumulada" in GUION
    assert "independiente del detector" in PREGUNTAS


# ------------------------------------------------ pregunta del track y cifras (16d, segundo comentario)

def test_guion_abre_con_el_nombre_y_la_pregunta_del_track():
    """16e: la primera frase hablada dice «Alicanto»; la segunda es la pregunta del track."""
    frases = re.split(r"(?<=[.»?])\s+", _texto_hablado(GUION).strip())
    assert "Alicanto" in frases[0]
    assert "¿cómo te darías cuenta?" in frases[1]
    assert "Alicanto es ese monitor: mide cuánta clave ya salió y la cambia antes de que sirva." in GUION


def test_lamina_del_problema_situa_el_track():
    assert "AI control: visibilidad y control sobre un agente que puede estar actuando en contra tuya" in slide("El problema")["text"]


def test_lamina_36_horas():
    s = slide("36 horas")
    assert idx("36 horas") > idx("Respaldo")   # en el respaldo (16e)
    for clave in ("tests automáticos", "80 + 80 + 180", "no vio el detector", "sin internet"):
        assert clave in s["text"], clave
    assert "PR" not in s["text"].split() and "commits" not in s["text"].lower()
    assert "python -m pytest -q" in GUION and "redteam/SELLO.md" in GUION


def test_ia_blanco_y_vector_sin_llm_real():
    sec = PREGUNTAS.split("¿Dónde está la IA")[1].split("\n## ")[0]
    assert "blanco y el vector" in sec and "determinista a propósito" in sec
    assert "docs/LLM_EN_VIVO.md" in sec and "ninguno la obedeció" in sec
    assert "PENDIENTE" not in sec


# ------------------------------------------------ cifras de la evaluación final (16f)

def _frases(texto):
    """Frases de un archivo: en HTML, cada línea sin etiquetas; en el resto, partidas por puntuación."""
    texto = re.sub(r"<[^>]+>", " ", texto)
    return [f for linea in texto.splitlines() for f in re.split(r"(?<=[.!?»])\s+", linea)]


def _sin_100_suelto(path):
    for f in _frases(path.read_text(encoding="utf-8")):
        if re.search(r"100\s?%", f):
            assert "grabados" in f or "nuevas" in f, f"{path.name}: {f.strip()!r}"


def test_nunca_100_por_ciento_a_secas():
    for f in _pitch_files():
        if f.suffix != ".css":   # en CSS «100%» es una medida, no una afirmación
            _sin_100_suelto(f)
    _sin_100_suelto(PITCH.parent / "demo" / "viz" / "results.html")


def test_guion_cifra_contraste_costo_y_limite_en_orden():
    hablado = norm(_texto_hablado(GUION)).lower()
    partes = ["180 de 180 ataques de familias que el detector nunca vio; ninguno pasó de 32 bits de 160",
              "sin rotación, 150 de 180 lo logran",
              "cuando duda, rota en vez de bloquear: rotó de más en 34 de 90 casos difíciles y no interrumpió ninguno",
              "son ataques grabados; contra uno que se adapta tenemos un tope de tres rotaciones y después bloqueo"]
    pos = [hablado.find(x) for x in partes]
    assert all(x >= 0 for x in pos), list(zip(partes, pos))
    assert pos == sorted(pos)
    assert "detiene el 100" not in GUION.lower()


def test_preguntas_con_cifras_reales():
    for clave in ("150 ataques que nosotros prevenimos y ella no, 0 al revés", "0 llamadas benignas bloqueadas de 5.879",
                  "40 de 180", "`results/test/LECTURA.md`", "`redteam/SELLO.md`",
                  "180 de 180 ataques no pasan de 96 bits", "tráfico sintético"):
        assert clave.lower() in PREGUNTAS.lower(), clave
    assert "PENDIENTE: la cifra T3" not in PREGUNTAS and "PENDIENTE: la corrida final" not in PREGUNTAS


def test_lamina_36_horas_nueve_sistemas():
    s = next(sl for sl in parse() if "36 horas" in sl["title"])
    assert s["pendientes"] == 0 and "9" in s["text"] and "sistemas comparados" in s["text"]


# ------------------------------------------------ formato de finales (16e)

def test_orden_de_las_laminas_sigue_al_guion():
    slides = parse()
    assert slides[0]["title"] == "Alicanto" and "¿cómo te darías cuenta?" in slides[0]["text"]
    assert "Demo" in slides[1]["text"]
    assert "enjambre" in slides[2]["title"].lower()
    assert slides[3]["title"] == "Qué es real y qué es simulado"
    assert slides[4]["title"].startswith("180 ataques")
    assert slides[5]["title"] == "Usuario y cierre"
    assert slides[6]["title"] == "Respaldo"


def test_real_y_simulado_en_lamina_y_guion():
    s = slide("Qué es real y qué es simulado")
    for clave in ("proxy", "motor", "gestor de secretos", "servidor del atacante", "sintéticas", "ficticio",
                  "guion reproducible"):
        assert clave in s["text"], clave
    assert ("El proxy, el motor, el gestor de secretos y el servidor del atacante son reales y corren aquí. Las claves "
            "son sintéticas, los servidores son locales y el hospital es ficticio. El agente de la demo es un guion "
            "reproducible.") in norm(_texto_hablado(GUION))


def test_texto_hablado_sin_jerga():
    hablado = _texto_hablado(GUION)
    for palabra in ("CUSUM", "min-entropía", "GFF", "DAG", "features"):
        assert palabra not in hablado, palabra
    assert "pinza" not in hablado.lower()


def test_laminas_respaldo_y_36_horas():
    assert slide("Respaldo") and slide("36 horas")


def test_preguntas_que_mas_se_repiten():
    assert "## Las que más se repiten" in PREGUNTAS and "permisos" in PREGUNTAS
    titulos = re.findall(r"^## (\d+)\. (.+)$", PREGUNTAS, flags=re.M)
    assert "permisos de Claude Code" in titulos[0][1] and "instala" in titulos[4][1]
    assert PREGUNTAS.index("## Las que más se repiten") < PREGUNTAS.index("## 1. ")
    assert "`docs/QUICKSTART.md`" in PREGUNTAS and "PENDIENTE: enlace a `docs/QUICKSTART.md`" not in PREGUNTAS
    assert (PITCH.parent / "docs" / "QUICKSTART.md").is_file()
