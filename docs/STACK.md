# How this repository relates to The Mark Intelligence Group's stack

proof-fabric is the read-boundary verification layer. It attaches an Ed25519-signed certificate to a file and re-verifies the certificate against the file's SHA-256 hash on every read, so that a file whose contents have changed since the certificate was issued fails the read rather than being returned. It shares the Merkle and Ed25519 primitives with state-substrate, mlx-omni, and tmig. The rest of this document describes the stack that proof-fabric closes at the read boundary.

## The eight claims, in working order

The claims are listed in the order each one first becomes load-bearing
during a single end-to-end pass. The order is not conceptual -- it is
operational. It is the sequence in which each program does its work.

| # | program | claim | when it runs |
|---|---|---|---|
| 1 | tstate | which states a system can reach | first: to bound what is possible before anything is pinned |
| 2 | state-substrate | a cryptographic attestation of a set of files | second: to pin the current state before any action |
| 3 | mlx-omni | primitives for peers that exchange state without a coordinator | third: to establish causal order across peers |
| 4 | aesn | a signed record of which commands ran | fourth: to execute a declared plan against the pinned state |
| 5 | unified-security-ops | a signed record of security dispatches | fifth: to dispatch security tooling against that state |
| 6 | twin-fabric | a verdict on whether a model matches observed behavior | sixth: to compare the model to what actually happened |
| 7 | proof-fabric | verification at the read boundary | seventh: to verify every artifact at the point of consumption |
| 8 | tmig | one signed manifest over the whole set | eighth: to fold all of the above into one signed object |

Each claim is a precondition for the next. tstate bounds what can
happen. state-substrate pins what is. mlx-omni orders who saw what.
aesn records what ran. unified-security-ops records what was touched.
twin-fabric says whether it matched. proof-fabric verifies at the
boundary. tmig names the whole set in one object.


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

## What the manifest is

The manifest is the single object the stack produces. Everything else
is intermediate. It is written to
`~/operator/signoff/signed/bridge-YYYY-MM-DD.json` and is the only
artifact that names the whole set.

### The manifest as an object

A manifest has identity, structure, invariants, and operations.

**Identity.** A manifest has a name (`bridge-2026-09-28.json`), a
location, a schema version, and a signature. Two manifests are equal
when their `bridge_root` fields are equal. Two manifests are distinct
when those fields differ. The `bridge_root` is the manifest's identity.

**Structure.** Six fields:

| Field | Type | Meaning |
|---|---|---|
| `schema` | string | manifest format version |
| `generated_at` | RFC 3339 timestamp | when the manifest was produced |
| `repos` | list of entries | one entry per discovered repository |
| `repos[i].merkle_root` | hex-64 | root over that repo's tracked files |
| `repos[i].tests` | {ok, summary} | test outcome for that repository |
| `bridge_root` | hex-64 | root over the sorted per-repo roots |
| `signatures` | map | composite signatures over catalogue hashes |
| `ed25519_sig` | base64 | signature over the canonical form |

**Invariants.** Every manifest satisfies all four, or it is not a
manifest:

1. Every `repos[i].tests.ok` is `true`. A manifest over a set in which
   any test suite failed is refused.
2. `bridge_root` recomputes from the per-repo roots in `repos`.
3. Every `repos[i].merkle_root` recomputes from the files on disk in
   that repository.
4. `ed25519_sig` verifies against the public key over the canonical
   form of every other field.

**Operations.** Conceptually, the manifest supports four:

| Operation | Effect |
|---|---|
| `verify(m, pk)` | recompute every root, check the signature, return boolean |
| `compare(m1, m2)` | return the list of repos whose `merkle_root` differs |
| `diff(m1, m2, repo)` | return the list of files whose leaf hashes differ |
| `changed(m)` | return true if the manifest differs from the previous one |

The manifest is what a third party receives. A party holding only the
manifest and the public key can reconstruct every claim the stack made:
which repositories were in the set, what each repository's byte contents
were, what each repository's test suite reported, and when the whole
claim was made.

## A sample end to end

The stack takes declared inputs, produces signed intermediates, folds
them into one manifest, and emits a single verifiable object. Below is
one concrete pass, start to finish.

### Step 0 -- the operator's world before anything runs

The operator has eight repositories under `$HOME`, one Ed25519 key pair
at `~/operator/signoff/keys/`, and three declared artifacts ready to
run:

    ~/aesn/plan.json                    # a plan to execute
    ~/unified-security-ops/scope.txt    # a list of authorized targets
    ~/twin-fabric/model.py              # a model to compare

### Step 1 -- aesn executes a plan

    $ aesn run ~/aesn/plan.json --key ~/operator/signoff/keys/signing.key

    pytest tests/unit                      exit 0    1.18s
    pytest tests/e2e                       exit 0    12.44s
    psql SELECT count(*) FROM users        rows 1    0.06s
    curl https://api.example.com/health    200       0.11s

    transcript: ~/aesn/transcripts/2026-09-28T18-04-11Z.json
    signature:  0f3b9c2a...  (Ed25519)

The transcript records every operation that ran, its exit status, a
SHA-256 hash of its output, and its duration. The transcript is signed
with the operator's Ed25519 key.

### Step 2 -- state-substrate attests the transcript file

    $ state-substrate attest \
        --files ~/aesn/transcripts/2026-09-28T18-04-11Z.json \
        --ops read,deploy \
        --ts now \
        --key ~/operator/signoff/keys/signing.key

    wrote ~/aesn/transcripts/2026-09-28T18-04-11Z.json.attestation
    root:      3e8b9a1c7f2e...
    ts:        2026-09-28T18:11:42Z
    ops:       read, deploy
    signature: MC4CAQAwBQYDK2VwBCIEIG...

The attestation commits to the transcript's byte contents. A party
holding the public key can verify it offline.

### Step 3 -- tmig discovers, tests, hashes, folds, signs

    $ cd ~/tmig && ./bridge verify --timeout 60

    discovered 8 repo(s)

      ok    aesn                       128 passed in 4.27s
      ok    mlx-omni                   348 passed in 27.60s
      ok    proof-fabric                14 passed in 0.08s
      ok    state-substrate             24 passed in 0.06s
      ok    tmig                        57 passed in 12.19s
      ok    tstate                      15 passed in 17.41s
      ok    twin-fabric                 34 passed in 1.99s
      ok    unified-security-ops        14 passed in 0.07s

    8/8 green

    bridge_root: 52ac9b55e1f0a2...
    wrote: attestations/latest.json

For each of the eight repositories, `tmig`:

1. Confirms the discovery predicate (`pyproject.toml` + `tests/` +
   `.git`).
2. Runs the repository's test suite in its own virtual environment, as
   a subprocess.
3. Hashes every tracked file into a SHA-256 hash.
4. Combines the hashes into an RFC 6962 Merkle root.
5. Folds the eight roots into a single `bridge_root` with a second
   Merkle pass.

### Step 4 -- tmig signs

    $ cd ~/tmig && ./bridge sign

    signed: ~/operator/signoff/signed/bridge-2026-09-28.json
    bridge_root: 52ac9b55e1f0a2...
    ed25519_sig: MC4CAQAwBQYDK2VwBCIEIG...

The manifest is only written if every test suite passed. If any suite
failed, `sign` refuses and no new signed manifest exists for that day.

### Step 5 -- what the manifest looks like

    {
      "schema": "tmig/manifest/v1",
      "generated_at": "2026-09-28T18:14:52Z",
      "repos": [
        {"name": "aesn",
         "merkle_root": "7d4f8a2b...",
         "tracked_files": 128,
         "tests": {"ok": true, "summary": "128 passed in 4.27s"}},
        {"name": "mlx-omni",
         "merkle_root": "b1c3e9a7...",
         "tracked_files": 214,
         "tests": {"ok": true, "summary": "348 passed in 27.60s"}},
        ... (six more)
      ],
      "bridge_root": "52ac9b55e1f0a2...",
      "signatures": {
        "failures_sig":   "2464e98a...",
        "forms_sig":      "e2f35cc8...",
        "protocols_sig":  "486f8a16...",
        "term_graph_sig": "e870d7f9...",
        "constants_sig":  "b1d685cb...",
        "standards_sig":  "1917eb79...",
        "axes_sig":       "7f570da7...",
        "envelope_sig":   "076ca3c1...",
        "predicated_sig": "45e92c90...",
        "delegate_sig":   "8925a92b..."
      },
      "ed25519_sig": "MC4CAQAwBQYDK2VwBCIEIG..."
    }

### Step 6 -- an external verifier checks it

A verifier with no access to the operator's machine holds only the
manifest and the public key. The verifier also holds a local clone of
the eight repositories.

    $ tmig verify-manifest ~/received/bridge-2026-09-28.json \
        --pub ~/keys/signing.pub

    schema:      tmig/manifest/v1
    generated:   2026-09-28T18:14:52Z
    signature:   verifies
    bridge_root: 52ac9b55e1f0a2...

    recomputing per-repo roots from local clones:
      aesn              recomputes
      mlx-omni          recomputes
      proof-fabric      recomputes
      state-substrate   recomputes
      tmig              recomputes
      tstate            recomputes
      twin-fabric       recomputes
      unified-security-ops  recomputes

    bridge_root recomputes from the eight roots
    ALL CLAIMS VERIFIED

If any file differs by a single byte, that repository's root no longer
recomputes, `bridge_root` no longer matches, and the verification
fails with the specific repository named.

### Step 7 -- what came out of the stack

One object: `bridge-2026-09-28.json`. From that object and the public
key, any party can establish:

- Which eight repositories were in the set.
- The exact byte contents of every tracked file in every repository.
- What each repository's test suite reported.
- When the manifest was produced.
- That nothing has been changed since.

The `aesn` transcript and the `state-substrate` attestation from
Steps 1 and 2 are intermediates. They are signed artifacts in their own
right, and they are the inputs to the manifest's claim. But the manifest
is the only object that names the whole set. It is the output.

#### Why the manifest is meaningful

The manifest replaces a set of separate trust claims with one. Without
it, a party who wants to know the state of the system must trust the
operator for each repository separately, and must trust that each test
suite ran against the code that was actually on disk at the time. With
the manifest and the public key, that party recomputes. They do not
trust the operator. They trust Ed25519 and SHA-256.

Six properties make the manifest meaningful:

1. **Externally verifiable.** A verifier needs the manifest and the
   public key. No network, no access to the operator's machines, no
   cooperation from the operator.

2. **Content-addressed.** Every byte of every tracked file is committed
   to by a Merkle root. A single changed byte changes that repository's
   root.

3. **Signed.** The `bridge_root` and the per-repo roots are signed with
   Ed25519. Any change after signing invalidates the signature.

4. **Complete.** Every repository in the discovery set appears. The set
   is not a subset chosen for convenience.

5. **Granular.** A change anywhere is localized to one repository's
   `merkle_root`. The diff names which repo changed, and inside that
   repo, which files.

6. **Aggregate.** One `bridge_root` names all eight. A verifier can
   check one value and be confident about the whole set.

#### How The Mark Intelligence Group uses the manifest

Six concrete uses:

1. **Release attestation.** Before publishing any wheel to PyPI, the
   manifest for that day names the exact byte content of every tracked
   file in every repository. The published wheel and the manifest
   together say what was released. An outside party who downloads the
   wheel can check it against the manifest.

2. **Audit by outside parties.** An auditor holding the public key and
   a local clone of the eight repositories runs `tmig
   verify-manifest`. Every per-repo root recomputes or the audit
   fails. No access to the operator's machines is required.

3. **Change detection.** A manifest signed on one day and a manifest
   signed on the next day either share the same `bridge_root` (nothing
   changed) or differ in a specific, nameable way (the diff names which
   repository changed and which files within it).

4. **Compliance evidence.** Regulatory frameworks ask for evidence that
   a specific version of the code was tested and shipped. The manifest
   is that evidence, cryptographically bound to the bytes.

5. **Incident response.** When something breaks, the manifest names the
   exact state of the code at the moment the manifest was signed. A
   rollback target is the commit the manifest names. The manifest
   records what was, not what should have been.

6. **Witness chain.** Each signed manifest is copied to
   `~/tmig-witness/` and committed to a separate git tree. If that tree
   is pushed to a remote controlled by a different party, the record
   becomes an externally auditable chain over time. The witness does
   not need to trust the operator's machine; it needs only the
   manifest, the public key, and its own git history.