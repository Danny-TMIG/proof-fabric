"""Certificate format. Small enough to audit in one sitting."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import json

VERSION = 1

CLAIM_TYPES = frozenset({
    "hash",        # artifact's sha256 == params.sha256
    "contains",    # tar archive contains params.paths
    "runs",        # artifact is executable, runs with args, exits 0
    "tests-pass",  # tar archive, extract, run params.cmd, exit 0
    "references",  # another cert with sha256 == params.cert_sha256 exists
})


@dataclass(frozen=True)
class Claim:
    type: str
    params: dict[str, Any]

    def __post_init__(self) -> None:
        if self.type not in CLAIM_TYPES:
            raise ValueError(f"unknown claim type: {self.type!r}")


@dataclass
class Certificate:
    version: int
    artifact_sha256: str
    claims: list[Claim]
    issuer: str
    pubkey_hex: str
    signature_hex: str

    def _body(self) -> dict:
        return {
            "version": self.version,
            "artifact_sha256": self.artifact_sha256,
            "claims": [{"type": c.type, "params": c.params} for c in self.claims],
            "issuer": self.issuer,
            "pubkey_hex": self.pubkey_hex,
        }

    def to_dict(self) -> dict:
        d = self._body()
        d["signature_hex"] = self.signature_hex
        return d

    def signing_payload(self) -> bytes:
        return json.dumps(self._body(), sort_keys=True,
                          separators=(",", ":")).encode()

    @classmethod
    def from_dict(cls, d: dict) -> "Certificate":
        return cls(
            version=d["version"],
            artifact_sha256=d["artifact_sha256"],
            claims=[Claim(c["type"], c["params"]) for c in d["claims"]],
            issuer=d["issuer"],
            pubkey_hex=d["pubkey_hex"],
            signature_hex=d["signature_hex"],
        )
