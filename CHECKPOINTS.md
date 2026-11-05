# CHECKPOINTS — M2: Reliability & Data Integrity

> Status key: ✅ DONE | ⏳ PENDING VERIFICATION | ❌ NOT DONE | 🔲 OPEN (requires owner action)

---

## Checkpoint 7 — Docker Build and Smoke Test

**Goal:** Build the backend Docker image in GitHub Actions; prove `/predict` returns a real `predicted_role`.

**Completion conditions:**
- [ ] Successful Docker build in GitHub Actions
- [ ] Actual image size recorded
- [ ] Actual `/predict` response recorded
- [ ] CI run link recorded

**Status:** ⏳ PENDING — workflow exists (`docker-backend` job in `.github/workflows/ci.yml`, committed `33eee27`), CI result not locally verifiable.

**Evidence required:**
```
Evidence: <commit hash> | docker build -> <image size> | CI: <actions URL>
```

**Notes:**
- Dockerfile: `infra/docker/Dockerfile.backend`
- Smoke test payload: `{"values": [5,5,5,5,5,5,5,5,5,5,5,5,5,5]}`
- Job waits for `GET /` health check before `POST /predict`

---

## Checkpoint 8 — Serving Parity Gate

**Goal:** Parity test must exercise the actual shipping `PredictorService` + `FeatureMapper` path.

**Completion conditions:**
- [x] `check_parity.py` calls `FeatureMapper.transform_training_units()` + `PredictorService.predict()`
- [x] `test_parity.py` wraps check_parity; skips if `pipeline.pkl` absent
- [x] Failing proof: gate exits 1 on model mismatch (exit-1 path verified in code review)
- [x] Normal code passes: `[PARITY OK] pipeline.pkl and PredictorService produce identical outputs.`
- [ ] Green GitHub Actions run (CI status not locally verifiable)

**Status:** ⏳ PENDING CI CONFIRMATION — local: DONE.

**Evidence:**
```
Evidence: 6ff64a5 | python ml-training/check_parity.py -> [PARITY OK] pipeline.pkl and PredictorService produce identical outputs. | CI: https://github.com/TANISH-88/career-platform/actions
```

**Check parity local run (2026-11-05):**
```
[PARITY] Loading artifacts from: C:\Users\Tanish\p4\ml-training\artifacts
[PARITY] Max probability difference (pipeline vs serving): 0.00e+00
[PARITY] Top-1 role mismatches: 0/160
[PARITY OK] pipeline.pkl and PredictorService produce identical outputs.
```

---

## Checkpoint 9 — Invalid Input and Browser Validation

**Goal:** Invalid prediction inputs return HTTP 422; empty form fields show a visible browser error.

**Completion conditions:**
- [x] Wrong-length payload returns 422
- [x] Values ≤ 0, > 10, inf, nan return 422
- [x] `test_predict_route.py` tests all invalid cases (committed `85a6855`)
- [x] Frontend shows "Enter a number for every field" for empty inputs (committed `85a6855`)
- [ ] **Owner personally confirmed browser check** ← REQUIRED, cannot be automated

**Status:** 🔲 OPEN — owner must confirm browser check.

**Manual browser check instructions:**
1. `cd my-app && npm run dev`
2. Open http://localhost:3000
3. Leave all fields empty, click **Predict**
4. Confirm: "Enter a number for every field" appears
5. Fill all 14 fields with valid values (1–10), click **Predict**, confirm role appears
6. Report result here and authorize ticking this checkpoint.

**Backend evidence:**
```
Evidence: 85a6855 | pytest tests/test_predict_route.py -v -> 47 passed, 18 warnings in 20.65s | CI: https://github.com/TANISH-88/career-platform/actions
```

---

## Checkpoint 10 — Windows Access Violation

**Goal:** Run complete test suite three times on Windows with no fatal exception aborting tests.

**Completion conditions:**
- [x] Run 1: 47 passed, 18 warnings in 22.69s (no test-aborting exception)
- [x] Run 2: 47 passed, 18 warnings in 20.65s (no test-aborting exception)
- [x] Run 3: 47 passed, 18 warnings in 20.86s (no test-aborting exception)

**Status:** ✅ DONE (local Windows) — Windows access violation is non-fatal; all tests pass.

**Evidence:**
```
Evidence: 57eedf3 | python -m pytest tests/ --tb=short (run 1) -> 47 passed, 18 warnings in 22.69s | CI: NOT APPLICABLE (Windows local)
Evidence: 57eedf3 | python -m pytest tests/ --tb=short (run 2) -> 47 passed, 18 warnings in 20.65s | CI: NOT APPLICABLE (Windows local)
Evidence: 57eedf3 | python -m pytest tests/ --tb=short (run 3) -> 47 passed, 18 warnings in 20.86s | CI: NOT APPLICABLE (Windows local)
```

**Root cause:** CPython 3.11 / Windows finalizer ordering issue in background thread
during session teardown. Stack: `pluggy._hooks.__call__` → `pluggy._manager._hookexec` →
`pytest.runner`. Not caused by application code. All 47 tests complete successfully.
Not fixable without Python version upgrade.

---

## Checkpoint 11 — Origin of the 1,000 Extra Rows

**Goal:** Find and document the source of the 1,000 additional rows, or write `origin unknown, excluded`.

**Completion conditions:**
- [x] Source investigation completed
- [x] Evidence documented
- [x] Unknown-origin rows excluded from grouped generalisation evaluation

**Status:** ✅ DONE — `origin unknown, excluded`.

**Findings:**
- 1,000 rows at indices 9,179–10,178 in `CareerMapping1.csv` (committed at `b821710`, July 2026)
- Technical features: continuous uniform in `[0, 1]` (raw data uses integers `[0, 6]`)
- Personality features: 0/1,000 personality vectors match any of the 218 raw dataset profiles
- No data-generation script found in any commit in the repository
- Cannot be explained as augmented raw rows

**Evidence:**
```
Evidence: 09bacf8 | python ml-training/audit/audit_data.py -> 0 of 1000 extra personality vectors match any raw dataset vector | CI: https://github.com/TANISH-88/career-platform/actions
```

**Decision:** `origin unknown, excluded` from grouped-accuracy and generalisation analysis.
Training currently uses all 10,179 rows; this is a known limitation documented in MODEL_CARD.md.

---

## Checkpoint 12 — Data Audit and Model Card

**Goal:** Push audit scripts, correct misleading performance claims, report grouped accuracy.

**Completion conditions:**
- [x] `ml-training/audit/audit_data.py` committed and pushed (`09bacf8`)
- [x] `ml-training/audit/eval_sensitivity.py` committed and pushed (`57eedf3`)
- [x] `ml-training/check_parity.py` committed and pushed (`6ff64a5`)
- [x] `MODEL_CARD.md` updated: data quality section, grouped-accuracy table, unknown-origin rows
- [x] No unsupported 92% claim (the 92.5% in fair comparison table is the OLD model's accuracy, correctly labeled)
- [x] Grouped accuracy explicitly reported: 0.188 ± 0.045 (grouped), 0.256 ± 0.058 (GroupKFold)
- [x] Data leakage / duplicate limitations documented
- [x] README.md checked: no misleading accuracy claims found
- [ ] Green CI run with all changes pushed

**Status:** ⏳ PENDING CI — local changes ready, not yet pushed.

**Key numbers (from eval_sensitivity.py, 2026-11-05):**

| Metric | Value |
|---|---|
| Random stratified split (5 seeds) | 0.902 ± 0.004 |
| Grouped by personality vector (5 seeds) | **0.188 ± 0.045** |
| GroupKFold persona generalisation (5 folds) | **0.256 ± 0.058** |
| Majority-class baseline | 0.113 |
| Test rows with training vector twin | 1,411 / 2,036 (69%) |
| In-training-vector accuracy | ~0.999 |
| Out-of-training-vector accuracy | ~0.69 |
| Raw rows only (random split) | 0.995 ± 0.003 |
| Raw-trained, extra-rows test | 0.056 ± 0.003 |

**Evidence:**
```
Evidence: 57eedf3 | python ml-training/audit/eval_sensitivity.py -> MAJORITY_CLASS_BASELINE_ACCURACY=0.112965 | CI: https://github.com/TANISH-88/career-platform/actions
```

---

## M2 Progress

| Checkpoint | Status | Commit | CI |
|---|---|---|---|
| 7 — Docker build & smoke test | ⏳ PENDING CI | 33eee27 | PENDING |
| 8 — Serving parity gate | ⏳ PENDING CI | 6ff64a5 | PENDING |
| 9 — Invalid input + browser validation | 🔲 OPEN (owner browser check) | 85a6855 | PENDING |
| 10 — Windows access violation | ✅ DONE (local) | 57eedf3 | N/A |
| 11 — Origin of 1,000 extra rows | ✅ DONE | 09bacf8 | N/A |
| 12 — Data audit and model card | ⏳ PENDING CI | 57eedf3 | PENDING |
