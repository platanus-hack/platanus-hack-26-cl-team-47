"""Visualización de la demo interactiva ?demo=elige (tarea 15l). Sin navegador."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

VIZ = Path(__file__).resolve().parents[1]


def test_split_js_conoce_demo_elige_y_las_teclas():
    js = (VIZ / "split.js").read_text(encoding="utf-8")
    for text in ('id: "elige"', "fixtures/encodings.json", "¿Cómo disfraza el atacante cada fragmento?",
                 "Elijan una opción", "speed: 4", "function choiceForKey", "choiceForKey(e.key"):
        assert text in js, text
    assert 'if (e.key === " ")' in js           # la barra espaciadora sigue pausando
    assert "enjambre" in js                       # la demo del enjambre sigue


def test_split_html_tiene_la_franja():
    html = (VIZ / "split.html").read_text(encoding="utf-8")
    for id_ in ('id="chooser"', 'id="chooser-question"', 'id="chooser-buttons"', 'id="chooser-hint"'):
        assert id_ in html
    assert '<section class="chooser" id="chooser" hidden' in html  # sin ?demo=elige no se ve


def test_home_enlaza_demo_interactiva():
    html = (VIZ / "home.html").read_text(encoding="utf-8")
    assert 'href="split.html?demo=elige"' in html and "Demo interactiva: el público elige" in html
    assert 'href="split.html"' in html and 'href="split.html?demo=enjambre"' in html


def test_estilos_de_la_franja():
    css = (VIZ / "style.css").read_text(encoding="utf-8")
    assert ".split-page .chooser" in css
    # Debe ganarle a ".split-page .chooser { display: flex }": sin ?demo=elige la franja no se ve.
    assert ".split-page .chooser[hidden]" in css


def test_encodings_json_forma():
    opts = json.loads((VIZ / "fixtures" / "encodings.json").read_text(encoding="utf-8"))
    assert 1 <= len(opts) <= 3
    assert opts[0] == {"id": "none", "label": "Tal cual", "left": "fixtures/real_left.jsonl",
                       "right": "fixtures/real_right.jsonl", "graph": "fixtures/real_graph.json"}
    for o in opts:
        assert o["id"] in {"none", "base64", "reversed"}
        assert (VIZ / o["left"]).is_file() and (VIZ / o["right"]).is_file()


@pytest.mark.skipif(not shutil.which("node"), reason="node no está instalado")
def test_teclas_en_node():
    script = """
const s = require(%s);
const opts = [{id: "none"}, {id: "reversed"}];
console.log(JSON.stringify({
  one: s.choiceForKey("1", opts), two: s.choiceForKey("2", opts), three: s.choiceForKey("3", opts),
  space: s.choiceForKey(" ", opts), zero: s.choiceForKey("0", opts), id: s.CHOOSER.id,
  h2: s.keysHint(2), h3: s.keysHint(3),
}));
""" % json.dumps(str(VIZ / "split.js"))
    r = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True,
                                  encoding="utf-8", check=True).stdout)
    assert r == {"one": 0, "two": 1, "three": None, "space": None, "zero": None, "id": "elige",
                 "h2": "Teclas 1 y 2 · espacio pausa", "h3": "Teclas 1, 2 y 3 · espacio pausa"}
