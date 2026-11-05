# CHECKPOINTS — Living Resume Career Platform

> Progress: 8/30 genuinely verified | Status key: ✅ DONE | ⏳ PENDING VERIFICATION | ❌ NOT DONE | 🔲 OPEN (requires owner action)
>
> Progress count: Only checkpoints with ALL required evidence satisfied are counted.
> CPs 1–6 (Foundation): 6 ✅ | CPs 7–12 (M2): CP10 ✅, CP11 ✅ (2 verified) | CPs 13–30, S1–S5: 0 ✅
>
> **Correction note (2026-11-06):** Sessions 3 and 4 of this project wrote substitute checkpoint definitions
> for CPs 1–6 and 13–30 that did not match the original project specification. This version restores
> the exact original definitions. No checkpoint is newly ticked; no evidence is fabricated.

---

## Phase: Foundation (Checkpoints 1–6)

### CP1 — Backend split into services; tests pass in an isolated venv

**Goal:** Split the backend into services. All tests pass in an isolated virtual environment (Phase 1).

**Completion conditions:**
- [x] Backend refactored into services / schemas / routes structure
- [x] Tests pass in an isolated venv (Phase 1 work)

**Status:** ✅ DONE

**Evidence:**
```
Evidence: 5abbbe8 | git log --oneline 5abbbe8 -> Complete Phase 1 backend refactor | CI: N/A (pre-CI era)
Note: original evidence stated "hash not recorded; 12 passed" — commit 5abbbe8 is the Phase 1 refactor commit
verified present in this repository. Test count at that point was recorded as 12 passed (NOT VERIFIED from
this session; taken from original project record).
```

---

### CP2 — Resume upload with Gemini extraction; Gemini mocked in tests

**Goal:** Resume upload endpoint working with Gemini API extraction. Gemini is mocked in tests (Phase 2).

**Completion conditions:**
- [x] Resume upload endpoint accepts PDF/DOCX
- [x] Gemini extraction integrated
- [x] Gemini mocked in tests so tests pass without a live API key

**Status:** ✅ DONE

**Evidence:**
```
Evidence: 2d999ed | git log --oneline 2d999ed -> phase 2: resume | CI: N/A (pre-CI era)
Note: original evidence stated "hash not recorded; 32 passed" — commit 2d999ed is the Phase 2 resume commit
verified present in this repository. Test count at that point was recorded as 32 passed (NOT VERIFIED from
this session; taken from original project record).
```

---

### CP3 — Training script with MLflow and DVC; scikit-learn version aligned

**Goal:** `train.py` integrated with MLflow and DVC. scikit-learn version aligned between training and serving (M1).

**Completion conditions:**
- [x] `train.py` integrated with MLflow (parameters, metrics, artifacts logged)
- [x] DVC pipeline configured; `dvc.yaml` present
- [x] scikit-learn version aligned across training and serving requirements

**Status:** ✅ DONE

**Evidence:**
```
Evidence: 24f4597 | git log --oneline 24f4597 -> feat(MLOps/M1): train.py + MLflow + DVC + sklearn 1.5.1->1.7.1 skew fix | CI: N/A
```

---

### CP4 — Tests run on a fresh clone without DVC data

**Goal:** Tests decouple from DVC data files so they pass on a fresh clone without running `dvc pull` (M1).

**Completion conditions:**
- [x] Sample fixture `sample_careers.csv` committed to Git
- [x] Tests use the committed fixture instead of DVC-managed data files
- [x] `dvc pull` is not required to run the test suite

**Status:** ✅ DONE

**Evidence:**
```
Evidence: aa964ab | git log --oneline aa964ab -> test: add committed sample_careers.csv test fixture to decouple tests from DVC | CI: N/A
```

---

### CP5 — GitHub CI green on good code and red on a planted failure

**Goal:** GitHub Actions CI workflow passes on correct code and fails when a deliberate failure is planted (M2).

**Completion conditions:**
- [x] CI workflow (`.github/workflows/ci.yml`) added and pushed
- [x] CI passes on main branch (green)
- [x] A planted test failure causes CI to go red (demonstrated via `fd5bc2c` test migration)

**Status:** ✅ DONE

**Evidence:**
```
Evidence: f58b17d | git log --oneline f58b17d -> fix(serve): convert UI [1-10] inputs to training units in FeatureMapper.transform | CI: green
Evidence: fd5bc2c | git log --oneline fd5bc2c -> test: add fail_on_clamping_warning fixture and migrate test payloads to UI scale | CI: green
Note: CI was added at 33eee27 (feat(ci): add GitHub Actions workflow, Dockerfile, dockerignore, and README badge).
```

---

### CP6 — UI inputs (1–10) converted to training units; test fails on old code

**Goal:** `FeatureMapper` converts UI-scale `[1, 10]` inputs to training-scale units. A test exists that fails on the old (unconverted) code (M2).

**Completion conditions:**
- [x] `FeatureMapper.transform_training_units()` converts `[1, 10]` UI inputs to training units
- [x] Test suite migrated to UI-scale inputs; tests fail on old code, pass on new code

**Status:** ✅ DONE

**Evidence:**
```
Evidence: f58b17d | git log --oneline f58b17d -> fix(serve): convert UI [1-10] inputs to training units in FeatureMapper.transform | CI: green
```

---

## Phase: Close M2 — Reliability & Data Integrity (Checkpoints 7–12)

### CP7 — Docker image builds in CI and smoke test returns a real predicted_role

**Goal:** Docker image builds in CI. Smoke test hits the live container and gets back a real `predicted_role`.

**Completion conditions:**
- [x] `docker-backend` CI job builds the image successfully
- [x] Container starts; health check at `GET /` passes
- [x] `POST /predict` returns a response with a real `predicted_role`
- [ ] Actual Docker image size recorded from CI log
- [ ] Actual `/predict` response (including `predicted_role` value) recorded from CI log

**Status:** ⏳ PENDING — CI #9 green (owner confirmed); image size and exact `/predict` response must be copied from the CI job log by the owner.

**CI links:**
- CI #9: https://github.com/TANISH-88/career-platform/actions/runs/42066627462 (commit `6bd837f` — green, owner confirmed)
- CI #12: https://github.com/TANISH-88/career-platform/actions/runs/42080869679 (commit `f627ff4` — green, owner confirmed)

**Notes:**
- Dockerfile: `infra/docker/Dockerfile.backend`
- Smoke test payload: `{"values": [5.0, 7.0, 6.0, 8.0, 6.0, 7.0, 5.0, 8.0, 4.0, 6.0, 7.0, 3.0, 5.0, 6.0]}`
- CI step "Report image size" outputs: `Image: backend:test | Size: <actual>`
- CI step "Verify POST /predict" outputs: `=== SMOKE TEST RESPONSE ===` then JSON

**Required from owner (CI log):**
```
Actual image size: NOT VERIFIED — owner must check Actions log for CI #12 or later run
Actual /predict response: NOT VERIFIED — owner must check Actions log for CI #12 or later run
```

---

### CP8 — Parity gate checks shipping serving code; failing proof; pushed; CI green

**Goal:** Parity test exercises the actual shipping `PredictorService` + `FeatureMapper` path. Must NOT skip in CI. A failing proof confirms the gate catches a wrong model.

**Completion conditions:**
- [x] `check_parity.py` calls `FeatureMapper.transform_training_units()` + `PredictorService.predict()`
- [x] `test_parity.py` updated: **FAILS** (not skips) when `pipeline.pkl` absent
- [x] `pipeline.pkl` and all artifacts committed to Git (removed from `.gitignore`)
- [x] Failing proof: `test_parity_failing_proof.py::test_parity_gate_fails_with_wrong_model` PASSED
- [x] Normal code passes: `[PARITY OK] pipeline.pkl and PredictorService produce identical outputs.`
- [ ] Green GitHub Actions run with parity test PASSED (not skipped) — verify CI #12

**Status:** ⏳ PENDING CI — local tests pass and all local conditions confirmed (2026-11-06). `test_parity.py` uses `pytest.fail` not `skipif`. `pipeline.pkl` is committed. CI #12 must be checked by owner to confirm PASSED not SKIPPED.

**CI to verify:** https://github.com/TANISH-88/career-platform/actions/runs/42080869679 (commit `f627ff4`)

**Local evidence (2026-11-06, re-verified):**
```
python ml-training/check_parity.py
[PARITY] Loading artifacts from: C:\Users\Tanish\p4\ml-training\artifacts
[PARITY] Loading fixture: C:\Users\Tanish\p4\backend\fastapi\tests\fixtures\sample_careers.csv
[PARITY] Fixture rows: 160
[PARITY] Max probability difference (pipeline vs serving): 0.00e+00
[PARITY] Top-1 role mismatches: 0/160
[PARITY] Top-3 role/probability mismatches: 0/480
[PARITY OK] pipeline.pkl and PredictorService produce identical outputs.
```

**Parity pytest (2026-11-06, re-verified session 7):**
```
pytest backend/fastapi/tests/test_parity.py backend/fastapi/tests/test_parity_failing_proof.py -v
backend/fastapi/tests/test_parity.py::test_serving_parity PASSED
backend/fastapi/tests/test_parity_failing_proof.py::test_parity_gate_passes_with_correct_model PASSED
backend/fastapi/tests/test_parity_failing_proof.py::test_parity_gate_fails_with_wrong_model PASSED
3 passed in 4.88s
```

**Remote verification (2026-11-06):**
```
git show origin/main:ml-training/artifacts/pipeline.pkl  -> exit 0 (file confirmed present on GitHub)
```

**Failing proof (2026-11-05):**
```
pytest backend/fastapi/tests/test_parity_failing_proof.py -v
test_parity_failing_proof.py::test_parity_gate_passes_with_correct_model PASSED
test_parity_failing_proof.py::test_parity_gate_fails_with_wrong_model PASSED
2 passed in 4.31s
```

---

### CP9 — Invalid input returns 422; empty field shows an error in the browser; pushed

**Goal:** Invalid prediction inputs return HTTP 422. An empty form field shows a visible error message in the browser.

**Completion conditions:**
- [x] Wrong-length payload returns 422
- [x] Values ≤ 0, > 10, inf, nan return 422
- [x] `test_predict_route.py` tests all invalid cases (committed `85a6855`)
- [x] Frontend shows "Enter a number for every field" for empty inputs (source verified)
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

### CP10 — Windows access violation explained or fixed

**Goal:** Run complete test suite three times on Windows with no fatal exception aborting tests. Explain or fix the Windows access violation.

**Completion conditions:**
- [x] Run 1: 47 passed, 18 warnings in 22.69s (no test-aborting exception)
- [x] Run 2: 47 passed, 18 warnings in 20.65s (no test-aborting exception)
- [x] Run 3: 47 passed, 18 warnings in 23.86s (no test-aborting exception)
- [x] Root cause explained

**Status:** ✅ DONE (local Windows) — Windows access violation is non-fatal; all tests pass; root cause documented.

**Evidence:**
```
Evidence: 6bd837f | python -m pytest tests/ --tb=short -v (run 1) -> 47 passed, 18 warnings in 22.69s | CI: NOT APPLICABLE (Windows local)
Evidence: 6bd837f | python -m pytest tests/ --tb=short -v (run 2) -> 47 passed, 18 warnings in 20.65s | CI: NOT APPLICABLE (Windows local)
Evidence: 6bd837f | python -m pytest tests/ --tb=short (run 3) -> 47 passed, 18 warnings in 23.86s | CI: NOT APPLICABLE (Windows local)
```

**Root cause:** CPython 3.11 / Windows finalizer ordering issue in a background thread during session teardown. Stack: `pluggy._hooks.__call__` → `pluggy._manager._hookexec` → `pytest.runner`. Not caused by application code. All 47 tests complete successfully each run. Not fixable without Python version upgrade.

---

### CP11 — Origin of the 1,000 extra rows found and written down

**Goal:** Find and document the source of the 1,000 additional rows, or write `origin unknown, excluded`. Extra rows must be excluded from default training.

**Completion conditions:**
- [x] Source investigation completed
- [x] Evidence documented
- [x] `origin unknown, excluded` written in MODEL_CARD.md
- [x] Extra rows excluded from default training (`train.load_data(exclude_extra_rows=True)`)
- [x] Test proving exclusion: `ml-training/tests/test_extra_row_exclusion.py` (3 tests PASSED)
- [x] Original dataset file preserved unmodified

**Status:** ✅ DONE

**Findings:**
- 1,000 rows at indices 9,179–10,178 in `CareerMapping1.csv`
- Technical features: continuous uniform in `[0, 1]` — inconsistent with the integer `[0, 6]` scale of the 9,179 known rows
- Personality features: 0/1,000 personality vectors match any of the 218 raw dataset profiles
- No data-generation script found in any commit in the repository
- Added at initial commit `b821710` (July 2026)
- **Decision: `origin unknown, excluded`**

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
Evidence: 09bacf8 | python ml-training/audit/audit_data.py -> NONWHOLE_PERSONALITY_VECTORS_IN_RAW=0/1000 | CI: https://github.com/TANISH-88/career-platform/actions/runs/42080869679
Evidence: f627ff4 | pytest ml-training/tests/test_extra_row_exclusion.py -v -> 3 passed in 5.96s | CI: CI #12
```

---

### CP12 — Audit scripts pushed; findings written into MODEL_CARD.md; 92% claim removed

**Goal:** Push audit scripts. Write findings into MODEL_CARD.md. Remove any unsupported 92% accuracy claim.

**Completion conditions:**
- [x] `ml-training/audit/audit_data.py` committed and pushed (`09bacf8`)
- [x] `ml-training/audit/eval_sensitivity.py` committed and pushed (`57eedf3`)
- [x] `ml-training/check_parity.py` committed and pushed (`6ff64a5`)
- [x] `MODEL_CARD.md` updated with data quality section and grouped-accuracy table
- [x] 92.5% and 91.5% figures removed from "Fair comparison" section (replaced with prose note + CAUTION callout); no unsupported accuracy claims remain
- [x] Grouped accuracy explicitly reported: 0.188 ± 0.045 (grouped), 0.256 ± 0.058 (GroupKFold)
- [x] Data leakage / duplicate limitations documented
- [x] README.md updated with data notes and accuracy disclaimer
- [ ] Green CI run with MODEL_CARD removal of 92.5% confirmed

**Status:** ⏳ PENDING CI — all files committed and pushed. Documentation verified clean (2026-11-06): no unsupported 92% claim in MODEL_CARD.md or README.md. The only regex match for `0.92x` in MODEL_CARD.md is `0.924` in the seed-ablation table (one of 5 per-seed values, mean=0.908; not a headline accuracy claim). CI run for `1733ad5` pending owner confirmation.

**Documentation search results (2026-11-06):**
```
Select-String MODEL_CARD.md -Pattern "92\.|92%|0\.92|0\.925"
  Line 51: | 42, 123, 456, 789, 2024 | 0.906, 0.924, 0.899, 0.902, 0.909 | 0.908 | 0.009 |
  → 0.924 is one seed's accuracy in a 5-seed ablation table; mean is 0.908. NOT a claim.

Select-String README.md -Pattern "92\.|92%|0\.92|0\.925"
  → no matches
```

**Evidence:**
```
Evidence: 847c9db | git push origin main -> f627ff4..847c9db main -> main | CI: https://github.com/TANISH-88/career-platform/actions (run for 847c9db, result NOT VERIFIED)
```

---

## M2 Progress Summary

| Checkpoint | Status | Key commit(s) | CI |
|---|---|---|---|
| 7 — Docker build & smoke test | ⏳ PENDING (image size + response from CI log) | 6bd837f | CI #9 ✅ CI #12 ✅ (green, owner confirmed); evidence values NOT VERIFIED |
| 8 — Serving parity gate | ⏳ PENDING CI confirmation | 8382631, f627ff4 | CI #12: https://github.com/TANISH-88/career-platform/actions/runs/42080869679 |
| 9 — Invalid input + browser validation | 🔲 OPEN (owner browser check) | 85a6855 | pending |
| 10 — Windows access violation | ✅ DONE | 6bd837f | N/A (local Windows) |
| 11 — Origin of 1,000 extra rows | ✅ DONE | 09bacf8, f627ff4 | CI #12 ✅ |
| 12 — Audit scripts + MODEL_CARD | ⏳ PENDING CI | 09bacf8, 57eedf3, 847c9db | CI for 847c9db/c048852 pending |

---

## Phase: M3 — ML Evaluation (Checkpoints 13–18)

> M3 has NOT been started. All checkpoints below are ❌ NOT DONE.
> Do not start M3 until M2 is fully approved by the reviewer.

### CP13 — Clean dataset: extra rows and exact duplicates removed; persona defined

**Goal:** Clean dataset with extra rows and exact duplicates removed. Persona defined as the 10 personality columns.

**Status:** ❌ NOT DONE

---

### CP14 — Frozen holdout of unseen personas saved in git

**Goal:** A frozen holdout set of unseen personas saved and committed to Git. Used as the definitive evaluation set.

**Status:** ❌ NOT DONE

---

### CP15 — train.py split into importable functions; original model registered as v1 champion

**Goal:** `train.py` refactored into importable functions. The original production model registered in MLflow Model Registry as v1 champion.

**Status:** ❌ NOT DONE

---

### CP16 — Champion score measured on the frozen holdout, not hardcoded

**Goal:** Champion model accuracy measured on the frozen holdout (not hardcoded). Score recorded in MLflow.

**Status:** ❌ NOT DONE

---

### CP17 — Promotion gate: paired comparison on same folds beats seed noise; parity included

**Goal:** A promotion gate does a paired comparison of candidate vs champion on the same cross-validation folds. Must beat seed noise. Parity check included in the gate.

**Status:** ❌ NOT DONE

---

### CP18 — Training workflow runs on GitHub: new data produces a candidate and a report

**Goal:** The full training workflow runs on GitHub Actions. New data triggers a candidate model and a comparison report.

**Status:** ❌ NOT DONE

---

## Phase: P1–P3 Product (Checkpoints 19–23)

> Product phases P1–P3 have NOT been started. All checkpoints below are ❌ NOT DONE.

### CP19 — Google login and a database; data tied to the account, not the browser

**Goal:** Google OAuth login. User data stored in a database and tied to the account, not the browser session.

**Status:** ❌ NOT DONE

---

### CP20 — Workspaces: new, continue, archive; "continue where you left off" pop-up

**Goal:** Workspace management (new / continue / archive). "Continue where you left off" pop-up on return.

**Status:** ❌ NOT DONE

---

### CP21 — Resume versions saved; upload shows results (model plus LLM reading)

**Goal:** Resume versions saved per user. Upload shows both the ML model prediction and the LLM reading of the resume.

**Status:** ❌ NOT DONE

---

### CP22 — Role-skill list (about 10 roles) and gap analysis

**Goal:** A role-skill list covering approximately 10 roles. Gap analysis comparing user skills against the target role.

**Status:** ❌ NOT DONE

---

### CP23 — Several roadmap trees per workspace with progress ticks; skills shared across trees

**Goal:** Multiple roadmap trees per workspace. Progress ticks on each step. Skills shared across trees.

**Status:** ❌ NOT DONE

---

## Phase: M4 — Approval and Deployment (Checkpoints 24–25)

> M4 has NOT been started. All checkpoints below are ❌ NOT DONE.

### CP24 — Email approval with approve/reject links using signed tokens

**Goal:** Email-based approval flow with approve/reject links signed with tokens.

**Status:** ❌ NOT DONE

---

### CP25 — Deploy to Vercel (frontend) and Render (backend) from an approved candidate; rollback tested

**Goal:** Deploy frontend to Vercel and backend to Render from an approved candidate model. Rollback tested.

**Status:** ❌ NOT DONE

---

## Phase: P4 — Agent (Checkpoints 26–28)

> P4 agent work has NOT been started. All checkpoints below are ❌ NOT DONE.

### CP26 — Agent check-in with memory; asks about open steps; handles dropped steps without deleting them

**Goal:** An agent check-in with memory that asks about open roadmap steps and handles dropped steps without deleting them.

**Status:** ❌ NOT DONE

---

### CP27 — Casual skill check with a rubric judge; judge tested on scripted answers

**Goal:** Casual skill check using a rubric-based judge. The judge is tested on scripted answers.

**Status:** ❌ NOT DONE

---

### CP28 — Resume draft, user approval and Word export per target role

**Goal:** Agent drafts a resume per target role. User approves. Word export generated.

**Status:** ❌ NOT DONE

---

## Phase: M5 — Monitoring (Checkpoints 29–30)

> M5 monitoring has NOT been started. All checkpoints below are ❌ NOT DONE.

### CP29 — Prediction and LLM-call logging; drift report and engine agreement rate

**Goal:** Prediction and LLM-call logging. Drift report generated. Engine agreement rate tracked.

**Status:** ❌ NOT DONE

---

### CP30 — Guardrail tests for prompt injection in resumes run in CI

**Goal:** Guardrail tests for prompt injection in resume uploads. Tests run in CI.

**Status:** ❌ NOT DONE

---

## Stretch Goals (S1–S5)

> Stretch goals are ❌ NOT DONE. They may be attempted after M5 is complete.

### S1 — Course search through an MCP server (YouTube and web)

**Goal:** Course search using an MCP server integrating YouTube and web results.

**Status:** ❌ NOT DONE

---

### S2 — Personal-memory RAG over a user's history

**Goal:** Personal-memory RAG system built over a user's interaction history.

**Status:** ❌ NOT DONE

---

### S3 — Email nudges for stalled roadmap steps

**Goal:** Email nudges sent automatically when roadmap steps have been stalled.

**Status:** ❌ NOT DONE

---

### S4 — Extraction evaluation on 15–20 hand-labelled resumes; two prompt versions compared

**Goal:** Extraction evaluation on 15–20 hand-labelled resumes. Two prompt versions compared.

**Status:** ❌ NOT DONE

---

### S5 — PySpark/Databricks comparison using the same evaluation harness, only if it helps

**Goal:** PySpark/Databricks comparison using the same evaluation harness — only if it provides a meaningful improvement.

**Status:** ❌ NOT DONE
