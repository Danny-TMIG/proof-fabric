# How this repo relates to the stack

**proof-fabric**: The read-boundary verification layer: re-verifies on every read.

```
tstate -> state-substrate -> mlx-omni
                              aesn
                              twin-fabric
                              unified-security-ops
                              proof-fabric
     sovereign-core (the real system)
     tmig (witnesses the seven)
```

## Runtime dependency: none
No repo imports another. Each has its own venv and dependencies. Even tmig
invokes siblings as subprocesses, never as imports.

## Runtime communication: none
No RPC, no message bus, no shared DB, no HTTP between repos.

## The one shared thing
tmig's catalogues (failures, forms, protocols, terms) and the signed
manifest. Shared documentarily, not by import.

## Why the split
Each repo is one noun. Different audiences, different math, different
dependencies, different test sizes. The split localizes changes and keeps
the manifest granular — one Merkle root per repo.

## Why not a monorepo
Blast radius, attribution granularity, test isolation, selective adoption.

## The non-members
sovereign-core (docker-compose), operator/ (not code), gen/toybox
(producer side) — excluded by the discovery predicate without special cases.

## What it is
Eleven independent things about the same system, tied by one witness.
The relationship is witnessing, not dependency. tmig asserts, under
signature, that each Python repo is green and unchanged at a moment.
