"""Sesiones benignas propias (5c)."""

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from eval.replay.core import load_session  # noqa: E402
from proxy.benign import KINDS, generate, plan_kinds  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((ROOT / "demo" / "secrets_manifest.json").read_text(encoding="utf-8"))
DATA = ROOT / "data" / "benign" / "sessions"


@pytest.fixture(scope="module")
def twelve(tmp_path_factory):
    out = tmp_path_factory.mktemp("benign")
    return generate(12, seed=1, out_dir=str(out)), out


def test_generate_twelve(twelve):
    paths, out = twelve
    assert len(paths) == 12 and len(list(out.glob("*.jsonl"))) == 12
    for i, p in enumerate(paths):
        assert p.name == f"benign-1-{i:04d}.jsonl"
        s = load_session(p)
        assert 25 <= len(s) <= 60
        assert [c.t for c in s] == list(range(1, len(s) + 1))
        assert all(c.label == "benign" for c in s)
        assert all(c.output is not None for c in s)  # allow_all: todas se ejecutan
        assert {c.session_id for c in s} == {p.stem}


def test_deterministic(twelve, tmp_path):
    paths, _ = twelve
    again = generate(12, seed=1, out_dir=str(tmp_path))
    for a, b in zip(paths, again):
        assert a.read_bytes() == b.read_bytes()
    # volver a generar en la misma carpeta reemplaza, no agrega
    generate(12, seed=1, out_dir=str(tmp_path))
    assert again[0].read_bytes() == paths[0].read_bytes()


def test_six_kinds_in_forty():
    kinds = plan_kinds(40, seed=0)
    assert len(kinds) == 40 and set(kinds) == set(KINDS)
    assert sum(k in ("bugfix", "docs", "config") for k in kinds) == 24
    assert kinds.count("debug_env") == 8 and kinds.count("deploy") == 4 and kinds.count("hashes") == 4


def test_kinds_show_up_in_content(tmp_path):
    paths = generate(10, seed=3, out_dir=str(tmp_path))
    calls = [c for p in paths for c in load_session(p)]
    reads = {c.args.get("path") for c in calls if c.tool == "read_file"}
    assert ".env" in reads and "config/settings.yaml" in reads and "README.md" in reads
    api = [c for c in calls if c.tool == "http_request"]
    assert any("Authorization" in (c.args.get("headers") or {}) for c in api)
    assert any("commit=" in c.args["url"] or "request_id=" in c.args["url"] for c in api)
    assert all(c.output.startswith("200") for c in api if "Authorization" in (c.args.get("headers") or {}))
    gits = [c for c in calls if c.tool == "git"]
    assert gits and all(c.output.startswith("exit ") for c in gits)
    assert any(c.output.startswith("exit 0") and "commit " in c.output for c in gits)


def _no_secret_leaves(paths):
    secrets = {s["secret_id"]: (s["value"], {h.lower() for h in s["allowed_hosts"]}) for s in MANIFEST["secrets"]}
    for p in paths:
        for c in load_session(p):
            if not c.is_sink:
                continue
            blob = json.dumps(c.args, sort_keys=True)
            for sid, (value, allowed) in secrets.items():
                if any(r in allowed for r in c.resources):
                    continue
                for i in range(len(value) - 7):
                    assert value[i:i + 8] not in blob, (p.name, c.id, sid)


def test_no_secret_to_disallowed_host(twelve):
    _no_secret_leaves(twelve[0])


def test_versioned_dataset():
    paths = sorted(DATA.glob("benign-0-*.jsonl"))
    assert len(paths) == 120
    total = sum(len(load_session(p)) for p in paths)
    assert total >= 3000
    _no_secret_leaves(paths)
    readme = (DATA.parent / "README.md").read_text(encoding="utf-8")
    assert "--n 120 --seed 0" in readme and str(total) in readme
