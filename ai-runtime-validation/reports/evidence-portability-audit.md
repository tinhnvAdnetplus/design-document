# Evidence Portability Audit

## Finding

Historical validation manifests created before evidence format version 2 include
live nested Git metadata. Those `.git` directories are not representable as
ordinary files in the outer repository, so a historical manifest can pass in
the originating workspace and fail after a clean clone.

The run `20260803T040752Z-130658` contains 344 manifest entries. A clean-clone
audit recovered 52 entries and reported 292 missing entries. This finding does
not invalidate the reproducible 82/82 contract result, but it means the old
artifact directory is not a self-contained evidence package.

## Remediation

Evidence format version 2 performs the following steps before writing a
manifest:

1. Capture each nested repository's HEAD, refs, and porcelain status.
2. Export all refs to a verified Git bundle.
3. Remove live nested `.git` metadata from the artifact directory.
4. Hash the portable bundle, metadata, working files, reports, and environment.
5. Verify the resulting package with `scripts/verify-evidence.sh`.

Historical committed evidence is retained unchanged. New evidence must pass the
portable verifier on a clean checkout.
