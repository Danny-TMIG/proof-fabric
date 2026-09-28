# Specification: proof-fabric

**Spec version:** 1.0
**Status:** Active
**Series:** tmig-stack/SPEC/proof-fabric
**Last updated:** 2026-09-28

## 1. Identification

| Field | Value |
|---|---|
| Project | proof-fabric |
| Repository | Danny-TMIG/proof-fabric |
| Language | Python 3.12+ |
| Maintainer | Danny-TMIG |

## 2. Abstract

Re-verifies signed certificate against recomputed hash on every read.

## 3. Scope

In scope: the functional surface described in section 5.

Out of scope: Artifact correct; certificate is most recent; signing key uncompromised.

## 4. Conformance

RFC 6962 §2.1; RFC 8032; FIPS 180-4 where applicable.

## 5. Conceptual model

For A, h = SHA-256, k Ed25519 keypair: c = (h(A), sigma) where sigma = Ed25519_sign(k.sk, h(A)). read(A, c, k.pk) returns A iff sigma verifies and h(A) equals hash in c.

## 6. Interfaces

Public Python API and CLI as documented in README.md.

## 7. Functional requirements

Derived from the model above. Each requirement's verification is the
observable behaviour under test in the repo test suite.

## 8. Non-functional requirements

Determinism; purity where applicable; dependency minimality.

## 9. Invariants

As listed in OVERVIEW.md §5.

## 10. Dependencies

See pyproject.toml.

## 11. Limitations and non-goals

- No freshness.
- No revocation.
- Per-read cost.
- Single-certificate API.
- Ed25519 only.

## 12. Versioning and compatibility

Semantic versioning. Public API stable within a major version.

## 13. Cross-references

- Stack index: tmig/docs/SPEC-STACK.md
- Relationship: docs/STACK.md
- Deep overview: docs/OVERVIEW.md
