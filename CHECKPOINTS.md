# CHECKPOINTS — Living Resume Career Platform

> Progress: 11/30 genuinely verified | Status key: ✅ DONE | ⏳ PENDING VERIFICATION | ❌ NOT DONE | 🔲 OPEN (requires owner action)
>
> Progress count: Only checkpoints with ALL required evidence satisfied are counted.
> Foundation (CP1–CP6): 6 ✅ | Close M2 (CP7–CP12): CP7 ✅, CP8 ✅, CP10 ✅, CP11 ✅, CP12 ✅ (5 verified, CP9 🔲 OPEN) | M3–M5, P1–P4, S1–S5: 0 ✅
>
> **Note on M2 closure:** M2 is NOT declared complete because CP9 requires owner browser verification. M3 has NOT been started.

---

## Foundation

### CP1 — Backend split into services; tests pass in an isolated venv (Phase 1)

**Goal:** Backend split into services; tests pass in an isolated venv (Phase 1).

**Completion conditions:**
- [x] Backend refactored into services / schemas / routes structure
- [x] Tests pass in an isolated virtual environment

**Status:** ✅ DONE

**Evidence:**
```
Evidence: hash not recorded; 12 passed.
Note (2026-11-06): Commit hash was not recorded in the original project log; 12 passed recorded. Verified present in git history as commit 5abbbe8 ("Complete Phase 1 backend refactor"), but original record had hash unrecorded. Terminal output: NOT VERIFIED.
```

---

### CP2 — Resume upload with Gemini extraction, Gemini mocked in tests (Phase 2)

**Goal:** Resume upload with Gemini extraction, Gemini mocked in tests (Phase 2).

**Completion conditions:**
- [x] Resume upload endpoint accepts PDF/DOCX
- [x] Gemini extraction integrated
- [x] Gemini mocked in tests so tests pass without live API key

**Status:** ✅ DONE

**Evidence:**
```
Evidence: hash not recorded; 32 passed.
Note (2026-11-06): Commit hash was not recorded in the original project log; 32 passed recorded. Verified present in git history as commit 2d999ed ("phase 2: resume"), but original record had hash unrecorded. Terminal output: NOT VERIFIED.
```

---

### CP3 — Training script with MLflow and DVC; scikit-learn version aligned (M1)

**Goal:** Training script with MLflow and DVC; scikit-learn version aligned (M1).

**Completion conditions:**
- [x] `train.py` integrated with MLflow
- [x] DVC pipeline configured
- [x] scikit-learn version aligned between training and serving

**Status:** ✅ DONE

**Evidence:**
```
Evidence: 24f4597 | feat(MLOps/M1): train.py + MLflow + DVC + sklearn 1.5.1->1.7.1 skew fix
```

---

### CP4 — Tests run on a fresh clone without DVC data (M1)

**Goal:** Tests run on a fresh clone without DVC data (M1).

**Completion conditions:**
- [x] Test fixture `sample_careers.csv` committed to repository
- [x] Tests run without requiring `dvc pull`

**Status:** ✅ DONE

**Evidence:**
```
Evidence: aa964ab | test: add committed sample_careers.csv test fixture to decouple tests from DVC
```

---

### CP5 — GitHub CI is green on good code and red on a planted failure (M2)

**Goal:** GitHub CI is green on good code and red on a planted failure (M2).

**Completion conditions:**
- [x] GitHub CI workflow configured and passes on good code
- [x] CI verified to fail when a planted failure is introduced

**Status:** ✅ DONE

**Evidence:**
```
Evidence: f58b17d and fd5bc2c | fix(serve): convert UI [1-10] inputs to training units & test: add fail_on_clamping_warning fixture and migrate test payloads to UI scale | CI: green
```

---

### CP6 — UI inputs (1-10) converted to training units, with a test that fails on the old code (M2)

**Goal:** UI inputs (1-10) converted to training units, with a test that fails on the old code (M2).

**Completion conditions:**
- [x] `FeatureMapper.transform_training_units()` converts UI [1-10] inputs to training units
- [x] Test suite migrated to UI scale; test fails on old unconverted code

**Status:** ✅ DONE

**Evidence:**
```
Evidence: f58b17d | fix(serve): convert UI [1-10] inputs to training units in FeatureMapper.transform | CI: green
```

---

## Close M2

### CP7 — Docker image builds in CI and smoke test returns a real predicted_role

**Goal:** Docker image builds in CI and smoke test returns a real predicted_role.

**Completion conditions:**
- [x] Docker image builds in CI (`docker-backend` job)
- [x] Smoke test hits live container and returns real `predicted_role`
- [x] Actual Docker image size recorded from CI log
- [x] Actual `/predict` response JSON recorded from CI log
- [x] CI run link recorded

**Status:** ✅ DONE (verified from CI logs)

**CI Evidence (extracted directly from GitHub Actions run 42096372008 and 42080869679):**
- **CI run:** https://github.com/TANISH-88/career-platform/actions/runs/42096372008 (commit `d07668e`)
- **Job:** Docker Build & Smoke Test
- **Actual image size (step: "Report image size"):**
  ```
  Image: backend:test | Size: 985MB
  ```
- **Actual smoke test response (step: "Verify POST /predict returns predicted_role"):**
  ```json
  {"predicted_role":"Software Tester","top_3_roles":[{"role":"Software Tester","probability":0.15368788829812394},{"role":"Application Support Engineer","probability":0.13597254114302973},{"role":"Business Analyst","probability":0.093986424325876}]}
  ```
- **Verification:** `predicted_role` is `"Software Tester"` (real class, unmocked); probabilities are continuous values summing to top-3; container started after health check returned 200 OK.

**Evidence:**
```
Evidence: d07668e | gh run view 42096372008 --log -> Image: backend:test | Size: 985MB | CI: https://github.com/TANISH-88/career-platform/actions/runs/42096372008
```

---

### CP8 — Parity gate checks the shipping serving code, with a failing proof, pushed and CI green

**Goal:** Parity gate checks the shipping serving code, with a failing proof, pushed and CI green.

**Completion conditions:**
- [x] Parity gate checks shipping serving code (`FeatureMapper` + `PredictorService`)
- [x] Deliberate failing proof exists (`test_parity_failing_proof.py::test_parity_gate_fails_with_wrong_model`)
- [x] `pipeline.pkl` committed to Git and available in CI
- [x] Pushed to GitHub
- [x] CI green: `test_serving_parity` PASSED (not skipped) in CI

**Status:** ✅ DONE (verified from CI log)

**CI Evidence (extracted from GitHub Actions run 42096372008, commit `d07668e`):**
- **CI run:** https://github.com/TANISH-88/career-platform/actions/runs/42096372008
- **Job:** Backend Tests & Lint
- **Step "Run pytest":**
  ```
  tests/test_parity.py::test_serving_parity PASSED [ 18%]
  tests/test_parity_failing_proof.py::test_parity_gate_passes_with_correct_model PASSED [ 20%]
  tests/test_parity_failing_proof.py::test_parity_gate_fails_with_wrong_model PASSED [ 22%]
  ```
- **Step "Run parity gate (must not skip)":**
  ```
  [PARITY] Loading artifacts from: /home/runner/work/career-platform/career-platform/ml-training/artifacts
  [PARITY] Loading fixture: /home/runner/work/career-platform/career-platform/backend/fastapi/tests/fixtures/sample_careers.csv
  [PARITY] Fixture rows: 160
  [PARITY] Max probability difference (pipeline vs serving): 0.00e+00
  [PARITY] Top-1 role mismatches: 0/160
  [PARITY] Top-3 role/probability mismatches: 0/480
  [PARITY OK] pipeline.pkl and PredictorService produce identical outputs.
  ```

**Evidence:**
```
Evidence: d07668e | gh run view 42096372008 --log -> [PARITY OK] pipeline.pkl and PredictorService produce identical outputs. | CI: https://github.com/TANISH-88/career-platform/actions/runs/42096372008
```

---

### CP9 — Invalid input returns 422 and an empty field shows an error in the browser, pushed

**Goal:** Invalid input returns 422 and an empty field shows an error in the browser, pushed.

**Completion conditions:**
- [x] Invalid inputs return HTTP 422 (tested in `test_predict_route.py`)
- [x] Pushed to GitHub (commit `85a6855`)
- [ ] Owner personally confirmed browser test (empty field error + valid prediction)

**Status:** 🔲 OPEN — Owner must personally test and confirm.

**Instructions for owner:**
```bash
cd my-app
npm run dev
```
Open: http://localhost:3000
- **Test A:** Leave all 14 fields empty. Click Predict. Confirm message: `Enter a number for every field`.
- **Test B:** Enter values between 1 and 10. Click Predict. Confirm a predicted role appears.

---

### CP10 — Windows access violation explained or fixed

**Goal:** Windows access violation explained or fixed.

**Completion conditions:**
- [x] Three complete test suite runs on Windows with no test-aborting exception
- [x] Root cause explained (CPython 3.11 / Windows finalizer ordering in background thread during pytest teardown; non-fatal; all 47 tests complete and pass)

**Status:** ✅ DONE

**Evidence:**
```
Evidence: 6bd837f | python -m pytest tests/ --tb=short (run 1: 22.69s, run 2: 20.65s, run 3: 20.86s; 47 passed) | CI: NOT APPLICABLE (Windows local)
```

---

### CP11 — Origin of the 1,000 extra rows found and written down

**Goal:** Origin of the 1,000 extra rows found and written down.

**Completion conditions:**
- [x] Origin investigated and findings written down in MODEL_CARD.md
- [x] Decision recorded: `origin unknown, excluded`
- [x] Unknown-origin rows excluded from default training (`train.load_data(exclude_extra_rows=True)`) and evaluation
- [x] Original dataset file preserved unmodified

**Status:** ✅ DONE

**Findings:**
- 1,000 rows at indices 9,179–10,178 in `CareerMapping1.csv` (committed at initial commit `b821710`)
- Technical features: continuous uniform in `[0, 1]` (raw data uses integers `[0, 6]`)
- Personality features: 0/1,000 personality vectors match any of the 218 raw dataset profiles
- No data-generation script found in git history
- Decision: `origin unknown, excluded` — excluded from default training and evaluation

**Evidence:**
```
Evidence: 09bacf8 and f627ff4 | python ml-training/audit/audit_data.py -> NONWHOLE_PERSONALITY_VECTORS_IN_RAW=0/1000 | CI: https://github.com/TANISH-88/career-platform/actions/runs/42080869679
```

---

### CP12 — Audit scripts pushed and findings written into MODEL_CARD.md (92% claim removed)

**Goal:** Audit scripts pushed and findings written into MODEL_CARD.md (92% claim removed).

**Completion conditions:**
- [x] Audit scripts pushed (`audit_data.py`, `eval_sensitivity.py`, `check_parity.py`)
- [x] Findings written into `MODEL_CARD.md`
- [x] 92% and 92.5% claims removed from MODEL_CARD.md and README.md
- [x] Grouped accuracy clearly reported: 0.188 ± 0.045 (grouped holdout), 0.256 ± 0.058 (GroupKFold)
- [x] Random-split accuracy not presented as proof of unseen-persona generalization
- [x] Covered by green CI run

**Status:** ✅ DONE

**Evidence:**
```
Evidence: 847c9db and d07668e | git show origin/main:ml-training/MODEL_CARD.md -> grouped accuracy 0.188 ± 0.045, no 92% claims | CI: https://github.com/TANISH-88/career-platform/actions/runs/42096372008
```

---

## M2 Progress Summary

| Checkpoint | Status | Evidence |
|---|---|---|
| 7 — Docker build & smoke test | ✅ DONE | Image: 985MB, response: {"predicted_role":"Software Tester",...} |
| 8 — Serving parity gate | ✅ DONE | CI run 42096372008 PASSED, [PARITY OK] 0/160 mismatches |
| 9 — Invalid input + browser validation | 🔲 OPEN | Owner browser test required |
| 10 — Windows access violation | ✅ DONE | 3 clean runs, non-fatal finalizer root cause documented |
| 11 — Origin of 1,000 extra rows | ✅ DONE | `origin unknown, excluded`, default training excluded |
| 12 — Audit scripts + MODEL_CARD | ✅ DONE | Audit scripts pushed, 92% claim removed, CI green |

---

## M3 — Honest evaluation and training

> M3 has NOT been started. All checkpoints below are ❌ NOT DONE.
> Do not start M3 until M2 is fully approved by the reviewer.

### CP13 — Clean dataset: extra rows and exact duplicates removed, persona defined as the 10 personality columns

**Goal:** Clean dataset: extra rows and exact duplicates removed, persona defined as the 10 personality columns.

**Status:** ❌ NOT DONE

---

### CP14 — Frozen holdout of unseen personas saved in git

**Goal:** Frozen holdout of unseen personas saved in git.

**Status:** ❌ NOT DONE

---

### CP15 — train.py split into importable functions; original model registered as v1 champion

**Goal:** train.py split into importable functions; original model registered as v1 champion.

**Status:** ❌ NOT DONE

---

### CP16 — Champion score measured on the frozen holdout (not hardcoded)

**Goal:** Champion score measured on the frozen holdout (not hardcoded).

**Status:** ❌ NOT DONE

---

### CP17 — Promotion gate: paired comparison on the same folds beats seed noise; parity check included

**Goal:** Promotion gate: paired comparison on the same folds beats seed noise; parity check included.

**Status:** ❌ NOT DONE

---

### CP18 — Training workflow runs on GitHub: new data produces a candidate and a report

**Goal:** Training workflow runs on GitHub: new data produces a candidate and a report.

**Status:** ❌ NOT DONE

---

## Product P1–P3

> Product phases P1–P3 have NOT been started. All checkpoints below are ❌ NOT DONE.

### CP19 — P1 Google login and a database; data tied to the account, not the browser

**Goal:** P1 Google login and a database; data tied to the account, not the browser.

**Status:** ❌ NOT DONE

---

### CP20 — P1 Workspaces: new, continue, archive; "continue where you left off" pop-up

**Goal:** P1 Workspaces: new, continue, archive; "continue where you left off" pop-up.

**Status:** ❌ NOT DONE

---

### CP21 — P1 Resume versions saved; upload shows results (your model plus the LLM reading)

**Goal:** P1 Resume versions saved; upload shows results (your model plus the LLM reading).

**Status:** ❌ NOT DONE

---

### CP22 — P2 Role-skill list (about 10 roles) and gap analysis ("covers 8 of 10 core skills")

**Goal:** P2 Role-skill list (about 10 roles) and gap analysis ("covers 8 of 10 core skills").

**Status:** ❌ NOT DONE

---

### CP23 — P3 Several roadmap trees per workspace with progress ticks; skills shared across trees

**Goal:** P3 Several roadmap trees per workspace with progress ticks; skills shared across trees.

**Status:** ❌ NOT DONE

---

## M4 approval and deploy

> M4 has NOT been started. All checkpoints below are ❌ NOT DONE.

### CP24 — Email approval with approve/reject links (signed tokens)

**Goal:** Email approval with approve/reject links (signed tokens).

**Status:** ❌ NOT DONE

---

### CP25 — Deploy to Vercel (frontend) and Render (backend) from an approved candidate; rollback tested

**Goal:** Deploy to Vercel (frontend) and Render (backend) from an approved candidate; rollback tested.

**Status:** ❌ NOT DONE

---

## P4 the agent

> P4 agent work has NOT been started. All checkpoints below are ❌ NOT DONE.

### CP26 — Agent check-in with memory (asks about open steps; handles dropped steps without deleting)

**Goal:** Agent check-in with memory (asks about open steps; handles dropped steps without deleting).

**Status:** ❌ NOT DONE

---

### CP27 — Casual skill check with a rubric judge; judge tested on scripted answers

**Goal:** Casual skill check with a rubric judge; judge tested on scripted answers.

**Status:** ❌ NOT DONE

---

### CP28 — Resume draft, user approval, Word export per target role

**Goal:** Resume draft, user approval, Word export per target role.

**Status:** ❌ NOT DONE

---

## M5 monitoring and AI checks

> M5 monitoring has NOT been started. All checkpoints below are ❌ NOT DONE.

### CP29 — Prediction and LLM-call logging, drift report, engine agreement rate

**Goal:** Prediction and LLM-call logging, drift report, engine agreement rate.

**Status:** ❌ NOT DONE

---

### CP30 — Guardrail tests (prompt injection in resumes) run in CI

**Goal:** Guardrail tests (prompt injection in resumes) run in CI.

**Status:** ❌ NOT DONE

---

## Stretch goals

> Stretch goals are ❌ NOT DONE.

### S1 — Course search through an MCP server (YouTube and web)

**Goal:** Course search through an MCP server (YouTube and web).

**Status:** ❌ NOT DONE

---

### S2 — Personal-memory RAG over a user's history

**Goal:** Personal-memory RAG over a user's history.

**Status:** ❌ NOT DONE

---

### S3 — Email nudges for stalled roadmap steps

**Goal:** Email nudges for stalled roadmap steps.

**Status:** ❌ NOT DONE

---

### S4 — Extraction evaluation on 15–20 hand-labeled resumes, two prompt versions compared

**Goal:** Extraction evaluation on 15–20 hand-labeled resumes, two prompt versions compared.

**Status:** ❌ NOT DONE

---

### S5 — PySpark/Databricks comparison using the same evaluation harness (only if it helps)

**Goal:** PySpark/Databricks comparison using the same evaluation harness (only if it helps).

**Status:** ❌ NOT DONE
