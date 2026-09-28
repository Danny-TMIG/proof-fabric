# How this repository relates to The Mark Intelligence Group's stack

proof-fabric is the read-boundary verification layer. It attaches an Ed25519-signed certificate to a file and re-verifies the certificate against the file's SHA-256 hash on every read, so that a file whose contents have changed since the certificate was issued fails the read rather than being returned. It shares the Merkle and Ed25519 primitives with state-substrate, mlx-omni, and tmig. The rest of this document describes the stack that proof-fabric closes at the read boundary.

## The eight claims

Each program in the stack produces one kind of verifiable claim:

| program | claim |
|---|---|
| tstate | which states a system can reach |
| state-substrate | a cryptographic attestation of a set of files |
| mlx-omni | primitives for peers that exchange state without a coordinator |
| aesn | a signed record of which commands ran |
| twin-fabric | a verdict on whether a model matches observed behavior |
| unified-security-ops | a signed record of security dispatches |
| proof-fabric | verification at the read boundary |
| tmig | one signed manifest over the whole set |

## The conceptual order

Read top-to-bottom as "each claim is about the one below", not as a call
path:

    tstate                  what states are reachable
    state-substrate         cryptographic attestation of a state
    mlx-omni                many peers each holding such states
    aesn                    actions taken against such states
    twin-fabric             model vs. observed transitions
    unified-security-ops    operational tools acting on the real system
    proof-fabric            verification at the read boundary
    tmig                    the verifier that witnesses the set

There is no function call from twin-fabric down to tstate, and no message
from proof-fabric to state-substrate. The relationship is conceptual.

## Why the stack is divided this way

Each program is one noun. tstate is reachability. proof-fabric is
re-verify-on-read. The split follows a design rule: if a program cannot be
described in one sentence without "and", it should be two programs.

Four structural properties depend on the split:

- Blast radius. A broken configuration in one program cannot break
  another's build.
- Attribution granularity. The manifest carries one cryptographic root per
  program. A change anywhere is localized to that program's root.
- Test isolation. Each program runs its tests in its own environment.
- Selective adoption. A user who wants reachability analysis can install
  tstate and nothing else.

## What is outside the stack

Three things live in the same working environment without being in tmig's
discovery set:

- **sovereign-core** is a docker-compose stack, not a Python package. It
  has its own health check.
- **operator/** is a directory tree of positions, decisions, and
  disconfirmations. It has no tests to run and nothing to hash.
- **gen / toybox** is a scaffold generator. It produces code that may end
  up in repositories, but is not itself a verified artifact.

## What the arrangement is

Eight independent programs that happen to be about the same system, tied
together by one verifier that has no runtime relationship to any of them.
tmig witnesses that each Python program is green and unchanged, and
produces one signed object that says so.
