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

## Input and output

### What goes in

The stack takes a working environment as its input. Concretely:

- **A working directory of Python repositories.** Each repository satisfies
  one predicate: it contains a `pyproject.toml` declaring either
  `[project]` or `[tool.poetry]`; it contains a `tests/` directory or a
  root-level `test_*.py` file; and it contains a `.git` directory.
  Repositories that fail any condition are omitted from the set.

- **A signing key.** One Ed25519 key pair, held by the operator, stored at
  `~/operator/signoff/keys/`. The public half is distributed to any party
  who will verify a manifest.

- **Declared artifacts.** For `aesn`, a plan — a JSON file naming a list
  of commands and the argument rules each command is permitted to use.
  For `unified-security-ops`, a scope file listing authorized targets.
  For `twin-fabric`, a model and a sampled trace. For `proof-fabric`, a
  certificate paired with a file.

- **Runtime facts.** Files to attest (`state-substrate`), events whose
  causal order matters (`mlx-omni`), states to enumerate (`tstate`).

- **The system itself.** The running processes, database endpoints, and
  network services that `aesn` and `unified-security-ops` operate against.

### What comes out

When every claim has been produced, the stack emits:

- **One signed manifest** at
  `~/operator/signoff/signed/bridge-YYYY-MM-DD.json`. The manifest contains
  the per-repository Merkle roots, the test verdict for each repository,
  the composite signatures over the catalogues, and one Ed25519 signature
  over the whole structure.

- **One bridge root** — an RFC 6962 Merkle root over the eight
  per-repository roots. Any change to any tracked file in any of the eight
  repositories changes this value.

- **A verifiable statement** that a third party holding only the manifest
  and the public key can check offline, with no network access and no
  trust in the machine that produced the manifest.

A manifest is signed only if every discovered repository's test suite
passed. A manifest over a set in which any test suite failed is refused.

### How the group uses the stack

The output is a single artifact — the signed manifest — that replaces the
set of individual claims a project would otherwise make about itself. The
artifact is used in four ways:

1. **Release attestation.** Before publishing a version of any program to
   PyPI, the manifest for that day names the exact byte content of every
   tracked file in every repository. The published version and the
   manifest together say what was released.

2. **Audit by outside parties.** A verifier external to the group holds
   the public key. Given the manifest and the public key, the verifier
   recomputes each repository's Merkle root from a local copy of the files
   and confirms the signature. No access to the group's machines is
   required. Verification is offline.

3. **Change detection.** Because the bridge root is a Merkle root over
   per-repository roots, any modification to any tracked file changes the
   root. A manifest signed on one day and a manifest signed on the next
   day will differ in a specific, nameable way if anything changed, and
   will be byte-identical in the bridge root if nothing did.

4. **Operational record.** `aesn` transcripts and `unified-security-ops`
   provenance chains are signed artifacts of the same shape as the
   manifest. When a deployment runs, an `aesn` transcript records what
   ran. When a security scan runs, a `unified-security-ops` chain records
   what was touched. The stack's purpose across all four uses is to
   convert *"the system is in this state"* from a claim about the
   operator's honesty into a claim about a signature that anyone can
   check.

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

## The three-axis map

The same eight programs can be read on three mathematical
axes — Cayley-Dickson (vertical doubling), Watson-Crick
(horizontal pairing), Hofstadter (the strange loop at the
top). See [`docs/MAPPING.md`](MAPPING.md).
