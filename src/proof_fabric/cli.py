from __future__ import annotations
import argparse
import json
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from proof_fabric.cert import Certificate, Claim
from proof_fabric.verify import sign, verify, VerifyError, MAX_DEPTH_DEFAULT


def cmd_keygen(a):
    priv = Ed25519PrivateKey.generate()
    Path(a.out).write_bytes(priv.private_bytes_raw())
    print(f"key: {a.out}")


def cmd_sign(a):
    priv = Ed25519PrivateKey.from_private_bytes(Path(a.key).read_bytes())
    art = Path(a.artifact).read_bytes()
    claims = [Claim(c["type"], c.get("params", {}))
              for c in json.loads(Path(a.claims).read_text())]
    cert = sign(art, claims, a.issuer, priv)
    Path(a.out).write_text(json.dumps(cert.to_dict(), indent=2))
    print(f"cert: {a.out}")


def cmd_verify(a):
    art = Path(a.artifact).read_bytes()
    cert = Certificate.from_dict(json.loads(Path(a.cert).read_text()))
    allow = set(a.allow.split(",")) if a.allow else None
    certs_dir = Path(a.certs_dir) if a.certs_dir else Path(a.cert).parent
    artifacts_dir = Path(a.artifacts_dir) if a.artifacts_dir else Path(a.artifact).parent
    _ctx = {
        "path": set(),
        "depth": 0,
        "max_depth": a.max_depth,
        "verified": set(),
        "trace": [],
    }
    try:
        with tempfile.TemporaryDirectory() as t:
            verify(art, cert,
                   certs_dir=certs_dir,
                   artifacts_dir=artifacts_dir,
                   tmp_dir=Path(t),
                   allowlist=allow,
                   max_depth=a.max_depth,
                   _ctx=_ctx)
    except VerifyError as e:
        print(f"FAIL: {e}")
        return 1
    print("OK")
    if a.trace:
        for row in _ctx["trace"]:
            indent = "  " * row["depth"]
            print(f"{indent}· d={row['depth']} {row['artifact_sha256']} "
                  f"claims={row['claims']} issuer={row['issuer']}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pcf")
    sub = ap.add_subparsers(dest="cmd", required=True)

    k = sub.add_parser("keygen")
    k.add_argument("out")
    k.set_defaults(func=cmd_keygen)

    s = sub.add_parser("sign")
    s.add_argument("--key", required=True)
    s.add_argument("--artifact", required=True)
    s.add_argument("--claims", required=True)
    s.add_argument("--issuer", required=True)
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_sign)

    v = sub.add_parser("verify")
    v.add_argument("--artifact", required=True)
    v.add_argument("--cert", required=True)
    v.add_argument("--allow", default="")
    v.add_argument("--certs-dir", default="")
    v.add_argument("--artifacts-dir", default="")
    v.add_argument("--max-depth", type=int, default=MAX_DEPTH_DEFAULT)
    v.add_argument("--trace", action="store_true")
    v.set_defaults(func=cmd_verify)

    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
