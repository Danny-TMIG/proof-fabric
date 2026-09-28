import io, json, tarfile, tempfile
from pathlib import Path
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from proof_fabric import Claim, Fabric, sign, verify, VerifyError
from proof_fabric.cert import Certificate


def _key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def _tar(paths: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for name, data in paths.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def test_hash_roundtrip():
    priv = _key()
    art = b"hello"
    import hashlib
    claims = [Claim("hash", {"sha256": hashlib.sha256(art).hexdigest()})]
    cert = sign(art, claims, "test", priv)
    with tempfile.TemporaryDirectory() as t:
        verify(art, cert, certs_dir=Path(t), tmp_dir=Path(t))


def test_hash_detects_tamper():
    priv = _key()
    art = b"hello"
    import hashlib
    claims = [Claim("hash", {"sha256": hashlib.sha256(art).hexdigest()})]
    cert = sign(art, claims, "test", priv)
    with tempfile.TemporaryDirectory() as t:
        with pytest.raises(VerifyError, match="hash mismatch|hash:"):
            verify(b"goodbye", cert, certs_dir=Path(t), tmp_dir=Path(t))


def test_wrong_key_rejected():
    priv = _key()
    other = _key()
    art = b"x"
    import hashlib
    cert = sign(art, [Claim("hash", {"sha256": hashlib.sha256(art).hexdigest()})],
                "test", priv)
    # forge with a different key
    cert.signature_hex = other.sign(cert.signing_payload()).hex()
    cert.pubkey_hex = other.public_key().public_bytes_raw().hex()
    # now signature is valid but issuer changed; if allowlist is strict, reject
    with tempfile.TemporaryDirectory() as t:
        with pytest.raises(VerifyError, match="issuer"):
            verify(art, cert, certs_dir=Path(t), tmp_dir=Path(t),
                   allowlist={"real-issuer"})


def test_contains_claim():
    priv = _key()
    art = _tar({"README.md": b"hi", "src/main.py": b"print(1)"})
    import hashlib
    claims = [
        Claim("hash", {"sha256": hashlib.sha256(art).hexdigest()}),
        Claim("contains", {"paths": ["README.md", "src/main.py"]}),
    ]
    cert = sign(art, claims, "test", priv)
    with tempfile.TemporaryDirectory() as t:
        verify(art, cert, certs_dir=Path(t), tmp_dir=Path(t))


def test_fabric_serves_when_valid():
    priv = _key()
    art = b"payload"
    import hashlib
    cert = sign(art, [Claim("hash", {"sha256": hashlib.sha256(art).hexdigest()})],
                "test", priv)
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        (d / "a.bin").write_bytes(art)
        (d / "a.bin.cert.json").write_text(json.dumps(cert.to_dict()))
        f = Fabric(d, d)
        ok, data = f.read("a.bin")
        assert ok and data == art


def test_fabric_quarantines_after_tamper():
    priv = _key()
    art = b"payload"
    import hashlib
    cert = sign(art, [Claim("hash", {"sha256": hashlib.sha256(art).hexdigest()})],
                "test", priv)
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        (d / "a.bin").write_bytes(art)
        (d / "a.bin.cert.json").write_text(json.dumps(cert.to_dict()))
        f = Fabric(d, d)
        # read once — valid
        assert f.read("a.bin")[0]
        # tamper with the artifact on disk
        (d / "a.bin").write_bytes(b"EVIL")
        # read again — the fabric re-verifies and refuses
        ok, reason = f.read("a.bin")
        assert not ok
        assert "hash mismatch" in reason or "hash:" in reason


def test_references_chain():
    priv = _key()
    import hashlib
    parent_art = b"parent"
    parent_cert = sign(parent_art, [], "test", priv)
    parent_bytes = json.dumps(parent_cert.to_dict()).encode()
    parent_sha = hashlib.sha256(parent_bytes).hexdigest()

    child_art = b"child"
    child_cert = sign(child_art, [
        Claim("hash", {"sha256": hashlib.sha256(child_art).hexdigest()}),
        Claim("references", {"cert_sha256": parent_sha}),
    ], "test", priv)

    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        (d / "parent.cert.json").write_bytes(parent_bytes)
        verify(child_art, child_cert, certs_dir=d, tmp_dir=d)
