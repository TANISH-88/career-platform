# Independent review follow-up

Reviewer verdict supplied by owner: CONDITIONALLY APPROVED at 818b1989f78bf64167373e58fe61d2234397abe1. CI #84 green. CP13/14/16 verified; CP15/17/18 partially verified. Reviewer found seed-only changes passed old gate 6/10 times; registry ephemeral; new-data ingestion absent; reference digest unpinned; stale DVC lock; evidence/triggers incomplete.

Corrections committed:
- CP17: fixed primary seed 42; compare 11 matched seeds, paired seed/persona bootstrap with equally weighted personas, macro-F1 non-regression, retain original single-seed gate. This reduces sensitivity but cannot guarantee generalization or eliminate repeated holdout selection bias. The fixed seed set was selected after reviewing the audit and is not independent confirmation.
- CP18: versioned development-only addendum, checksums, provenance, schema, row IDs, feature ranges, duplicate and holdout-persona rejection; frozen evaluation unchanged. Empty manifest because no genuine new data was supplied. Synthetic tests only.
- Reference SHA256 and exact benchmark pinned; candidate CLI and CI use same guarded path; new tests for altered reference, addendum, seed and macro-F1 behavior; corrected workflow triggers.
- DVC stage aligned with candidate-only default CLI. Real DVC reproduction run https://github.com/TANISH-88/career-platform/actions/runs/45491253541 pending; lock must be refreshed from actual output, not fabricated.
- Checkpoints CP15/17/18 reopened. Persistent MLflow registration outside temporary CI remains unverified. For local verification use python ml-training/train.py bootstrap --register --output ml-training/m3-output (fresh output directory, persistent SQLite tracking URI); preserve database and artifact location and verify version 1 can be loaded after process restart.
- No serving binaries changed, no merge, no deployment, no M4. All new CI results require inspection and Claude re-review.

## Follow-up evidence

- DVC #1 failed: DVC 3.51.2 imported `_DIR_MARK`, unavailable in pathspec 1.1.1. Pinned pathspec 0.12.1 in workflow and training requirements. DVC #2 succeeded, run https://github.com/TANISH-88/career-platform/actions/runs/45491639091, artifact 14966207110. Actual regenerated lock committed at d93a7b7 (output: Updating lock file 'dvc.lock').
- CI #101, https://github.com/TANISH-88/career-platform/actions/runs/45491374320: 49 backend passed, 14 ML passed, 3 skipped (63 total passed). All five review-correction tests passed. Candidate #14 https://github.com/TANISH-88/career-platform/actions/runs/45491652918: mean matched seed gain 0, equal-persona gain 0, macro-F1 gain 0, promotion_eligible false; artifact 14965599417.
- Separate synthetic addendum push proof branch m3/addendum-proof, commit ee590e8, workflow https://github.com/TANISH-88/career-platform/actions/runs/45492166328, pending. Never merge this branch. Real addendum stays empty.
- Persistent local registration still needs owner evidence; final reviewer approval remains pending.

- Synthetic development addendum workflow https://github.com/TANISH-88/career-platform/actions/runs/45492166328 succeeded (commit ee590e8, job 138793052603). Champion accuracy 0.1972972972972973, candidate 0.20405405405405405, gain 0.006756756756756757, 90% CI [-0.01775543578606786, 0.03735740126446213], mean matched-seed row gain -0.006511056511056512, mean equal-persona gain -0.005120195461104551, mean seed macro-F1 gain -0.011685913991271463. Parity passed, promotion_eligible false, artifact 14965219827 uploaded. This is workflow proof using synthetic test data, not evidence of improved real-world performance. Never merge m3/addendum-proof. CP17/18 corrections technically verified; independent sign-off pending. CP15 persistent registration remains open.
