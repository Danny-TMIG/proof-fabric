<!-- tmig-stack-intro -->

## What this is

**proof-fabric** is the read-side of the stack: it lets an artifact — a build output, a data file, a certificate — be published alongside a signed certificate, and re-verifies that certificate against the artifact's actual hash every time the artifact is read, so a stored file and its proof can never silently drift apart. Certificates are Ed25519-signed, the hash is checked in-process on each access, and if anything has changed since the certificate was issued the read fails loudly rather than quietly serving the wrong bytes. Its purpose is to make *the bytes you got are the bytes that were attested* a runtime property rather than an assumption, and to give the rest of the stack a canonical way to hand a file to a consumer with proof of what it is, not just evidence of what it once was.

*Part of the [tmig stack](https://github.com/Danny-TMIG/tmig).*
