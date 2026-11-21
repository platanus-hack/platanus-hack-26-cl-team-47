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
            self.cur = {"title": "", "body": "", "quote": "", "pendientes": 0, "text": ""}
            self.slides.append(self.cur)
        if self.cur is not None:
            if "pendiente" in cls:
                self.cur["pendientes"] += 1
            self.stack.append((tag, "cita" in cls))

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()
        if tag == "section":
            self.cur = None

    def handle_data(self, data):
        if self.cur is None or not self.stack:
            return
        self.cur["text"] += data + " "
        tags = [t for t, _ in self.stack]
        if "h1" in tags or "h2" in tags:
            self.cur["title"] += data
        elif any(c for _, c in self.stack):
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


def test_doce_laminas():
    assert len(parse()) == 12


def test_sin_internet():
    assert not re.search(r"https?://", HTML)
    for ref in re.findall(r'(?:src|href)="([^"]+)"', HTML):
        assert not ref.startswith("/")


def test_resultados_solo_pendientes_y_sin_cifras():
    s9 = parse()[8]
    assert s9["pendientes"] >= 4
    sin_nombres = re.sub(r"\bT[1-4]\b", "", s9["text"])
    assert not re.search(r"\d", sin_nombres), "la lámina 9 no puede tener cifras"


def test_citas_literales():
    slides = parse()
    assert norm(slides[3]["quote"]) == QUOTE_4
    assert norm(slides[7]["quote"]) == QUOTE_8


def test_maximo_cuarenta_palabras_de_cuerpo():
    """Cuerpo = todo menos el título. Única excepción: la cita literal de la lámina 8
    (41 palabras en el documento v4.0; no se recorta sin visto bueno del líder)."""
    for n, s in enumerate(parse(), 1):
        body = words(s["body"])
        quote = words(s["quote"])
        if n == 8:
            assert not body, "la lámina 8 solo lleva la cita"
            assert len(quote) == 41
            continue
        total = len(body) + len(quote)
        assert total <= 40, f"lámina {n}: {total} palabras"


def test_demo_enlaza_la_pantalla_dividida():
    assert 'href="../demo/viz/split.html"' in HTML
    assert (PITCH.parent / "demo" / "viz" / "split.html").is_file()


def test_guion_doce_secciones_y_pendientes():
    guion = (PITCH / "GUION.md").read_text(encoding="utf-8")
    secciones = re.findall(r"^## (\d+)\. ", guion, flags=re.M)
    assert secciones == [str(i) for i in range(1, 13)]
    assert re.search(r"^## Pendientes", guion, flags=re.M)
    for falta in ("T1", "T2", "T3", "T4", "escenario", "qué pedimos"):
        assert falta in guion
