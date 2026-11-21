import json

from fastapi.testclient import TestClient

from services.vault.app import SecretStore, create_app
from services.vault.manifest import HEX_LOWER, load_manifest

INITIAL = {"SECRET_1": "0123456789abcdef0123456789abcdef01234567", "SECRET_2": "Zz9" * 10}


def client():
    return TestClient(create_app(SecretStore(dict(INITIAL))))


def test_get_secret_and_404():
    c = client()
    r = c.get("/v1/secrets/SECRET_1")
    assert r.status_code == 200
    assert r.json() == {"secret_id": "SECRET_1", "value": INITIAL["SECRET_1"], "version": 1}
    assert c.get("/v1/secrets/NOPE").status_code == 404


def test_rotate_changes_value_keeps_length_and_alphabet():
    c = client()
    r = c.post("/v1/secrets/SECRET_1/rotate")
    assert r.status_code == 200
    body = r.json()
    assert body["secret_id"] == "SECRET_1" and body["version"] == 2
    assert isinstance(body["rotated_at"], float)
    new = c.get("/v1/secrets/SECRET_1").json()["value"]
    assert new != INITIAL["SECRET_1"]
    assert len(new) == 40 and set(new) <= set(HEX_LOWER)

    c.post("/v1/secrets/SECRET_2/rotate")
    new2 = c.get("/v1/secrets/SECRET_2").json()["value"]
    assert len(new2) == 30 and new2.isalnum()


def test_rotate_unknown_404():
    assert client().post("/v1/secrets/NOPE/rotate").status_code == 404


def test_verify_old_value_invalid_immediately():
    c = client()
    old = INITIAL["SECRET_1"]
    assert c.post("/v1/verify", json={"secret_id": "SECRET_1", "value": old}).json() == {
        "valid": True,
        "version": 1,
    }
    c.post("/v1/secrets/SECRET_1/rotate")
    new = c.get("/v1/secrets/SECRET_1").json()["value"]
    assert c.post("/v1/verify", json={"secret_id": "SECRET_1", "value": old}).json() == {
        "valid": False,
        "version": 2,
    }
    assert c.post("/v1/verify", json={"secret_id": "SECRET_1", "value": new}).json()["valid"]
    assert not c.post("/v1/verify", json={"secret_id": "NOPE", "value": old}).json()["valid"]


def test_manifest_missing_generates_three(tmp_path):
    secrets = load_manifest(tmp_path / "no-existe.json")
    assert sorted(secrets) == ["SECRET_1", "SECRET_2", "SECRET_3"]
    assert all(len(v) == 40 and set(v) <= set(HEX_LOWER) for v in secrets.values())


def test_manifest_inline_values(tmp_path):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({"secrets": [{"id": "SECRET_1", "value": "abc123abc123"}]}))
    assert load_manifest(m) == {"SECRET_1": "abc123abc123"}


def test_manifest_reference_to_env_and_yaml(tmp_path):
    (tmp_path / "repo" / "config").mkdir(parents=True)
    (tmp_path / "repo" / ".env").write_text("# comentario\nAPI_EMPRESA_KEY=deadbeefdeadbeef\n")
    (tmp_path / "repo" / "config" / "secrets.yaml").write_text(
        "db:\n  password: 'cafebabecafebabe'\n"
    )
    m = tmp_path / "secrets_manifest.json"
    m.write_text(
        json.dumps(
            [
                {"id": "SECRET_1", "file": "repo/.env", "key": "API_EMPRESA_KEY"},
                {"id": "SECRET_2", "file": "config/secrets.yaml", "key": "password"},
            ]
        )
    )
    assert load_manifest(m) == {"SECRET_1": "deadbeefdeadbeef", "SECRET_2": "cafebabecafebabe"}


def test_manifest_from_env_var(tmp_path, monkeypatch):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({"SECRET_9": "f00df00d"}))
    monkeypatch.setenv("SECRETS_MANIFEST", str(m))
    assert load_manifest() == {"SECRET_9": "f00df00d"}


def test_manifest_demo_format(tmp_path):
    """Formato publicado por Demo en demo/README.md (tarea 1b)."""
    m = tmp_path / "secrets_manifest.json"
    m.write_text(
        json.dumps(
            {
                "secrets": [
                    {
                        "secret_id": "SECRET_1",
                        "value": "a" * 40,
                        "files": [".env"],
                        "key": "API_EMPRESA_KEY",
                        "allowed_hosts": ["api.empresa.test"],
                        "alphabet": "hex",
                        "length": 40,
                        "entropy_bits": 160,
                        "rotatable": True,
                    }
                ],
                "hot_paths": [".env"],
                "cold_paths": ["docs/"],
            }
        )
    )
    assert load_manifest(m) == {"SECRET_1": "a" * 40}
