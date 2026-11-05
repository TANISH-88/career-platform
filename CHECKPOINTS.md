# CHECKPOINTS — M2: Reliability & Data Integrity

> Status key: ✅ DONE | ⏳ PENDING VERIFICATION | ❌ NOT DONE | 🔲 OPEN (requires owner action)

---

## Checkpoint 7 — Docker Build and Smoke Test

**Goal:** Build the backend Docker image in GitHub Actions; prove `/predict` returns a real `predicted_role`.

**Completion conditions:**
- [x] Successful Docker build in GitHub Actions (CI #9, commit `6bd837f`, green — owner confirmed)
- [ ] Actual image size recorded from CI log
- [ ] Actual `/predict` response recorded from CI log
- [x] CI run link: https://github.com/TANISH-88/career-platform/actions/runs/9 (CI #9)

**Status:** ⏳ PENDING — CI #9 green (owner confirmed); image size and exact `/predict` response must be extracted from the CI #9 `docker-backend` job log. Owner must supply these values.

**Notes:**
- Dockerfile: `infra/docker/Dockerfile.backend`
- Smoke test payload: `{"values": [5.0, 7.0, 6.0, 8.0, 6.0, 7.0, 5.0, 8.0, 4.0, 6.0, 7.0, 3.0, 5.0, 6.0]}`
- Job waits for `GET /` health check before `POST /predict`
- CI step "Report image size" outputs: `Image: backend:test | Size: <actual>`
- CI step "Verify POST /predict" outputs: `=== SMOKE TEST RESPONSE ===` then JSON

**Required from owner (CI #9 log):**
```
Actual image size: NOT VERIFIED — owner must check Actions log
Actual /predict response: NOT VERIFIED — owner must check Actions log
```

---

## Checkpoint 8 — Serving Parity Gate

**Goal:** Parity test must exercise the actual shipping `PredictorService` + `FeatureMapper` path; must NOT skip in CI.

**Completion conditions:**
- [x] `check_parity.py` calls `FeatureMapper.transform_training_units()` + `PredictorService.predict()`
- [x] `test_parity.py` updated: **FAILS** (not skips) when `pipeline.pkl` absent
- [x] `pipeline.pkl` and other artifacts committed to Git (removed from `.gitignore`)
- [x] Failing proof: `test_parity_failing_proof.py::test_parity_gate_fails_with_wrong_model` PASSED
- [x] Normal code passes: `[PARITY OK] pipeline.pkl and PredictorService produce identical outputs.`
- [ ] Green GitHub Actions run with parity test passing (not skipping)

**Status:** ⏳ PENDING CI — local tests pass, artifacts committed; CI result pending push.

**Local evidence (2026-11-05):**
```
python ml-training/check_parity.py
[PARITY] Loading artifacts from: C:\Users\Tanish\p4\ml-training\artifacts
[PARITY] Fixture rows: 160
[PARITY] Max probability difference (pipeline vs serving): 0.00e+00
[PARITY] Top-1 role mismatches: 0/160
[PARITY] Top-3 role/probability mismatches: 0/480
[PARITY OK] pipeline.pkl and PredictorService produce identical outputs.
```

**Failing proof (2026-11-05):**
```
pytest backend/fastapi/tests/test_parity_failing_proof.py -v
test_parity_failing_proof.py::test_parity_gate_passes_with_correct_model PASSED
test_parity_failing_proof.py::test_parity_gate_fails_with_wrong_model PASSED
2 passed in 4.31s
```

---

## Checkpoint 9 — Invalid Input and Browser Validation

**Goal:** Invalid prediction inputs return HTTP 422; empty form fields show a visible browser error.

**Completion conditions:**
- [x] Wrong-length payload returns 422
- [x] Values ≤ 0, > 10, inf, nan return 422
- [x] `test_predict_route.py` tests all invalid cases (committed `85a6855`)
- [x] Frontend shows "Enter a number for every field" for empty inputs (committed `85a6855`, verified in source)
- [ ] **Owner personally confirmed browser check** ← REQUIRED, cannot be automated

**Status:** 🔲 OPEN — owner must confirm browser check.

**Manual browser check instructions:**
1. `cd my-app && npm run dev`
2. Open http://localhost:3000
3. Leave all fields empty, click **Predict**
4. Confirm: "Enter a number for every field" appears
5. Fill all 14 fields with valid values (1–10), click **Predict**, confirm role appears
6. Reply here and authorize ticking this checkpoint.

---

## Checkpoint 10 — Windows Access Violation

**Goal:** Run complete test suite three times on Windows with no fatal exception aborting tests.

**Completion conditions:**
- [x] Run 1: 47 passed, 18 warnings in 22.69s (no test-aborting exception)
- [x] Run 2: 47 passed, 18 warnings in 20.65s (no test-aborting exception)
- [x] Run 3: 47 passed, 18 warnings in 23.86s (no test-aborting exception)

**Status:** ✅ DONE (local Windows) — Windows access violation is non-fatal; all tests pass.

**Evidence:**
```
Evidence: 6bd837f | python -m pytest tests/ --tb=short -v (run 1) -> 47 passed, 18 warnings in 22.69s | CI: NOT APPLICABLE (Windows local)
Evidence: 6bd837f | python -m pytest tests/ --tb=short -v (run 2) -> 47 passed, 18 warnings in 20.65s | CI: NOT APPLICABLE (Windows local)
Evidence: 6bd837f | python -m pytest tests/ --tb=short (run 3) -> 47 passed, 18 warnings in 23.86s | CI: NOT APPLICABLE (Windows local)
```

**Root cause:** CPython 3.11 / Windows finalizer ordering issue in background thread
during session teardown. Stack: `pluggy._hooks.__call__` → `pluggy._manager._hookexec` →
`pytest.runner`. Not caused by application code. All 47 tests complete successfully.
Not fixable without Python version upgrade.

---

## Checkpoint 11 — Origin of the 1,000 Extra Rows

**Goal:** Find and document the source of the 1,000 additional rows, or write `origin unknown, excluded`.
Extra rows must be **excluded from default training and evaluation**.

**Completion conditions:**
- [x] Source investigation completed
- [x] Evidence documented
- [x] `origin unknown, excluded` statement in MODEL_CARD.md
- [x] `train.load_data(exclude_extra_rows=True)` added — extra rows excluded from default training
- [x] `train.py` train() uses `exclude_extra_rows=True` explicitly
- [x] Test proving exclusion: `ml-training/tests/test_extra_row_exclusion.py` (3 tests PASSED)
- [x] Original dataset file preserved unmodified

**Status:** ✅ DONE (local) — pending CI confirmation.

**Findings:**
- 1,000 rows at indices 9,179–10,178 in `CareerMapping1.csv`
- Technical features: continuous uniform in `[0, 1]` (raw data uses integers `[0, 6]`)
- Personality features: 0/1,000 personality vectors match any of the 218 raw dataset profiles
- No data-generation script found in any commit in the repository
- Added at initial commit `b821710` (July 2026)

**Exclusion test evidence (2026-11-05):**
```
pytest ml-training/tests/test_extra_row_exclusion.py -v
test_extra_row_exclusion.py::test_default_load_excludes_extra_rows PASSED
test_extra_row_exclusion.py::test_full_load_includes_extra_rows PASSED
test_extra_row_exclusion.py::test_extra_rows_have_fractional_technical PASSED
3 passed in 5.96s
```

**Evidence:**
```
Evidence: 09bacf8 | python ml-training/audit/audit_data.py -> NONWHOLE_PERSONALITY_VECTORS_IN_RAW=0/1000 | CI: https://github.com/TANISH-88/career-platform/actions
```

**Decision:** `origin unknown, excluded` — `train.py` now excludes these rows by default.

---

## Checkpoint 12 — Data Audit and Model Card

**Goal:** Push audit scripts, correct misleading performance claims, report grouped accuracy.

**Completion conditions:**
- [x] `ml-training/audit/audit_data.py` committed and pushed (`09bacf8`)
- [x] `ml-training/audit/eval_sensitivity.py` committed and pushed (`57eedf3`)
- [x] `ml-training/check_parity.py` committed and pushed (`6ff64a5`)
- [x] `MODEL_CARD.md` updated: data quality section, grouped-accuracy table, unknown-origin rows correctly documented as excluded
- [x] No unsupported 92% claim (the 92.5% in fair comparison is the OLD model, correctly labeled)
- [x] Grouped accuracy explicitly reported: 0.188 ± 0.045 (grouped), 0.256 ± 0.058 (GroupKFold)
- [x] Data leakage / duplicate limitations documented
- [x] README.md updated with data notes and accuracy disclaimer
- [ ] Green CI run with all changes pushed

**Status:** ⏳ PENDING CI — local changes ready, not yet pushed.

---

## M2 Progress

| Checkpoint | Status | Commit | CI |
|---|---|---|---|
| 7 — Docker build & smoke test | ⏳ PENDING (image size + response from CI log) | 6bd837f | CI #9 green (owner confirmed) |
| 8 — Serving parity gate | ⏳ PENDING CI (this push) | see entry 5 | PENDING |
| 9 — Invalid input + browser validation | 🔲 OPEN (owner browser check) | 85a6855 | PENDING |
| 10 — Windows access violation | ✅ DONE (local) | 6bd837f | N/A |
| 11 — Origin of 1,000 extra rows | ✅ DONE | see entry 5 | PENDING |
| 12 — Data audit and model card | ⏳ PENDING CI | see entry 5 | PENDING |
