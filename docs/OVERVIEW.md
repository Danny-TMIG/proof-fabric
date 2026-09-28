# proof-fabric — Re-Verify on Read

## Abstract

proof-fabric attaches a signed certificate to an artifact (a build output,
a data file, a serialized structure) and re-verifies the certificate against
the artifact's actual hash on every read. Certificates are Ed25519-signed;
the hash is recomputed in-process on each access; if the artifact has drifted
since the certificate was issued, the read fails loudly. The unit of
guarantee is *this bytes-then-read are the bytes that were attested*.

## 1. Problem

A stored artifact and its proof of correctness are two pieces of state that
can drift. A build produces a binary and a manifest; the binary is later
recompiled with a patch and the manifest is not; downstream consumers read
the manifest and believe they are installing the original. A data file is
signed and later modified by a process that does not know about the
signature. The general problem: an artifact's proof is only meaningful at the
moment it is checked against the artifact's *current* bytes, not against the
bytes at some earlier moment when the proof was attached. Systems that check
once and then trust indefinitely are the source of a well-known class of
supply-chain compromises.

## 2. Formal model

Let `A` be an artifact (an arbitrary byte string), `h` SHA-256, and `k` an
Ed25519 key pair. A *certificate* for `A` under `k` is

    c = (h(A), σ)  where σ = Ed25519_sign(k.sk, h(A))

The read operation `read(A, c, k.pk)` returns `A` iff
`σ` verifies against `k.pk` over `h(A)` **and** `h(A)` equals the hash in `c`.
Both conditions are evaluated on every read; neither is cached.

## 3. Design decisions

**Re-verify on every read, not on store.** A certificate attached at write
time proves nothing about the artifact's state at read time. Re-verifying on
read is the only construction that closes the window between
attestation and use.

**Hash, not signature over artifact.** The certificate signs the *hash* of
the artifact, not the artifact itself. This makes certificates small and
constant-size regardless of the artifact's size, and permits the artifact to
be transmitted by any channel (including untrusted ones) as long as the
certificate arrives intact.

**Fail-closed on mismatch.** A read that fails verification raises; it does
not return the artifact with a warning. A caller that wants to log-and-
proceed can catch the exception explicitly, but the default is failure.

**No caching of verification results.** A common optimization is to cache
the (path, mtime, verdict) tuple to avoid re-hashing. proof-fabric does not
do this: the entire point is that the artifact's bytes at read time are the
ones attested, and caching re-introduces exactly the window the library
exists to close.

## 4. Threat model

*In scope:* artifact tampering after certificate issuance; certificate
tampering (detected by signature verification); artifact substitution between
two certificates (both verifications must pass for the same hash);
filesystem-level rollback (a reverted file fails verification unless the
rollback also reverts the certificate, in which case a signed certificate
that is genuinely old but hash-matching will still verify — proof-fabric
does not protect against a rollback to a previously-attested state).

*Out of scope:* compromise of the signing key; compromise of SHA-256 or
Ed25519; attacks that keep `h(A)` the same while changing `A` (a collision);
attacks that replace both the artifact and its certificate with an older but
consistently-signed pair (freshness is a separate concern).

## 5. What it proves, and what it doesn't

Proves: at the moment of read, the artifact's SHA-256 equaled the hash
recorded in the certificate, and the certificate verified against the public
key. Together, that the artifact is *some* byte string that was signed by
the holder of the private key under this certificate.

Does not prove: that the artifact is *correct*; that the certificate is the
*most recent* certificate for the artifact (a stale but valid certificate
passes); that the signing key was not compromised; that the caller is using
the certificate they think they are using (unless the caller's own logic
ensures this).

## 6. Related work

- *IETF TUF.* Signed metadata with rollback protection via version numbers;
  proof-fabric's certificate has no version, so rollback protection is
  absent by design and must be provided by the caller.
- *Sigstore Cosign.* Signed container images with transparency-log
  integration; proof-fabric is a library, not a signing service.
- *The Update Framework's hashes.* Hash-per-file in a signed manifest;
  proof-fabric adopts the same idea at the read boundary rather than at the
  update boundary.
- *Content-addressed storage (IPFS, git objects).* Identity is the hash;
  proof-fabric separates the artifact from its certificate so that the
  artifact can move freely while the certificate remains the trust anchor.
- *The "verify-then-use" pattern in security engineering.* proof-fabric is
  an instance of this pattern with a specific choice: verify on *every* use,
  not once at load.

## 7. Known limitations

1. **No freshness.** A valid but old certificate passes verification.
2. **No revocation.** A certificate signed under a compromised key remains
   valid until the key's public half is removed from the verifier's trust
   store.
3. **Per-read cost.** Re-hashing large artifacts on every read can be
   expensive; the library does not offer an incremental-hashing optimization
   because it would reintroduce the cached-verdict window.
4. **Single-certificate API.** Multi-signer certificates require composing
   the library with a threshold scheme elsewhere.
5. **Signature scheme is fixed.** Ed25519 only; a different scheme would
   require a fork.

## 8. Extension points

- **Freshness markers** (monotonic version, timestamp) as optional fields.
- **Threshold certificates** for multi-signer workflows.
- **Streaming verification** for artifacts too large to hash in one pass.
- **Revocation lists** for certificates signed under subsequently-compromised
  keys.
