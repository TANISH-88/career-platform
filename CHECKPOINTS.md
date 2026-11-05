# CHECKPOINTS — Living Resume Career Platform

> Progress: 8/30 genuinely verified | Status key: ✅ DONE | ⏳ PENDING VERIFICATION | ❌ NOT DONE | 🔲 OPEN (requires owner action)
>
> Progress count: Only checkpoints with ALL required evidence satisfied are counted.
> CPs 1–6 (Foundation): 6 ✅ | CPs 7–12 (M2): CP10 ✅, CP11 ✅ (2 verified) | CPs 13–30, S1–S5: 0 ✅

---

## Phase: Foundation (Checkpoints 1–6)

### CP1 — Backend Architecture Refactor

**Goal:** Refactor the backend into a clean services / schemas / routes structure.

**Completion conditions:**
- [x] `services/`, `schemas/`, `routes/` structure in place
- [x] `PredictorService` and `FeatureMapper` classes separated from route handlers
- [x] All existing tests pass after refactor

**Status:** ✅ DONE

**Evidence:**
```
Evidence: 2d999ed | git show --stat 2d999ed -> clean architecture verified in codebase | CI: N/A (pre-CI era)
```

---

### CP2 — ML Model Serving (FeatureMapper + PredictorService)

**Goal:** `FeatureMapper` correctly converts UI-scale `[1, 10]` inputs to training-scale units; `PredictorService` wraps the Random Forest pipeline.

**Completion conditions:**
- [x] `FeatureMapper.transform_training_units()` converts UI inputs to training scale
- [x] `PredictorService.predict()` returns predicted role and probabilities
- [x] Unit tests cover transformation and prediction

**Status:** ✅ DONE

**Evidence:**
```
Evidence: f58b17d | git log --oneline f58b17d -> fix(serve): convert UI [1-10] inputs to training units | CI: N/A
```

---

### CP3 — MLflow Integration and Training Pipeline

**Goal:** `train.py` logs parameters, metrics and artifacts to MLflow; sklearn version pinned.

**Completion conditions:**
- [x] `train.py` integrated with MLflow
- [x] sklearn upgraded from 1.5.1 to 1.7.1
- [x] DVC pipeline configured

**Status:** ✅ DONE

**Evidence:**
```
Evidence: 24f4597 | git log --oneline 24f4597 -> feat(MLOps/M1): train.py + MLflow + DVC + sklearn 1.5.1->1.7.1 | CI: N/A
```

---

### CP4 — DVC Data Versioning

**Goal:** DVC remote configured with relative path; `dvc.yaml` pipeline reproducible.

**Completion conditions:**
- [x] DVC remote set to relative local path
- [x] `dvc repro` runs without absolute-path errors
- [x] `.dvc` files committed

**Status:** ✅ DONE

**Evidence:**
```
Evidence: 6239c24 | git log --oneline 6239c24 -> chore(dvc): use relative path for local_storage remote | CI: N/A
```

---

### CP5 — Frontend Next.js with Prediction Form

**Goal:** `my-app/` Next.js application with a functional 14-field prediction form that calls the backend `/predict` endpoint.

**Completion conditions:**
- [x] `my-app/` exists with Next.js application
- [x] Prediction form with 14 slider/number fields
- [x] Form submits to backend and displays `predicted_role`

**Status:** ✅ DONE

**Evidence:**
```
Evidence: 2d999ed | git show --stat 2d999ed -> my-app/ frontend with prediction form | CI: N/A
```

---

### CP6 — Resume Parsing Integration

**Goal:** Backend accepts resume uploads; `ResumeParser` extracts features; `/resume` route returns parsed data.

**Completion conditions:**
- [x] `ResumeParser` class implemented
- [x] `/resume` route accepting PDF/DOCX uploads
- [x] Parsed features returned as JSON

**Status:** ✅ DONE

**Evidence:**
```
Evidence: 2d999ed | git show --stat 2d999ed -> ResumeParser and resume routes present | CI: N/A
```

---

## Phase: Close M2 — Reliability & Data Integrity (Checkpoints 7–12)

### CP7 — Docker Build and Smoke Test

**Goal:** Build the backend Docker image in GitHub Actions and prove that the actual prediction endpoint works inside the container.

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

**Required from owner (CI log):**
```
Actual image size: NOT VERIFIED — owner must check Actions log
Actual /predict response: NOT VERIFIED — owner must check Actions log
```

---

### CP8 — Serving Parity Gate

**Goal:** Parity test must exercise the actual shipping `PredictorService` + `FeatureMapper` path; must NOT skip in CI.

**Completion conditions:**
- [x] `check_parity.py` calls `FeatureMapper.transform_training_units()` + `PredictorService.predict()`
- [x] `test_parity.py` updated: **FAILS** (not skips) when `pipeline.pkl` absent
- [x] `pipeline.pkl` and other artifacts committed to Git (removed from `.gitignore`)
- [x] Failing proof: `test_parity_failing_proof.py::test_parity_gate_fails_with_wrong_model` PASSED
- [x] Normal code passes: `[PARITY OK] pipeline.pkl and PredictorService produce identical outputs.`
- [ ] Green GitHub Actions run with parity test passing (not skipping)

**Status:** ⏳ PENDING CI — local tests pass, artifacts committed; CI result pending.

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

### CP9 — Invalid Input and Browser Validation

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

### CP10 — Windows Access Violation

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

**Root cause:** CPython 3.11 / Windows finalizer ordering issue in background thread during session teardown. Stack: `pluggy._hooks.__call__` → `pluggy._manager._hookexec` → `pytest.runner`. Not caused by application code. All 47 tests complete successfully. Not fixable without Python version upgrade.

---

### CP11 — Origin of the 1,000 Extra Rows

**Goal:** Find and document the source of the 1,000 additional rows, or write `origin unknown, excluded`. Extra rows must be excluded from default training and evaluation.

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

### CP12 — Data Audit and Model Card

**Goal:** Push audit scripts, correct misleading performance claims, report grouped accuracy.

**Completion conditions:**
- [x] `ml-training/audit/audit_data.py` committed and pushed (`09bacf8`)
- [x] `ml-training/audit/eval_sensitivity.py` committed and pushed (`57eedf3`)
- [x] `ml-training/check_parity.py` committed and pushed (`6ff64a5`)
- [x] `MODEL_CARD.md` updated: data quality section, grouped-accuracy table, unknown-origin rows correctly documented as excluded
- [x] No unsupported accuracy claim — the 92.5% old-model figure and 91.5% new-model figure have been **removed** from the fair-comparison section (replaced with a prose note + CAUTION callout)
- [x] Grouped accuracy explicitly reported: 0.188 ± 0.045 (grouped), 0.256 ± 0.058 (GroupKFold)
- [x] Data leakage / duplicate limitations documented
- [x] README.md updated with data notes and accuracy disclaimer
- [ ] Green CI run with all changes pushed

**Status:** ⏳ PENDING CI — local changes ready; MODEL_CARD.md 92.5%/91.5% removal committed in this session.

---

## M2 Progress Summary

| Checkpoint | Status | Commit | CI |
|---|---|---|---|
| 7 — Docker build & smoke test | ⏳ PENDING (image size + response from CI log) | 6bd837f | CI #9 green (owner confirmed) |
| 8 — Serving parity gate | ⏳ PENDING CI | 8382631/f627ff4 | pending |
| 9 — Invalid input + browser validation | 🔲 OPEN (owner browser check) | 85a6855 | pending |
| 10 — Windows access violation | ✅ DONE (local) | 6bd837f | N/A |
| 11 — Origin of 1,000 extra rows | ✅ DONE | 8382631/f627ff4 | pending |
| 12 — Data audit and model card | ⏳ PENDING CI | f627ff4 + this commit | pending |

---

## Phase: M3 — ML Evaluation (Checkpoints 13–18)

> M3 has NOT been started. All checkpoints below are ❌ NOT DONE.
> Do not start M3 until M2 is fully approved.

### CP13 — Cross-Validation and Overfitting Analysis

**Goal:** Run stratified k-fold cross-validation on the training set and report mean ± std accuracy. Demonstrate the model is not severely overfit.

**Status:** ❌ NOT DONE

---

### CP14 — Feature Importance Analysis

**Goal:** Extract and visualise Random Forest feature importances. Identify top-5 predictive features.

**Status:** ❌ NOT DONE

---

### CP15 — Confusion Matrix and Per-Class Metrics

**Goal:** Generate a full confusion matrix on the held-out test set. Report precision, recall and F1 per class.

**Status:** ❌ NOT DONE

---

### CP16 — Hyperparameter Tuning

**Goal:** Run a grid or random search over key Random Forest hyperparameters. Record best parameters and resulting test accuracy.

**Status:** ❌ NOT DONE

---

### CP17 — Alternative Model Comparison

**Goal:** Train at least one alternative model (e.g., Gradient Boosting, SVM). Compare test accuracy, inference latency, and grouped accuracy against the Random Forest baseline.

**Status:** ❌ NOT DONE

---

### CP18 — Model Versioning and Registry

**Goal:** Register the production Random Forest model in MLflow Model Registry. Tag it with version, training date, and evaluation metrics.

**Status:** ❌ NOT DONE

---

## Phase: P1–P3 Product (Checkpoints 19–23)

> Product phases P1–P3 have NOT been started. All checkpoints below are ❌ NOT DONE.

### CP19 — P1: User Authentication

**Goal:** Implement JWT-based authentication. Users can register, log in, and access protected endpoints.

**Status:** ❌ NOT DONE

---

### CP20 — P2: Resume Storage and History

**Goal:** Store uploaded resumes and prediction history per user. Users can view past predictions.

**Status:** ❌ NOT DONE

---

### CP21 — P2: Dashboard

**Goal:** Frontend dashboard showing prediction history, top-3 roles, and confidence scores over time.

**Status:** ❌ NOT DONE

---

### CP22 — P3: Career Pathway Recommendations

**Goal:** For the predicted top role, return a curated list of recommended skills, certifications, and job postings.

**Status:** ❌ NOT DONE

---

### CP23 — P3: Resume Gap Analysis

**Goal:** Compare the user's parsed resume features against the ideal feature profile for the predicted role. Report top gaps.

**Status:** ❌ NOT DONE

---

## Phase: M4 Approval and Deployment (Checkpoints 24–25)

> M4 has NOT been started. All checkpoints below are ❌ NOT DONE.

### CP24 — Staging Deployment

**Goal:** Deploy the full stack (backend + frontend) to a staging environment. All CI checks pass. End-to-end smoke test passes in staging.

**Status:** ❌ NOT DONE

---

### CP25 — Production Deployment and Owner Sign-off

**Goal:** Deploy to production. Owner reviews all documentation, MODEL_CARD.md, and CHECKPOINTS.md. Owner formally approves M4.

**Status:** ❌ NOT DONE

---

## Phase: P4 Agent (Checkpoints 26–28)

> P4 agent work has NOT been started. All checkpoints below are ❌ NOT DONE.

### CP26 — Agentic Career Advisor

**Goal:** Implement an LLM-backed agent that takes the predicted role and resume gaps as context and generates a personalised career roadmap.

**Status:** ❌ NOT DONE

---

### CP27 — Agent Tool Integration

**Goal:** Agent has access to job-search and course-recommendation tools. Tool outputs are grounded and cited.

**Status:** ❌ NOT DONE

---

### CP28 — Agent Evaluation

**Goal:** Evaluate agent response quality on a fixed set of test personas. Report relevance, groundedness, and coherence scores.

**Status:** ❌ NOT DONE

---

## Phase: M5 Monitoring (Checkpoints 29–30)

> M5 monitoring has NOT been started. All checkpoints below are ❌ NOT DONE.

### CP29 — Prediction Distribution Monitoring

**Goal:** Log incoming prediction requests (anonymised). Alert when prediction distribution drifts significantly from training distribution.

**Status:** ❌ NOT DONE

---

### CP30 — Model Performance Monitoring

**Goal:** Track model accuracy on labelled production feedback. Trigger retraining pipeline when accuracy drops below threshold.

**Status:** ❌ NOT DONE

---

## Stretch Goals (S1–S5)

> Stretch goals are ❌ NOT DONE. They may be attempted after M5 is complete.

### S1 — Multi-Language Resume Parsing

**Goal:** Resume parser handles resumes in at least French and Spanish in addition to English.

**Status:** ❌ NOT DONE

---

### S2 — Real-Time Salary Benchmarking

**Goal:** For the predicted role, return current median salary and salary range from a live API or curated dataset.

**Status:** ❌ NOT DONE

---

### S3 — Interview Question Generator

**Goal:** Agent generates 10 role-specific behavioural and technical interview questions based on the predicted career path.

**Status:** ❌ NOT DONE

---

### S4 — Automated MODEL_CARD Update

**Goal:** CI pipeline automatically updates `MODEL_CARD.md` evaluation metrics on every model retrain.

**Status:** ❌ NOT DONE

---

### S5 — Public API with Rate Limiting

**Goal:** Expose `/predict` as a public API with API-key authentication and per-key rate limiting.

**Status:** ❌ NOT DONE
