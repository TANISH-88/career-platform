# Independent review follow-up

Reviewer verdict supplied by owner: CONDITIONALLY APPROVED at 818b1989f78bf64167373e58fe61d2234397abe1. CI #84 green. CP13/14/16 verified; CP15/17/18 partially verified. Reviewer found seed-only changes passed old gate 6/10 times; registry ephemeral; new-data ingestion absent; reference digest unpinned; stale DVC lock; evidence/triggers incomplete.

Corrections committed:
- CP17: fixed primary seed 42; compare 11 matched seeds, paired seed/persona bootstrap with equally weighted personas, macro-F1 non-regression, retain original single-seed gate. This reduces sensitivity but cannot guarantee generalization or eliminate repeated holdout selection bias. The fixed seed set was selected after reviewing the audit and is not independent confirmation.
- CP18: versioned development-only addendum, checksums, provenance, schema, row IDs, feature ranges, duplicate and holdout-persona rejection; frozen evaluation unchanged. Empty manifest because no genuine new data was supplied. Synthetic tests only.
- Reference SHA256 and exact benchmark pinned; candidate CLI and CI use same guarded path; new tests for altered reference, addendum, seed and macro-F1 behavior; corrected workflow triggers.
- DVC stage aligned with candidate-only default CLI. Real DVC reproduction run https://github.com/TANISH-88/career-platform/actions/runs/45491253541 pending; lock must be refreshed from actual output, not fabricated.
- Checkpoints CP15/17/18 reopened. Persistent MLflow registration outside temporary CI remains unverified. For local verification use python ml-training/train.py bootstrap --register --output ml-training/m3-output (fresh output directory, persistent SQLite tracking URI); preserve database and artifact location and verify version 1 can be loaded after process restart.
- No serving binaries changed, no merge, no deployment, no M4. All new CI results require inspection and Claude re-review.
