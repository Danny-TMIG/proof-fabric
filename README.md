# proof-fabric

proof-fabric is a Python library that attaches an Ed25519-signed certificate to
a file and re-verifies the certificate against the file's SHA-256 hash on every
read. If the file's contents have changed since the certificate was issued, the
read fails with an error rather than returning the file. proof-fabric is the
read-boundary verification layer of the tmig stack.

proof-fabric is a standalone library. The only runtime dependency is the `cryptography` library. No other program in the tmig stack is required to use proof-fabric.

## What problem proof-fabric solves

An artifact and a signed manifest that describes the artifact are two pieces of
state that can drift apart. A build produces a binary and a manifest listing
the binary's hash. A later rebuild patches the binary and does not update the
manifest. A downstream user downloads the manifest, believes it describes the
binary, and installs a binary that does not match the manifest.

The gap between checking a hash once and checking it on every read is where
this class of error occurs. Systems that check once at load time and then trust
the artifact indefinitely do not detect a change that occurs after the initial
check. proof-fabric closes this gap by checking on every read.

## What proof-fabric provides

- **Certificate creation.** Given a file and an Ed25519 private key,
  proof-fabric produces a certificate containing the SHA-256 hash of the file
  and an Ed25519 signature over that hash.
- **Read with verification.** Given a file, a certificate, and the
  corresponding public key, proof-fabric returns the file's contents if and only
  if the signature verifies and the recomputed hash equals the hash in the
  certificate. Otherwise, the read raises an error.
- **No caching.** The hash and signature check runs on every call to the read
  function. No verification result is stored between calls.

## The mathematical model

Let `A` be a file with byte contents. Let `h` be SHA-256. Let `(sk, pk)` be an
Ed25519 key pair.

A certificate for `A` under `(sk, pk)` is a pair:

    c = (h(A), sigma)
    sigma = Ed25519_sign(sk, h(A))

The read operation `read(A, c, pk)` returns `A` if and only if both conditions
hold: the signature `sigma` verifies against `pk` over `h(A)`, and the
recomputed hash of `A` equals the hash stored in `c`. Both conditions are
evaluated on every call.

## Installation

    pip install proof-fabric

Requires Python 3.12 or newer.

## Usage

    from proof_fabric import certify, read

    cert = certify(artifact_bytes, sk=load_key("~/.config/proof-fabric/signing.key"))
    verified = read(artifact_bytes, cert, pk=load_public_key("..."))
    assert verified == artifact_bytes

A command-line sequence:

    $ proof-fabric certify artifact.bin --key ~/.config/proof-fabric/signing.key

    wrote artifact.bin.cert
    hash:      3e8b9a1c7f2e...
    signature: MC4CAQAwBQYDK2VwBCIEIG...

    $ proof-fabric read artifact.bin --cert artifact.bin.cert \
          --pub ~/.config/proof-fabric/signing.pub

    hash matches certificate
    signature verifies
    artifact bytes returned

If the artifact has been modified:

    $ echo tampered > artifact.bin
    $ proof-fabric read artifact.bin --cert artifact.bin.cert \
          --pub ~/.config/proof-fabric/signing.pub

    hash mismatch: certificate says 3e8b9a1c..., artifact is 8f2e7d1a...
    read refused

## What a certificate proves

Given a certificate and a public key, a verifying party can establish that at
the moment of the read, the file's SHA-256 hash equaled the hash recorded in
the certificate and the certificate's signature verified against the public
key.

## What a certificate does not prove

- That the file's contents are correct.
- That the certificate is the most recent certificate for the file. A stale
  but valid certificate passes verification.
- That the signing key was not compromised.
- That the caller is using the certificate the caller intends to use.

## Known limitations

- **No freshness.** A valid but old certificate passes verification. The
  library does not check that the certificate is newer than some threshold.
- **No revocation.** A certificate signed under a key that is later compromised
  remains valid until the corresponding public key is removed from the
  verifier's trust store.
- **Per-read cost.** The file is rehashed on every read. For large files, this
  cost may be significant. The library deliberately does not cache the
  verification result, because caching would reopen the gap that the library
  exists to close.
- **Single-certificate API.** A multi-signer workflow requires composing this
  library with a threshold scheme. The threshold scheme is not provided.
- **Ed25519 only.** The signature scheme is fixed at Ed25519.

## Relationship to the tmig stack

proof-fabric is one of eight independent programs in the tmig stack. Formal
specification: [docs/SPEC.md](docs/SPEC.md). Relationship model:
[docs/STACK.md](docs/STACK.md).

## License

See [LICENSE](LICENSE).
