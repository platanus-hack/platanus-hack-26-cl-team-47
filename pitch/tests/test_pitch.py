"""Tests del esqueleto del pitch (tarea 16a). Sin navegador ni dependencias externas."""

import re
from html.parser import HTMLParser
from pathlib import Path

PITCH = Path(__file__).resolve().parents[1]
HTML = (PITCH / "index.html").read_text(encoding="utf-8")

QUOTE_4 = "«No adivinamos la intención del atacante. Medimos cuánto sabe, y hacemos que robar despacio no sirva.»"
QUOTE_8 = ("«Trabajos de este año muestran que contar la fuga acumulada ve lo que los detectores por turno no ven. "
           "Nosotros lo hacemos sin acceso al modelo, con falsas alarmas medidas, y rotamos el secreto para que lo "
           "filtrado deje de servir.»")


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
            self.stack.append((tag, "cita" in cls, "pendiente" in cls))

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


def words(s):
    return [w for w in re.split(r"\s+", s) if re.search(r"\w", w)]


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def test_trece_laminas():
    assert len(parse()) == 13


def test_sin_internet():
    assert not re.search(r"https?://", HTML)  # las URL de fuentes van en PREGUNTAS.md
    for ref in re.findall(r'(?:src|href)="([^"]+)"', HTML):
        assert not ref.startswith("/")


def test_resultados_solo_pendientes_y_sin_cifras():
    s10 = parse()[9]
    assert s10["pendientes"] >= 4
    sin_nombres = re.sub(r"\bT[1-4]\b", "", s10["text"])
    assert not re.search(r"\d", sin_nombres), "la lámina 10 no puede tener cifras"


def test_citas_literales():
    slides = parse()
    assert norm(slides[3]["quote"]) == QUOTE_4
    assert norm(slides[8]["quote"]) == QUOTE_8


def test_maximo_cuarenta_palabras_de_cuerpo():
    """Cuerpo = todo menos el título, los marcadores PENDIENTE (no son texto final) y los datos
    de las tablas (cifras, no prosa: lámina 8 del enjambre, 16c).
    Única excepción: la cita literal de la lámina 9 (41 palabras en el documento v4.0;
    no se recorta sin visto bueno del líder); su línea menor (tarea 16b) va aparte."""
    for n, s in enumerate(parse(), 1):
        body = words(s["body"])
        quote = words(s["quote"])
        if n == 9:
            assert len(quote) == 41
            assert len(body) <= 40, f"lámina 9: la línea menor tiene {len(body)} palabras"
            continue
        total = len(body) + len(quote)
        assert total <= 40, f"lámina {n}: {total} palabras"


def test_demo_enlaza_la_pantalla_dividida():
    assert 'href="../demo/viz/split.html"' in HTML
    assert (PITCH.parent / "demo" / "viz" / "split.html").is_file()


def test_guion_trece_secciones_y_pendientes():
    guion = (PITCH / "GUION.md").read_text(encoding="utf-8")
    secciones = re.findall(r"^## (\d+)\. ", guion, flags=re.M)
    assert secciones == [str(i) for i in range(1, 14)]
    assert re.search(r"^## Pendientes", guion, flags=re.M)
    for falta in ("T1", "T2", "T3", "T4", "qué pedimos"):  # el escenario ya se decidió (15j)
        assert falta in guion


# ------------------------------------------------ tarea 16b

PREGUNTAS = (PITCH / "PREGUNTAS.md").read_text(encoding="utf-8")
GUION = (PITCH / "GUION.md").read_text(encoding="utf-8")


def test_preguntas_tiene_las_diez_hospital_y_enjambre():
    titulos = re.findall(r"^## \d+\. (.+)$", PREGUNTAS, flags=re.M)
    assert len(titulos) == 12
    claves = ("CaMeL y FIDES", "Chauhan y Revankar", "OCELOT", "detect-secrets", "broker de credenciales",
              "Dónde está la IA", "Qué no detectan", "Rotar no rompe producción", "Son los primeros",
              "resultados son reales", "Por qué un hospital", "varios agentes")
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
    s9 = parse()[8]
    assert "hasta donde encontramos" in s9["body"].lower()


def test_lamina_12_tiene_pendiente():
    assert parse()[11]["pendientes"] >= 1
    assert "LLM" in parse()[11]["pend_text"]


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
    assert 'href="../demo/viz/split.html"' in HTML and "Demo" in slides[6]["text"]
    s = slides[7]
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
    assert "mismo proceso" in sec and "trabajo futuro" in sec
    assert "No encontramos ningún trabajo que lleve una cuenta acumulada por secreto entre agentes".lower() in PREGUNTAS.lower()


def test_guion_usa_cuentagotas_y_dice_el_tiempo_total():
    assert "Cuentagotas" in GUION
    assert not re.search(r"\b(?:con|contra) el medidor\b", GUION)
    assert re.search(r"Tiempo total: \d+ min", GUION)
    assert re.search(r"^## 8\. Y si atacan en enjambre", GUION, flags=re.M)


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
