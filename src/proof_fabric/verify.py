"""Sign + verify. Verify re-checks claims against current bytes.

Recursive references: a `references` claim that names an artifact
transitively verifies the referenced certificate. Cycle detection via
path-tracking. Per-read cache avoids re-verifying a cert twice in one
call. Depth limit refuses runaway chains.
"""
from __future__ import annotations
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path
from typing import Any, Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from proof_fabric.cert import Certificate, Claim, VERSION

MAX_DEPTH_DEFAULT = 16


class VerifyError(Exception):
    pass


# ── primitive verifiers ──────────────────────────────────────────────
def _v_hash(claim: Claim, art: bytes, ctx: dict) -> None:
    want = claim.params["sha256"]
    got = hashlib.sha256(art).hexdigest()
    if got != want:
        raise VerifyError(f"hash mismatch: cert={want[:12]}… artifact={got[:12]}…")


def _v_contains(claim: Claim, art: bytes, ctx: dict) -> None:
    want = claim.params["paths"]
    try:
        tf = tarfile.open(fileobj=io.BytesIO(art), mode="r:*")
    except tarfile.TarError:
        raise VerifyError("contains: not a tar archive")
    names = {m.name for m in tf.getmembers()}
    missing = [p for p in want if p not in names]
    if missing:
        raise VerifyError(f"contains: missing {missing[:3]}")


def _v_runs(claim: Claim, art: bytes, ctx: dict) -> None:
    args = claim.params.get("args", [])
    tmp = ctx["tmp"]; tmp.mkdir(parents=True, exist_ok=True)
    exe = tmp / "artifact.bin"
    exe.write_bytes(art)
    exe.chmod(0o755)
    r = subprocess.run([str(exe), *args], capture_output=True, timeout=30)
    if r.returncode != 0:
        raise VerifyError(f"runs: exit {r.returncode}")


def _v_tests_pass(claim: Claim, art: bytes, ctx: dict) -> None:
    try:
        tf = tarfile.open(fileobj=io.BytesIO(art), mode="r:*")
    except tarfile.TarError:
        raise VerifyError("tests-pass: not a tar archive")
    tmp = ctx["tmp"] / "t"; tmp.mkdir(parents=True, exist_ok=True)
    tf.extractall(tmp, filter="data")
    cmd = claim.params["cmd"]
    r = subprocess.run(cmd, cwd=tmp, capture_output=True, timeout=120)
    if r.returncode != 0:
        tail = (r.stdout + r.stderr).decode(errors="replace").splitlines()[-1:]
        raise VerifyError(f"tests-pass: exit {r.returncode} {tail}")


def _v_references(claim: Claim, art: bytes, ctx: dict) -> None:
    """Shallow check + optional recursive verification."""
    want_sha = claim.params["cert_sha256"]
    certs_dir: Path = ctx["certs_dir"]
    artifacts_dir: Path | None = ctx["artifacts_dir"]
    _ctx: dict = ctx["_ctx"]

    cert_path: Path | None = None
    for f in certs_dir.glob("*.cert.json"):
        if hashlib.sha256(f.read_bytes()).hexdigest() == want_sha:
            cert_path = f
            break
    if cert_path is None:
        raise VerifyError(f"references: cert {want_sha[:12]}… not found")

    # shallow mode
    if artifacts_dir is None:
        return

    # resolve parent artifact name
    name = claim.params.get("artifact")
    if name is None:
        # convention: foo.cert.json <-> foo
        name = cert_path.name[: -len(".cert.json")]
    parent_path = artifacts_dir / name
    if not parent_path.exists():
        raise VerifyError(f"references: parent artifact {name!r} not found")

    parent_cert = Certificate.from_dict(json.loads(cert_path.read_text()))
    parent_key = parent_cert.artifact_sha256

    if parent_key in _ctx["path"]:
        raise VerifyError(f"references: cycle at {parent_key[:12]}…")
    if parent_key in _ctx["verified"]:
        return

    if _ctx["depth"] + 1 > _ctx["max_depth"]:
        raise VerifyError(
            f"references: depth limit {_ctx['max_depth']} exceeded "
            f"at {parent_key[:12]}…"
        )

    _ctx["path"].add(parent_key)
    _ctx["depth"] += 1
    try:
        verify(
            parent_path.read_bytes(),
            parent_cert,
            certs_dir=certs_dir,
            tmp_dir=ctx["tmp"],
            allowlist=ctx["allowlist"],
            artifacts_dir=artifacts_dir,
            _ctx=_ctx,
        )
        _ctx["verified"].add(parent_key)
    finally:
        _ctx["depth"] -= 1
        _ctx["path"].discard(parent_key)


VERIFIERS: dict[str, Callable] = {
    "hash": _v_hash,
    "contains": _v_contains,
    "runs": _v_runs,
    "tests-pass": _v_tests_pass,
    "references": _v_references,
}


# ── public API ───────────────────────────────────────────────────────
def sign(artifact: bytes, claims: list[Claim], issuer: str,
         priv: Ed25519PrivateKey) -> Certificate:
    cert = Certificate(
        version=VERSION,
        artifact_sha256=hashlib.sha256(artifact).hexdigest(),
        claims=claims,
        issuer=issuer,
        pubkey_hex=priv.public_key().public_bytes_raw().hex(),
        signature_hex="",
    )
    cert.signature_hex = priv.sign(cert.signing_payload()).hex()
    return cert


def verify(
    artifact: bytes,
    cert: Certificate,
    *,
    certs_dir: Path,
    tmp_dir: Path,
    allowlist: set[str] | None = None,
    artifacts_dir: Path | None = None,
    max_depth: int = MAX_DEPTH_DEFAULT,
    _ctx: dict | None = None,
) -> None:
    """Raise VerifyError if anything fails.

    If artifacts_dir is given and a `references` claim names an artifact,
    that cert is recursively verified. Cycle detection and depth limiting
    apply to the recursion.
    """
    if _ctx is None:
        _ctx = {
            "path": set(),
            "depth": 0,
            "max_depth": max_depth,
            "verified": set(),
            "trace": [],
        }

    key = (cert.artifact_sha256, cert.signature_hex)
    if key in _ctx["verified"]:
        return

    if cert.version != VERSION:
        raise VerifyError(f"unsupported version {cert.version}")

    if allowlist is not None and cert.issuer not in allowlist:
        raise VerifyError(f"issuer {cert.issuer!r} not allowed")

    pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(cert.pubkey_hex))
    try:
        pub.verify(bytes.fromhex(cert.signature_hex), cert.signing_payload())
    except Exception:
        raise VerifyError("signature invalid")

    actual = hashlib.sha256(artifact).hexdigest()
    if actual != cert.artifact_sha256:
        raise VerifyError(
            f"hash mismatch: cert={cert.artifact_sha256[:12]}… "
            f"artifact={actual[:12]}…"
        )

    _ctx["trace"].append({
        "depth": _ctx["depth"],
        "issuer": cert.issuer,
        "artifact_sha256": cert.artifact_sha256[:12],
        "claims": len(cert.claims),
    })

    _ctx["path"].add(cert.artifact_sha256)
    try:
        ctx = {
            "tmp": tmp_dir,
            "certs_dir": certs_dir,
            "artifacts_dir": artifacts_dir,
            "allowlist": allowlist,
            "_ctx": _ctx,
        }
        for c in cert.claims:
            VERIFIERS[c.type](c, artifact, ctx)
        _ctx["verified"].add(key)
    finally:
        _ctx["path"].discard(cert.artifact_sha256)
