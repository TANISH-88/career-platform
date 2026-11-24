# M3 Part B verification — CI #66

Commit: 55572273068bdad19d719149df877d7b00fd01d1
Branch: m3/part-a-corrected
CI: https://github.com/TANISH-88/career-platform/actions/workflows/ci.yml?query=branch%3Am3%2Fpart-a-corrected
Evidence: owner-supplied green CI screenshot and exact champion/candidate verification log.

- Champion recipe fixed to notebook RF; trained on development personas only.
- Frozen holdout: 44 personas, 740 rows.
- Champion accuracy: 0.1972972972972973 (146/740); macro-F1: 0.16639113268278288.
- MLflow champion career-rf-m3-champion version 1, run 00f7fb527e4d46d2a7b32cde98d9e830.
- Legacy career-rf-legacy version 1 separately registered, historical training included holdout personas, not comparable.
- Registry was isolated SQLite in CI; not a persistent production registry.
- Champion and identical candidate parity passed: max probability difference 0.00e+00, top-1 0/160 and top-3 0/480 mismatches each.
- Candidate accuracy: 0.1972972972972973; observed gain 0; paired 90% interval [0, 0]; min gain 0.02; seed 42; 2,000 persona resamples; promotion_eligible=false.
- CI #66 backend, frontend and Docker succeeded. Workflow contains the synthetic gate tests and explicit assertions on registry versions and identical candidate rejection. Exact individual gate test log was not supplied.
- Model signature warning from MLflow; no deployment. Existing serving binaries unchanged.
- Part C requires a durable champion reference (frozen row-aligned predictions or artifact); CI #66 uploaded reports only. No production promotion approved.
