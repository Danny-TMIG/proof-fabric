# How this repository relates to the stack

**proof-fabric** is the read-boundary verification layer. Verifies that what you are reading right now is what was attested.

## The conceptual stack

Read top-to-bottom as *each layer is about the one below*, not a call path.

    tstate                 pure math: what states are reachable
    state-substrate        cryptography over those states
    mlx-omni               many peers each holding such states
    aesn                   actions taken against such states
    twin-fabric            model vs observed transitions
    unified-security-ops   operational tools on the real system
    proof-fabric           verification at the read boundary
    sovereign-core         the actual system
    tmig                   the verifier that witnesses the set

## Runtime dependency: none

No repo imports another. Each has its own pyproject.toml, own venv, own
version. Even tmig invokes siblings as subprocesses, never as imports.

## Runtime communication: none

No RPC, no message bus, no shared DB, no HTTP between repos.

## The one shared thing

tmig catalogues (failures, forms, protocols, terms) and the signed manifest.
Shared documentarily, not by import.

## Why the split

Each repo is one noun. Different audiences, different math, different
dependencies, different test sizes. The split localizes changes and keeps the
manifest granular — one Merkle root per repo.

## Why not a monorepo

Blast radius, attribution granularity, test isolation, selective adoption.

## Non-members

sovereign-core (docker-compose), operator/ (not code), gen/toybox (producer
side) — excluded by the discovery predicate without special cases.

## What this arrangement is

Eleven independent things about the same system, tied by one witness. The
relationship is witnessing, not dependency.
