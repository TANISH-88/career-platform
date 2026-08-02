# Implementation Plan: Resume Upload & Skill Extraction (Phase 2)

## Overview

Phase 2 adds resume-based auto-fill to the Career Prediction Platform.
The implementation is strictly additive: new files are created, and three existing files
receive minimal, surgical additions. A pre-existing typo in `Features.jsx` is fixed first
because it silently corrupts every prediction payload.

## Tasks

- [x] 1. [BUG FIX] Fix conscientiousness spelling in `Features.jsx`
  - In `my-app/app/components/Features.jsx`, inside the `other_features` array, change:
    - `name: 'Conscientousness'` → `name: 'Conscientiousness'`
    - `key: 'conscientousness'` → `key: 'conscientiousness'`
  - These are the **only** two changes in this file; no other line is touched.
  - This fixes the silent mismatch with `page.js`'s `orderedKeys` where `conscientiousness`
    (correct) was used but the input was keyed to the misspelled variant, causing the
    Conscientiousness value to be sent as `0` on every prediction.
  - _Requirements: pre-existing bug fix (not tied to Phase 2 requirements, but must be
    resolved before Phase 2 wires the resume scores into the same `values` state)_

- [x] 2. Append Phase 2 constants to `app/config/constants.py`
  - [x] 2.1 Append `GEMINI_MODEL` and `MAX_RESUME_BYTES` to `constants.py`
    - Add exactly these two lines after the existing `ROLE_MAPPING` block, preceded by a
      `# --- Phase 2 additions ---` comment:
      ```python
      GEMINI_MODEL: str = "gemini-2.5-flash-lite"
      MAX_RESUME_BYTES: int = 5 * 1024 * 1024   # 5 MB
      ```
    - Do NOT modify any existing constant, import, or line in the file.
    - _Requirements: 10.1, 10.3, 11.3_

- [x] 3. Create `app/schemas/resume.py` — Pydantic data models
  - [x] 3.1 Implement `ResumeExtraction` and `ParsedResumeResponse`
    - Create `backend/fastapi/app/schemas/resume.py`.
    - `ResumeExtraction`: 14 `float` fields in the exact order of `orderedKeys`, each
      constrained with `Field(ge=1.0, le=10.0)`. Add a comment cross-referencing
      `TECHNICAL_FEATURES + PERSONALITY_FEATURES` from `constants.py`. Field names must
      use the correct spelling: `conscientiousness`.
    - `ParsedResumeResponse`: the same 14 `float` fields with **no** `Field` constraints
      (clamp is the authoritative guard; this model is purely for serialisation).
    - Both models import from `pydantic` only; no import from `constants.py` needed here.
    - _Requirements: 2.3, 2.6, 4.2_

- [x] 4. Create `app/services/resume_parser.py` — custom exceptions preamble
  - [x] 4.1 Define `UnsupportedMediaTypeError` and `GeminiUnavailableError` at module level
    - Create `backend/fastapi/app/services/resume_parser.py` (file creation only at this step).
    - Define the two custom exception classes before the `ResumeParser` class so they can
      be imported by the route without a circular dependency:
      ```python
      class UnsupportedMediaTypeError(Exception):
          """Raised when a file format other than PDF or DOCX is supplied."""

      class GeminiUnavailableError(Exception):
          """Raised when the Gemini API call fails or times out."""
      ```
    - _Requirements: 1.4, 2.5_

- [x] 5. Complete `ResumeParser` class in `app/services/resume_parser.py`
  - [x] 5.1 Implement `__init__`, `extract_text`, and `extract_skills`
    - Add all necessary imports: `os`, `io`, `pdfplumber`, `docx`, `google.genai`,
      `google.genai.types`, `dotenv.load_dotenv`, and the local imports
      `from app.config.constants import GEMINI_MODEL` and
      `from app.schemas.resume import ResumeExtraction, ParsedResumeResponse`.
    - `__init__`: call `load_dotenv()`, read `GEMINI_API_KEY` from `os.environ`, raise
      `RuntimeError("GEMINI_API_KEY is not set")` if absent/empty, then instantiate
      `self._client = google.genai.Client(api_key=api_key)`. Never log the key value.
    - `_extract_pdf(self, file_bytes)`: open `pdfplumber.open(io.BytesIO(file_bytes))`,
      concatenate all page text with `\n`, return the string.
    - `_extract_docx(self, file_bytes)`: open `docx.Document(io.BytesIO(file_bytes))`,
      join all paragraph text, return the string.
    - `extract_text(self, file_bytes, filename)`: dispatch to `_extract_pdf` or
      `_extract_docx` by extension; raise `UnsupportedMediaTypeError` for any other
      extension; raise `ValueError("Resume file is empty or unreadable")` if the result
      is empty or whitespace-only.
    - `extract_skills(self, text)`: build the prompt string, then call
      `self._client.models.generate_content(model=GEMINI_MODEL, contents=prompt,
      config=types.GenerateContentConfig(response_mime_type="application/json",
      response_schema=ResumeExtraction))` inside a `try/except Exception` that re-raises
      as `GeminiUnavailableError`. Include the mandatory free-tier data-usage comment
      immediately before the API call block. After `response.parsed`, apply the server-side
      clamp `max(1.0, min(10.0, v))` over all 14 fields by iterating
      `extraction.model_fields`. Return `ParsedResumeResponse(**clamped)`.
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.4, 2.5, 2.7, 2.8, 2.9, 3.1, 3.2, 3.3, 12.1, 12.2_

- [x] 6. Create `app/routes/resume.py` — `POST /parse-resume` route
  - [x] 6.1 Implement the route handler with the full guard chain
    - Create `backend/fastapi/app/routes/resume.py`.
    - Declare `resume_router = APIRouter()`.
    - Define `ALLOWED_EXTENSIONS = {"pdf", "docx"}` and `ALLOWED_MIMES` with the PDF and
      DOCX MIME types.
    - `parse_resume(request, file)`:
      1. Read all bytes with `await file.read()`.
      2. Size guard: if `len(file_bytes) > MAX_RESUME_BYTES` return `JSONResponse(413, ...)`.
      3. Extension + MIME guard: if either fails return `JSONResponse(415, ...)`.
      4. Get `parser = request.app.state.resume_parser`.
      5. Call `parser.extract_text(file_bytes, filename)` inside `try/except
         UnsupportedMediaTypeError` (→ 415) and `except ValueError` (→ 422).
      6. Call `parser.extract_skills(text)` inside `try/except GeminiUnavailableError`
         (→ 502).
      7. Return the `ParsedResumeResponse` result.
    - Do NOT import or reference `PredictorService`, `FeatureMapper`, `ModelRegistry`,
      or anything from `app/routes/predict.py`.
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 11.1, 11.2_

- [ ] 7. Update `app/main.py` — add exactly 3 lines
  - [ ] 7.1 Wire the resume router and parser into the app
    - Add two new import lines after the existing `from app.routes.predict import router` line:
      ```python
      from app.routes.resume import resume_router
      from app.services.resume_parser import ResumeParser
      ```
    - Inside the `lifespan` startup block, add one line after
      `app.state.predictor = PredictorService()`:
      ```python
      app.state.resume_parser = ResumeParser()
      ```
    - After the existing `app.include_router(router)` call, add:
      ```python
      app.include_router(resume_router)
      ```
    - All other lines in `main.py` remain byte-for-byte identical.
    - _Requirements: 4.8, 3.2_

- [ ] 8. Install new dependencies and pin exact versions in `requirements.txt`
  - Activate `backend/fastapi/venv` and install the three new packages:
    ```
    pip install google-genai pdfplumber python-docx
    ```
  - After installation, run `pip show google-genai pdfplumber python-docx` to capture the
    exact installed versions.
  - Append the pinned entries to `backend/fastapi/requirements.txt` under a
    `# Phase 2 — Resume parsing` comment. Do NOT duplicate or change any existing entry.
  - Also pin any newly pulled transitive dependencies that are not already in the file
    (use `pip freeze` to identify them).
  - _Requirements: 8.1, 8.2, 8.3_

- [ ] 9. Checkpoint — verify backend wiring before writing tests
  - Ensure `backend/fastapi/venv` is active.
  - Run: `python -c "from app.services.resume_parser import ResumeParser; print('import ok')"` from `backend/fastapi/`.
  - Run: `python -c "from app.routes.resume import resume_router; print('router ok')"`.
  - Ask the user before proceeding if either import fails.

- [ ] 10. Create `tests/test_resume_route.py` — 7 test cases with mocked Gemini
  - [ ] 10.1 Add session-scoped fixtures for file bytes
    - Add `minimal_pdf_bytes` (session): a hand-crafted minimal valid PDF byte string that
      `pdfplumber` can open, containing the text `"Python developer with 3 years experience."`.
      Build it with `reportlab` if available, or use a hardcoded 500-byte valid PDF literal.
    - Add `minimal_docx_bytes` (session): use `python-docx` in memory (`io.BytesIO`) to
      create a Document with one paragraph of real text; return `getvalue()`.
    - Add `oversized_bytes` (session): `b"x" * (5 * 1024 * 1024 + 1)`.
    - _Requirements: 9.1, 9.6_
  - [ ] 10.2 Add `mock_gemini` fixture and `resume_client` fixture
    - `mock_gemini` (function-scoped, via `monkeypatch`): patch
      `app.services.resume_parser.google.genai.Client` so that
      `client.models.generate_content().parsed` returns a `ResumeExtraction` with all
      14 fields set to `5.0`.
    - `resume_client` (module-scoped): a `TestClient(app)` constructed while the mock is
      applied at the lifespan startup so `app.state.resume_parser` holds the mocked parser.
    - _Requirements: 9.1_
  - [ ] 10.3 Implement `test_valid_pdf_returns_200_with_14_keys`
    - Upload `minimal_pdf_bytes` as `"resume.pdf"` with `content_type="application/pdf"`.
    - Assert `status_code == 200`, `set(body.keys()) == set(ORDERED_KEYS)`,
      all values are `float`, all values in `[1.0, 10.0]`.
    - _Requirements: 4.2, 9.2 — validates Property 1_
  - [ ] 10.4 Implement `test_valid_docx_returns_200_with_14_keys`
    - Same structure as 10.3 but uploads `minimal_docx_bytes` as `"resume.docx"` with the
      DOCX MIME type.
    - _Requirements: 4.2, 9.2 — validates Property 1_
  - [ ] 10.5 Implement `test_unsupported_type_returns_415`
    - Upload `b"hello"` as `"resume.txt"` with `content_type="text/plain"`.
    - Assert `status_code == 415` and `body["detail"] == "Unsupported file type. Upload a PDF or DOCX file."`.
    - _Requirements: 4.3, 9.3 — validates Property 2_
  - [ ] 10.6 Implement `test_oversized_file_returns_413`
    - Upload `oversized_bytes` as `"big.pdf"` with `content_type="application/pdf"`.
    - Assert `status_code == 413` and `body["detail"] == "File too large. Maximum allowed size is 5 MB."`.
    - _Requirements: 4.4, 9.5, 11.2, 11.4_
  - [ ] 10.7 Implement `test_empty_file_returns_422`
    - Upload `b""` as `"empty.pdf"` with `content_type="application/pdf"`.
    - Patch `parser.extract_text` to raise `ValueError("Resume file is empty or unreadable")`.
    - Assert `status_code == 422` and `body["detail"] == "Resume file is empty or unreadable."`.
    - _Requirements: 4.5, 1.3 — validates Property 5_
  - [ ] 10.8 Implement `test_gemini_error_returns_502_and_app_stays_alive`
    - Override the mock so `client.models.generate_content` raises `Exception("quota exceeded")`.
    - Upload `minimal_pdf_bytes` as `"resume.pdf"`.
    - Assert `status_code == 502` and correct `detail` message.
    - Send a follow-up `GET /` and assert `status_code == 200` to confirm the app is alive.
    - _Requirements: 4.6, 9.4 — validates Property 4_
  - [ ] 10.9 Implement `test_out_of_range_clamp_returns_clamped_values`
    - Configure mock `response.parsed` to return a `ResumeExtraction` where
      `computer_architecture=0.0`, `programming_skills=15.0`, all others `5.0`.
    - Upload `minimal_pdf_bytes`.
    - Assert `status_code == 200`, `body["computer_architecture"] == 1.0`,
      `body["programming_skills"] == 10.0`, all values in `[1.0, 10.0]`.
    - _Requirements: 12.3, 9.5 — validates Property 3_

- [ ] 11. Create `tests/test_phase1_regression.py` — regression wrapper
  - [ ] 11.1 Re-import all Phase 1 test functions
    - Create `backend/fastapi/tests/test_phase1_regression.py`.
    - Import (re-export) every test function from the three Phase 1 modules:
      - From `tests.test_predict_route`: `test_predict_valid_input_returns_200`,
        `test_predict_wrong_length_returns_422`, `test_health_check`
      - From `tests.test_feature_mapper`: `test_feature_mapper_smoke`,
        `test_feature_mapper_output_shape`, `test_feature_mapper_rejects_too_few_values`,
        `test_feature_mapper_rejects_too_many_values`
      - From `tests.test_predictor_service`: `test_predictor_service_smoke`,
        `test_predicted_role_is_valid`, `test_top_3_roles_count`,
        `test_top_3_roles_probabilities_in_range`, `test_predictor_service_bad_models_dir`
    - Do NOT define any new fixtures; `conftest.py` fixtures resolve automatically.
    - Add a module docstring: `"""Regression wrapper: re-runs all Phase 1 test functions."""`
    - _Requirements: 6.1, 6.2, 6.3_

- [ ] 12. Create `my-app/app/components/ResumeUpload.jsx`
  - [ ] 12.1 Implement the ResumeUpload component
    - Create `my-app/app/components/ResumeUpload.jsx`.
    - Add `'use client'` at the top.
    - Define the `ACCEPTED` constant:
      `'application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document'`
    - Component receives `{ setValues }` as its only prop.
    - State: `loading` (bool, false) and `error` (string, '').
    - `handleSubmit(e)`: prevent default, read `e.target.elements.resume.files[0]`, guard
      for no file, set `loading=true`, `error=''`, build `FormData` with field name `file`,
      `fetch('http://127.0.0.1:8000/parse-resume', { method: 'POST', body: formData })`,
      on success call `setValues(data)`, on non-ok response set `error` from `data.detail`,
      on network error set `"Network error. Please check your connection."`, always set
      `loading=false` in `finally`.
    - Render: heading "Auto-fill from Resume", descriptive `<p>`, a `<form>` with a `file`
      input (name="resume", accept=ACCEPTED, disabled when loading), a submit button
      showing "Extracting…" when loading / "Upload & Extract Skills" otherwise, and an
      error `<p>` (red, visible only when `error` is non-empty).
    - Disable both the input and the button while `loading === true`.
    - On error, do NOT call `setValues`.
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 13. Update `my-app/app/page.js` — add 2 lines only
  - [ ] 13.1 Import `ResumeUpload` and render it above `Features`
    - After the existing `import Features from "./components/Features";` line, add:
      ```js
      import ResumeUpload from "./components/ResumeUpload";
      ```
    - Inside the `return (...)` JSX, add `<ResumeUpload setValues={setValues} />` as the
      first child of the outer `<div>`, immediately above `<Features .../>`.
    - No other lines change; `setValues` is already defined in the existing `useState`.
    - _Requirements: 7.6, 7.7_

- [ ] 14. Final checkpoint — run full test suite and confirm all tests pass
  - Activate `backend/fastapi/venv`.
  - Run: `pytest tests/ -v` from `backend/fastapi/`.
  - Paste the actual pytest output to verify:
    - All 7 `test_resume_route` tests pass.
    - All 12 `test_phase1_regression` tests pass.
    - Zero failures across the full suite.
  - Ask the user if any test is failing before marking complete.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery.
- Task 1 is a standalone bug fix unrelated to Phase 2 features but must be first — it
  directly affects the `values` state that `ResumeUpload` pre-fills.
- Task 8 (dependency install + pin) is a hard prerequisite for Tasks 10–11; tests need
  `google-genai`, `pdfplumber`, and `python-docx` importable inside `venv`.
- The design document's `Correctness Properties` section maps each property to specific
  test cases: Properties 1–5 are covered by test cases in Tasks 10.3–10.9.
- All tests run inside `backend/fastapi/venv` with `pytest` only — no Hypothesis.
- No Phase 1 file (`predictor.py`, `feature_mapper.py`, `model_registry.py`,
  `agent_orchestrator.py`, `predict.py`, `prediction.py`, existing tests) is modified.
- `constants.py` only receives two appended lines; no existing constant is changed.
- `main.py` only receives three new lines; no existing line is changed.
- `page.js` only receives two new lines; no existing line is changed.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["3.1", "4.1"] },
    { "id": 3, "tasks": ["5.1"] },
    { "id": 4, "tasks": ["6.1"] },
    { "id": 5, "tasks": ["7.1"] },
    { "id": 6, "tasks": ["8"] },
    { "id": 7, "tasks": ["10.1", "10.2", "11.1", "12.1"] },
    { "id": 8, "tasks": ["10.3", "10.4", "10.5", "10.6", "10.7", "10.8", "10.9", "13.1"] }
  ]
}
```
