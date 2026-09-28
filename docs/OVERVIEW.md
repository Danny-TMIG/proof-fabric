# proof-fabric — Re-Verify on Read

## Abstract

Re-verifies signed certificate against recomputed hash on every read.

## 1. Problem

A stored artifact and its proof can drift.

## 2. Formal model

For A, h = SHA-256, k Ed25519 keypair: c = (h(A), sigma) where sigma = Ed25519_sign(k.sk, h(A)). read(A, c, k.pk) returns A iff sigma verifies and h(A) equals hash in c.

## 3. Design decisions

Re-verify every read. Hash, not artifact. Fail-closed on mismatch. No caching.

## 4. Threat model

In scope: artifact tampering, certificate tampering, artifact substitution. Out of scope: signing key compromise, cryptanalysis, freshness.

## 5. What it proves, and what it does not

Proves: At read time, artifact SHA-256 equaled certificate hash and certificate verified.

Does not prove: Artifact correct; certificate is most recent; signing key uncompromised.

## 6. Related work

IETF TUF; Sigstore Cosign; Update Framework hashes; content-addressed storage; verify-then-use pattern.

## 7. Known limitations

- No freshness.
- No revocation.
- Per-read cost.
- Single-certificate API.
- Ed25519 only.

## 8. Extension points

1. Freshness markers.
2. Threshold certificates.
3. Streaming verification.
4. Revocation lists.
