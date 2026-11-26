# M3 Part C verification and reviewer handoff

## Verified workflow results (2026-11-25)
- Candidate-only workflow #2: https://github.com/TANISH-88/career-platform/actions/runs/45487376480 — success, commit 1fa93b3383deaa7aad47d4b3465ca467078ef721; job 138776248386.
- Champion/candidate accuracy both 0.1972972972972973; gain 0, paired 90% interval [0,0], 2,000 persona resamples; parity true; promotion_eligible false. Top-1 mismatches 0/160 and top-3 0/480. Rejection is a successful workflow outcome.
- Candidate artifact m3-candidate, ID 14964493210, 2,311,201 bytes; upload successful, expires 2026-12-08T21:05:31Z (14 days).
- Intentional tamper workflow #3: https://github.com/TANISH-88/career-platform/actions/runs/45487439466 — failure, commit 1575944191468105f3481bfaa8c96f46b7324f1c, branch m3/tamper-proof; job 138776470302. Validation failed with exactly: ValueError: Cleaned dataset SHA256 does not match frozen holdout. Artifact upload skipped; zero artifacts. Never merge this branch.
- Initial workflow #1: https://github.com/TANISH-88/career-platform/actions/runs/45487330393 — failed because champion-reference.json had not yet been committed; fixed by 1fa93b3, verified in #2.
- Frozen champion reproduction: https://github.com/TANISH-88/career-platform/actions/runs/45487237769, success; 740 row-aligned predictions from fixed Part B commit 5557227, matching its measured accuracy and macro-F1.
- CP18 technically verified. Main SHA 0fc2b913da5f16a33d579a23d841c7ba6c12436b unchanged at comparison. No serving model binaries changed, no promotion/deployment. Latest full CI for documentation commits was still running at time of inspection.

## Claude review checklist
Review branch m3/part-a-corrected against main. Do not merge or deploy before review.
1. CP13/14: see docs/m3/part-a-verification.md. Check exact deduplication, persona IDs, role mapping and frozen split. Original 2/8 quota impossible, approved at least 1/1 for all roles. API Specialist has 2 total personas.
2. CP15/16/17: see docs/m3/part-b-verification.md and model card. Verify the historical model is not an unseen-persona baseline; champion dev-only training, row-aligned paired bootstrap and parity. CI registry is ephemeral, not production. Exact test results: 49 backend + 9 ML passed, 3 legacy DVC tests skipped.
3. CP18: review workflow, immutable-by-convention reference, artifact retention and both run logs above. Check whether the reference should have an independently pinned digest or stronger protection, and whether holdout identity/versioning needs additional safeguards. Workflow intentionally rejects changes to the frozen dataset unless a reviewed evaluation version is prepared; it does not yet ingest arbitrary new development-only data. Manual workflow dispatch becomes available once the workflow exists on default branch; push trigger verified. Historical dvc.lock remains stale until a reviewed DVC reproduction. No M4 work started.
4. Review whether checkpoint requirements are fully met; flag any missing evidence, bugs or changes required. Do not claim final approval merely from green CI.
