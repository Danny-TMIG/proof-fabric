# The three-axis map — proof-fabric

**proof-fabric** is the read-boundary layer. On the vertical axis, proof-fabric is level 7 — the level at which once-for-all verification is lost. On the horizontal axis, it supplies the (file, certificate) pair. On the cyclic axis, proof-fabric is not reflexive: a certificate may be checked on read, but the check does not produce a new certificate unless the caller writes one.

The rest of this document is identical in all eight repos.

## The three axes

Three mathematical structures describe the same object — the stack — from
three different angles. They are not three descriptions. They are three
axes of one description.

### Axis 1 — Cayley-Dickson: vertical doubling

The Cayley-Dickson construction doubles an algebra at each step:

    R (1)  ->  C (2)  ->  H (4)  ->  O (8)  ->  S (16)  ->  ...

Each doubling gains a dimension and loses exactly one algebraic property:
order, then commutativity, then associativity, then alternativity, then
divisibility. Monotone in dimension, monotone in loss. The stack is a
Cayley-Dickson tower in the same sense:

| Level | Program | Doubles from below | Loses |
|---|---|---|---|
| 1 | tstate | — | — |
| 2 | state-substrate | a file set into (root, signature) | verification without a key |
| 3 | mlx-omni | one state into (state, causal clock) | the single-writer assumption |
| 4 | aesn | a permitted action into (action, transcript) | purity — side effects exist |
| 5 | twin-fabric | a model into (model, trace) | the closed-world assumption |
| 6 | unified-security-ops | a dispatch into (dispatch, provenance) | abstraction — real systems |
| 7 | proof-fabric | a certificate into (certificate, re-check) | once-for-all verification |
| 8 | tmig | the verified set into (repo roots, bridge root) | — see Axis 3 |

Level 8 does not lose a property. It closes a loop. That is Axis 3.

### Axis 2 — Watson-Crick: horizontal pairing

Watson-Crick pairing pairs two complementary bases. A pairs with T; G
pairs with C. The pairing is a fixed point of complement:
complement(complement(x)) = x. Each base alone carries half the
information. Only the pair carries the strand. Each level of the stack is
the same structure: a producer and a verifier that pair.

| Level | Producer | Verifier |
|---|---|---|
| tstate | reachable set | cycle set |
| state-substrate | Merkle root | Ed25519 signature over the root |
| mlx-omni | event | vector-clock timestamp |
| aesn | plan | transcript |
| twin-fabric | model | trace |
| unified-security-ops | scope file | signed dispatch log |
| proof-fabric | file | certificate |
| tmig | repo Merkle root | bridge Merkle root |

A plan without a transcript is a wish. A certificate without a file is a
commitment to nothing. A file without a certificate is a claim with no
witness. The pair is the base of a base-pair.

### Axis 3 — Hofstadter: the strange loop

Hofstadter's central image is the strange loop — a hierarchy whose top
level refers back to its bottom, so the system describes itself describing
itself. Bach's canons. Escher's hands drawing hands. Goedel's sentence
that says of itself that it is unprovable.

The stack closes such a loop at `tmig`. The discovery predicate is:

    pyproject.toml  +  tests/  +  .git

tmig satisfies all three. tmig discovers itself, runs its own test suite,
hashes its own files into the bridge root. The manifest that tmig signs
contains a Merkle root over tmig's own source, including the code that
produced the manifest. The verifier is inside the set it verifies.

The loop does not fully close — the signer's public key must be trusted
from outside — but it closes far enough to be useful. Any change to
tmig's source changes the bridge root. Any change to the bridge root
invalidates the signature.

### The three axes are one object

- Vertical (Cayley-Dickson) — dimension. How many independent things
  the stack distinguishes.
- Horizontal (Watson-Crick) — complementarity. How those things pair.
- Cyclic (Hofstadter) — reflexivity. What happens at the top.

Cut one way: eight levels of doubling. Cut another: eight pairs of
complementary claims. Cut a third: a single loop that returns on itself.

### What the map predicts

If the map is right, three things hold:

1. A new level would lose exactly one property. The level above tmig, if
   one exists, would lose "verifiable without trusting the key
   distribution."
2. Every producer has a verifier. A program without a complement is not a
   level. It is a utility.
3. The loop stays closed. Any change to the discovery predicate must
   preserve the reflexive case. Removing tmig from tmig's own discovery
   set opens the loop.

Fail any of the three, and the map is wrong.
