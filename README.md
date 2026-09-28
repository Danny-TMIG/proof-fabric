# proof-fabric

**Re-verify on read. The bytes you got are the bytes that were attested.**

proof-fabric attaches a signed certificate to an artifact and re-verifies the
certificate against the artifact actual hash on every read. If the artifact
has drifted since certificate issuance, the read fails loudly.

## The problem

You build a binary, produce a manifest listing its hash, publish both. A week
later someone recompiles with a patch and forgets to update the manifest.
Downstream users download the manifest, believe it describes the binary, and
install something else.

proof-fabric closes this by making the certificate check part of every read.

## What it does

For artifact A, SHA-256 h, Ed25519 keypair k:

    c = (h(A), sigma)   where sigma = Ed25519_sign(k.sk, h(A))

`read(A, c, k.pk)` returns A iff sigma verifies AND h(A) equals the hash in c.
Both conditions on every read. Neither cached.

## Install

    pip install proof-fabric

## Usage

    from proof_fabric import certify, read

    cert = certify(artifact_bytes, sk=load_key("~/.config/proof-fabric/signing.key"))
    verified = read(artifact_bytes, cert, pk=load_public_key("..."))
    assert verified == artifact_bytes

Terminal:

    $ proof-fabric certify artifact.bin --key ~/.config/proof-fabric/signing.key
    wrote artifact.bin.cert
    hash:      3e8b9a1c7f2e...
    signature: MC4CAQAwBQYDK2VwBCIEIG...

    $ proof-fabric read artifact.bin --cert artifact.bin.cert --pub ~/.config/proof-fabric/signing.pub
    ✓ hash matches certificate
    ✓ signature verifies
    artifact bytes returned

    $ echo tampered > artifact.bin
    $ proof-fabric read artifact.bin --cert artifact.bin.cert --pub ~/.config/proof-fabric/signing.pub
    ✗ hash mismatch: certificate says 3e8b9a1c..., artifact is 8f2e7d1a...
    read refused

## Known limitations

- No freshness.
- No revocation.
- Per-read cost.
- Single-certificate API.
- Ed25519 only.

## Where this fits

proof-fabric is the read-boundary verification layer. Full model in
[docs/STACK.md](docs/STACK.md).

## License

See LICENSE.
