# Requirements Document

## Introduction

Phase 2 extends the existing Career Prediction Platform (Phase 1 FastAPI backend) with resume upload and LLM-based skill extraction. A user uploads a PDF or DOCX resume; the backend extracts raw text, sends it to the Gemini API with a structured response schema, and returns 14 float values (one per feature in `TECHNICAL_FEATURES + PERSONALITY_FEATURES`) on a 1–10 scale. The frontend pre-fills the existing `values` state in `page.js` so the user can review and edit every score before clicking Predict.

Phase 2 is strictly additive: no existing file from Phase 1 (services, routes, schemas, tests) is modified. The `POST /predict` endpoint and its request/response contract remain untouched.

---

## Glossary

- **ResumeParser**: New service at `backend/fastapi/app/services/resume_parser.py` responsible for text extraction and Gemini API calls.
- **ResumeExtraction**: Pydantic model at `backend/fastapi/app/schemas/resume.py` that holds one `float` field per feature name; used directly as Gemini's `response_schema`.
- **ParseResumeRoute**: New FastAPI route at `backend/fastapi/app/routes/resume.py` that accepts an `UploadFile` and returns 14 extracted values.
- **ResumeUpload**: New Next.js component at `my-app/app/components/ResumeUpload.jsx` that sends the file to `/parse-resume` and pre-fills the `values` state.
- **Gemini API**: Google's generative AI API accessed via the official `google-genai` SDK with a structured `response_schema`.
- **GEMINI_MODEL**: The constant `"gemini-2.5-flash-lite"` defined in `app/config/constants.py`, referencing the stable Gemini 2.5 Flash-Lite model. Selected because: it is explicitly designed for "simple data extraction", has the highest free-tier rate limits (15 RPM, 1,000 requests/day), supports structured outputs natively, and is the stable (non-preview) free-tier Flash model as of July 2025.
- **TECHNICAL_FEATURES**: The list of 4 technical feature name strings defined in `app/config/constants.py`.
- **PERSONALITY_FEATURES**: The list of 10 personality feature name strings defined in `app/config/constants.py`.
- **orderedKeys**: The 14-element array of snake_case keys used in `page.js` to build the prediction payload, matching the order `TECHNICAL_FEATURES + PERSONALITY_FEATURES`.
- **values state**: The React `useState` object in `page.js` keyed by `orderedKeys`; read by `Features.jsx` to render inputs.
- **Phase 1 test suite**: The three existing test files (`test_predict_route.py`, `test_feature_mapper.py`, `test_predictor_service.py`) plus `conftest.py`.

---

## Requirements

### Requirement 1: Text Extraction from Uploaded Resume

**User Story:** As a job seeker, I want to upload my resume as a PDF or DOCX file, so that the system can read its content without requiring me to copy-paste text manually.

#### Acceptance Criteria

1. WHEN a PDF file is provided to the ResumeParser, THE ResumeParser SHALL extract all readable text using `pdfplumber` and return it as a single UTF-8 string.
2. WHEN a DOCX file is provided to the ResumeParser, THE ResumeParser SHALL extract all readable text using `python-docx` and return it as a single UTF-8 string.
3. IF the extracted text from a PDF or DOCX file is empty or contains only whitespace, THEN THE ResumeParser SHALL raise a `ValueError` with the message `"Resume file is empty or unreadable"`.
4. THE ResumeParser SHALL NOT accept any file format other than PDF and DOCX; all other formats SHALL cause the caller to receive an `UnsupportedMediaTypeError`.

---

### Requirement 2: LLM-Based Skill Extraction via Gemini API

**User Story:** As a job seeker, I want the system to automatically score my skills from my resume text, so that I do not have to manually assign values to 14 features.

#### Acceptance Criteria

1. WHEN resume text is provided to the ResumeParser, THE ResumeParser SHALL call the Gemini API using the official `google-genai` SDK with the `ResumeExtraction` Pydantic model as the `response_schema`.
2. THE ResumeParser SHALL NOT perform manual JSON parsing or string splitting to extract feature scores; structured output from the SDK SHALL be the only extraction mechanism.
3. THE ResumeParser SHALL return exactly 14 float values, one for each feature name in `TECHNICAL_FEATURES + PERSONALITY_FEATURES`, in that order.
4. THE ResumeParser SHALL source all feature names exclusively from `app/config/constants.py`; feature names SHALL NOT be redefined or duplicated inside `resume_parser.py` or `resume.py`.
5. IF the Gemini API returns an error or times out, THEN THE ResumeParser SHALL raise a `GeminiUnavailableError` with a descriptive message that includes the upstream error detail.
6. THE ResumeExtraction schema SHALL define one `float` field per feature name in `TECHNICAL_FEATURES + PERSONALITY_FEATURES`, each constrained to the range `[1.0, 10.0]` via Pydantic `Field(ge=1.0, le=10.0)` validation.
7. THE ResumeParser SHALL use the model identifier stored in the `GEMINI_MODEL` constant imported from `app/config/constants.py`; the model string SHALL NOT be inlined in `resume_parser.py`.
8. AFTER receiving a structured response from the Gemini API, THE ResumeParser SHALL apply a server-side clamp to every extracted value using `max(1.0, min(10.0, value))`, regardless of whether the Pydantic schema constraint was honored. This clamp is the authoritative enforcement; schema validation is a first-pass guard only.
9. THE `resume_parser.py` file SHALL include a comment immediately before the Gemini API call block with the following text: `# NOTE: Free-tier Gemini requests may be used by Google for model training and improvement. Do not send confidential, proprietary, or personally identifiable information through this path without first reviewing Google's data usage policies and upgrading to a paid tier if required.`

---

### Requirement 3: GEMINI_API_KEY Configuration

**User Story:** As a backend developer, I want the application to fail fast on startup when the Gemini API key is missing, so that misconfiguration is caught immediately rather than at request time.

#### Acceptance Criteria

1. THE ResumeParser SHALL load `GEMINI_API_KEY` exclusively from `backend/fastapi/.env` using `python-dotenv`.
2. IF `GEMINI_API_KEY` is absent or empty in the environment at application startup, THEN THE Application SHALL raise a `RuntimeError` with the message `"GEMINI_API_KEY is not set"` before accepting any requests.
3. THE Application SHALL NOT expose the value of `GEMINI_API_KEY` in any log output, error response, or API response body.

---

### Requirement 4: POST /parse-resume Route

**User Story:** As a frontend developer, I want a `/parse-resume` endpoint that accepts a resume file and returns 14 feature scores, so that I can pre-fill the prediction form without building a separate extraction service.

#### Acceptance Criteria

1. THE ParseResumeRoute SHALL expose a `POST /parse-resume` endpoint that accepts a multipart `UploadFile` field named `file`.
2. WHEN a valid PDF or DOCX file is uploaded, THE ParseResumeRoute SHALL return HTTP 200 with a JSON object containing exactly 14 keys matching `orderedKeys` (`computer_architecture`, `programming_skills`, `project_management`, `communication_skills`, `openness`, `conscientiousness`, `extraversion`, `agreeableness`, `emotional_range`, `conversation`, `openness_change`, `hedonism`, `self_enhancement`, `self_transcendence`), each mapped to a `float` in `[1.0, 10.0]`.
3. IF the uploaded file's MIME type or extension is not PDF or DOCX, THEN THE ParseResumeRoute SHALL return HTTP 415 with a JSON body `{"detail": "Unsupported file type. Upload a PDF or DOCX file."}`.
4. IF the uploaded file exceeds 5 MB in size, THEN THE ParseResumeRoute SHALL return HTTP 413 with a JSON body `{"detail": "File too large. Maximum allowed size is 5 MB."}` before attempting any text extraction or Gemini API call.
5. IF the uploaded file is empty or its text content is unreadable, THEN THE ParseResumeRoute SHALL return HTTP 422 with a JSON body `{"detail": "Resume file is empty or unreadable."}`.
6. IF the Gemini API is unavailable or returns an error, THEN THE ParseResumeRoute SHALL return HTTP 502 with a JSON body `{"detail": "Skill extraction service unavailable. Please try again later."}` and the FastAPI application SHALL remain running.
7. THE ParseResumeRoute SHALL NOT modify, call, or import `PredictorService`, `FeatureMapper`, `ModelRegistry`, or `app/routes/predict.py`.
8. THE ParseResumeRoute SHALL be registered in `app/main.py` by including the new router; `app/main.py` modifications SHALL be limited to adding the new router import and `app.include_router(resume_router)` call.

---

### Requirement 5: Zero Modification of Phase 1 Artifacts

**User Story:** As a backend developer, I want Phase 2 to be purely additive, so that existing prediction functionality is guaranteed to be unaffected by the resume feature.

#### Acceptance Criteria

1. THE Phase 2 implementation SHALL NOT modify `backend/fastapi/app/services/predictor.py`, `backend/fastapi/app/services/feature_mapper.py`, `backend/fastapi/app/services/model_registry.py`, `backend/fastapi/app/services/agent_orchestrator.py`, or `backend/fastapi/app/routes/predict.py`.
2. THE Phase 2 implementation SHALL NOT modify `backend/fastapi/app/schemas/prediction.py` or `backend/fastapi/app/config/constants.py`.
3. THE Phase 2 implementation SHALL NOT alter the request schema, response schema, HTTP method, or URL path of the `POST /predict` endpoint.
4. THE Phase 2 implementation SHALL NOT modify any existing test file in `backend/fastapi/tests/`.

---

### Requirement 6: Regression Test for Phase 1

**User Story:** As a developer, I want a dedicated regression test that re-runs the full Phase 1 test suite, so that I have an explicit, auditable signal that Phase 2 did not break any Phase 1 behaviour.

#### Acceptance Criteria

1. THE test suite SHALL include a file `backend/fastapi/tests/test_phase1_regression.py` that imports and re-executes all assertions from `test_predict_route.py`, `test_feature_mapper.py`, and `test_predictor_service.py`.
2. WHEN the regression test file is run with `pytest` inside `backend/fastapi/venv`, THE test runner SHALL report zero failures for all Phase 1 test cases.
3. THE regression test file SHALL NOT duplicate fixture definitions; it SHALL reuse `conftest.py` fixtures without modification.

---

### Requirement 7: ResumeUpload Frontend Component

**User Story:** As a job seeker, I want to upload my resume from the web interface, so that the feature sliders are pre-filled automatically and I can adjust them before submitting a prediction.

#### Acceptance Criteria

1. THE ResumeUpload component SHALL render a file input that accepts only `.pdf` and `.docx` MIME types (`application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`).
2. WHEN a user selects a file and submits it, THE ResumeUpload component SHALL send a `multipart/form-data` POST request to `http://127.0.0.1:8000/parse-resume` with the file in a field named `file`.
3. WHEN THE ParseResumeRoute returns HTTP 200, THE ResumeUpload component SHALL call `setValues` with the returned object so that the `values` state in `page.js` is updated with all 14 keys.
4. WHILE the upload and extraction request is in flight, THE ResumeUpload component SHALL display a loading indicator and disable the file input and submit button.
5. IF THE ParseResumeRoute returns an error (HTTP 413, 415, 422, or 502), THEN THE ResumeUpload component SHALL display a human-readable error message to the user and SHALL NOT overwrite the current `values` state.
6. THE ResumeUpload component SHALL be rendered in `page.js` above the `Features` component so that pre-filled values are visible to the user before interaction.
7. AFTER pre-fill, THE `Features` component SHALL remain fully editable; the user SHALL be able to modify any of the 14 values before clicking Predict.

---

### Requirement 8: Dependency Management

**User Story:** As a developer, I want all new dependencies pinned to exact versions, so that the environment is reproducible and no existing dependency is accidentally overwritten.

#### Acceptance Criteria

1. THE `backend/fastapi/requirements.txt` file SHALL include `google-genai`, `pdfplumber`, and `python-docx` each pinned to the exact version installed in `backend/fastapi/venv`.
2. THE updated `requirements.txt` SHALL NOT duplicate any entry that already exists in the file.
3. THE updated `requirements.txt` SHALL NOT remove or change the version pin of any existing dependency.

---

### Requirement 9: Test Coverage for Phase 2

**User Story:** As a developer, I want automated tests for the resume parsing feature that run entirely without real API calls, so that the test suite is fast, deterministic, and has no external cost.

#### Acceptance Criteria

1. THE Phase 2 test suite SHALL mock the Gemini client; no test SHALL make a real network call to the Gemini API.
2. WHEN a valid PDF or DOCX file fixture is provided to the mocked pipeline, THE test SHALL assert that the response is HTTP 200 and that the response body contains exactly 14 keys matching `orderedKeys`, each with a `float` value in `[1.0, 10.0]`.
3. WHEN a file with an unsupported extension is uploaded, THE test SHALL assert that the response is HTTP 415.
4. WHEN the mocked Gemini client raises an exception, THE test SHALL assert that the response is HTTP 502 and that the FastAPI application instance remains available for subsequent requests.
5. THE Phase 2 tests SHALL include a test for HTTP 413 (oversized file) and a test for the out-of-range clamp (Requirement 12.3).
6. THE Phase 2 tests SHALL be runnable with `pytest` inside `backend/fastapi/venv` without any additional setup beyond installing `requirements.txt`.
7. THE Phase 2 tests SHALL NOT use Hypothesis or any other property-based testing library.

---

### Requirement 10: Gemini Model Constant

**User Story:** As a backend developer, I want the Gemini model name defined as a single named constant, so that updating to a newer model requires a one-line change in one place.

#### Acceptance Criteria

1. THE constant `GEMINI_MODEL: str = "gemini-2.5-flash-lite"` SHALL be defined in `backend/fastapi/app/config/constants.py` alongside the existing `ROLE_MAPPING`, `TECHNICAL_FEATURES`, and `PERSONALITY_FEATURES` constants.
2. THE `ResumeParser` SHALL import `GEMINI_MODEL` from `app/config/constants.py` and pass it as the model identifier to the `google-genai` SDK call; the model string `"gemini-2.5-flash-lite"` SHALL NOT appear anywhere in `resume_parser.py`.
3. No other Phase 1 constant or value in `constants.py` SHALL be modified when adding `GEMINI_MODEL`.

---

### Requirement 11: Upload Size Limit

**User Story:** As an operator, I want oversized resume uploads rejected before any processing begins, so that a single large file cannot exhaust the daily free-tier Gemini quota.

#### Acceptance Criteria

1. THE ParseResumeRoute SHALL read the uploaded file's byte length before any text extraction or Gemini API call.
2. IF the uploaded file exceeds 5,242,880 bytes (5 MB), THE ParseResumeRoute SHALL return HTTP 413 with a JSON body `{"detail": "File too large. Maximum allowed size is 5 MB."}` and SHALL NOT proceed to text extraction or call the Gemini API.
3. THE 5 MB limit SHALL be enforced as a named constant `MAX_RESUME_BYTES: int = 5 * 1024 * 1024` defined in `backend/fastapi/app/config/constants.py`, not as a magic number inline in the route handler.
4. THE Phase 2 test suite SHALL include a test that uploads a synthetic file exceeding 5 MB and asserts the response is HTTP 413.

---

### Requirement 12: Server-Side Score Clamp

**User Story:** As a backend developer, I want extracted scores clamped to [1.0, 10.0] on the server regardless of what the model returns, so that out-of-range values from the LLM never reach the frontend or prediction pipeline.

#### Acceptance Criteria

1. THE `ResumeParser` SHALL apply `max(1.0, min(10.0, value))` to every extracted float immediately after receiving the structured response from the Gemini SDK, before returning values to the route handler.
2. The server-side clamp SHALL be applied even when Pydantic schema validation (`ge=1.0, le=10.0`) also rejects out-of-range values — the clamp is the authoritative enforcement layer.
3. THE Phase 2 test suite SHALL include a test that configures the mocked Gemini client to return a `ResumeExtraction`-shaped response containing at least one value below 1.0 and one value above 10.0, and asserts that the `/parse-resume` endpoint returns HTTP 200 with all values clamped to `[1.0, 10.0]`.
