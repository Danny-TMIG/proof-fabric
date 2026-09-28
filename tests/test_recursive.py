"""Tests for recursive references, cycle detection, depth limiting, caching."""
import hashlib
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from proof_fabric import Claim, sign, verify, VerifyError
import importlib as _il
verify_mod = _il.import_module('proof_fabric.verify')


def _key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def _cert_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_chain(art_dir: Path, certs_dir: Path, n: int, priv,
                 prefix: str = "c"):
    """Build a chain c0 <- c1 <- ... <- c{n-1}. Returns (top_art, top_cert, top_name)."""
    prev_cert_sha = None
    prev_name = None
    for i in range(n):
        name = f"{prefix}{i}.bin"
        content = f"level {i}".encode()
        claims = [Claim("hash",
                        {"sha256": hashlib.sha256(content).hexdigest()})]
        if prev_cert_sha is not None:
            claims.append(Claim("references",
                                {"cert_sha256": prev_cert_sha,
                                 "artifact": prev_name}))
        cert = sign(content, claims, "test", priv)
        (art_dir / name).write_bytes(content)
        cert_path = certs_dir / f"{name}.cert.json"
        cert_path.write_text(json.dumps(cert.to_dict()))
        prev_cert_sha = _cert_sha(cert_path)
        prev_name = name
    return content, cert, name


def test_chain_of_three_passes(tmp_path):
    art = tmp_path / "a"; art.mkdir()
    crt = tmp_path / "c"; crt.mkdir()
    tmp = tmp_path / "t"; tmp.mkdir()
    priv = _key()
    top_art, top_cert, _ = _build_chain(art, crt, 3, priv)
    verify(top_art, top_cert, certs_dir=crt, artifacts_dir=art, tmp_dir=tmp)


def test_chain_reports_trace(tmp_path):
    art = tmp_path / "a"; art.mkdir()
    crt = tmp_path / "c"; crt.mkdir()
    tmp = tmp_path / "t"; tmp.mkdir()
    priv = _key()
    top_art, top_cert, _ = _build_chain(art, crt, 3, priv)
    ctx = {"path": set(), "depth": 0, "max_depth": 16,
           "verified": set(), "trace": []}
    verify(top_art, top_cert, certs_dir=crt, artifacts_dir=art,
           tmp_dir=tmp, _ctx=ctx)
    depths = [r["depth"] for r in ctx["trace"]]
    assert depths == [0, 1, 2]


def test_chain_detects_tampered_root(tmp_path):
    art = tmp_path / "a"; art.mkdir()
    crt = tmp_path / "c"; crt.mkdir()
    tmp = tmp_path / "t"; tmp.mkdir()
    priv = _key()
    top_art, top_cert, _ = _build_chain(art, crt, 3, priv)
    # tamper with the leaf-most artifact
    (art / "c0.bin").write_bytes(b"EVIL")
    with pytest.raises(VerifyError, match="hash mismatch|hash:"):
        verify(top_art, top_cert, certs_dir=crt, artifacts_dir=art, tmp_dir=tmp)


def test_depth_limit(tmp_path):
    art = tmp_path / "a"; art.mkdir()
    crt = tmp_path / "c"; crt.mkdir()
    tmp = tmp_path / "t"; tmp.mkdir()
    priv = _key()
    top_art, top_cert, _ = _build_chain(art, crt, 20, priv)
    with pytest.raises(VerifyError, match="depth limit"):
        verify(top_art, top_cert, certs_dir=crt, artifacts_dir=art,
               tmp_dir=tmp, max_depth=5)


def test_cache_avoids_rework(tmp_path, monkeypatch):
    """Diamond: leaf references A and B, both A and B reference root.
    Root's hash claim must be verified only once."""
    art = tmp_path / "a"; art.mkdir()
    crt = tmp_path / "c"; crt.mkdir()
    tmp = tmp_path / "t"; tmp.mkdir()
    priv = _key()

    def mk(name, content, claims):
        cert = sign(content, claims, "test", priv)
        (art / f"{name}.bin").write_bytes(content)
        cp = crt / f"{name}.bin.cert.json"
        cp.write_text(json.dumps(cert.to_dict()))
        return cert, _cert_sha(cp)

    # root
    root_content = b"root"
    _, root_sha = mk("root", root_content, [
        Claim("hash", {"sha256": hashlib.sha256(root_content).hexdigest()}),
    ])

    # A and B both reference root
    for name in ("A", "B"):
        content = f"{name} content".encode()
        mk(name, content, [
            Claim("hash", {"sha256": hashlib.sha256(content).hexdigest()}),
            Claim("references", {"cert_sha256": root_sha, "artifact": "root.bin"}),
        ])

    # leaf references both A and B
    a_sha = _cert_sha(crt / "A.bin.cert.json")
    b_sha = _cert_sha(crt / "B.bin.cert.json")
    leaf_content = b"leaf"
    leaf_cert = sign(leaf_content, [
        Claim("hash", {"sha256": hashlib.sha256(leaf_content).hexdigest()}),
        Claim("references", {"cert_sha256": a_sha, "artifact": "A.bin"}),
        Claim("references", {"cert_sha256": b_sha, "artifact": "B.bin"}),
    ], "test", priv)

    # spy on hash verifications for the root's sha
    root_sha_hex = hashlib.sha256(root_content).hexdigest()
    root_checks = {"n": 0}
    orig_hash = verify_mod.VERIFIERS["hash"]

    def spy(claim, art_bytes, ctx):
        if claim.params.get("sha256") == root_sha_hex:
            root_checks["n"] += 1
        return orig_hash(claim, art_bytes, ctx)

    monkeypatch.setitem(verify_mod.VERIFIERS, "hash", spy)

    verify(leaf_content, leaf_cert, certs_dir=crt, artifacts_dir=art, tmp_dir=tmp)
    # root's hash claim should be verified exactly once, not twice
    assert root_checks["n"] == 1, f"root verified {root_checks['n']} times"


def test_missing_parent_refused(tmp_path):
    art = tmp_path / "a"; art.mkdir()
    crt = tmp_path / "c"; crt.mkdir()
    tmp = tmp_path / "t"; tmp.mkdir()
    priv = _key()

    # child references a cert that doesn't exist
    content = b"x"
    cert = sign(content, [
        Claim("hash", {"sha256": hashlib.sha256(content).hexdigest()}),
        Claim("references", {"cert_sha256": "00" * 32, "artifact": "ghost.bin"}),
    ], "test", priv)
    with pytest.raises(VerifyError, match="not found"):
        verify(content, cert, certs_dir=crt, artifacts_dir=art, tmp_dir=tmp)


def test_shallow_mode_without_artifacts_dir(tmp_path):
    """When artifacts_dir is None, references is a shallow existence check."""
    art = tmp_path / "a"; art.mkdir()
    crt = tmp_path / "c"; crt.mkdir()
    tmp = tmp_path / "t"; tmp.mkdir()
    priv = _key()

    content = b"parent"
    parent_cert = sign(content, [
        Claim("hash", {"sha256": hashlib.sha256(content).hexdigest()}),
    ], "test", priv)
    cp = crt / "parent.bin.cert.json"
    cp.write_text(json.dumps(parent_cert.to_dict()))
    parent_sha = _cert_sha(cp)

    child = b"child"
    child_cert = sign(child, [
        Claim("hash", {"sha256": hashlib.sha256(child).hexdigest()}),
        Claim("references", {"cert_sha256": parent_sha}),
    ], "test", priv)
    verify(child, child_cert, certs_dir=crt, tmp_dir=tmp)
