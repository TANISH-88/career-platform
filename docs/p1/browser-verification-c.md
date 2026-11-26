# P1 Part C — Live Browser Verification Report

- **Date:** 2026-11-27
- **Branch:** `p1/accounts` (verified against local build of `app/main.py`, `app/config/constants.py`, `app/services/resume_parser.py`, and `my-app`)
- **Browser:** Google Chrome (remote debugging port 9222)
- **Servers:**
  - FastAPI Backend: `http://127.0.0.1:8000` (SQLite `partc_verify.db` migrated via `alembic upgrade head`)
  - Next.js Frontend: `http://localhost:3000` (`next start` production build with `.env.local`)
- **Credentials:** Configured locally via `backend/.env` (`GOOGLE_CLIENT_ID`, `GEMINI_API_KEY`) and `my-app/.env.local` (`NEXT_PUBLIC_GOOGLE_CLIENT_ID`). No secret values are included in this report.

---

## 1. Live Google Sign-In (OAuth)

- **Status:** PASS
- Navigated to `http://localhost:3000/login` — confirmed live Google Sign-In button rendered (fallback text not shown).
- Completed Google OAuth sign-in flow:
  - `POST /api/auth/google` -> `200 OK`
  - `GET /api/auth/me` -> `200 OK` (`<verified-google-test-account>`)
  - Redirected to `/workspaces`; navbar displayed authenticated controls (`FuturePredict / Quick Predict / Workspaces / Sign out`).
- Database verification (`users` table): confirmed `google_sub` is populated and `password_hash` is `NULL` (Google-only account).

---

## 2. Live Gemini Resume Analysis (`synthetic_resume.pdf`)

- **Status:** PASS
- **Fix applied during verification:** Google Gemini API returned `404 NOT_FOUND` for `gemini-2.5-flash-lite` (deprecated for new keys, recommending `gemini-3.5-flash-lite`). Updated `GEMINI_MODEL` in `backend/fastapi/app/config/constants.py` to `"gemini-3.5-flash-lite"`.
- Created workspace `"Part C Gemini Verify"` (`id = 3aa34582-12a8-4982-840f-d40e7acb7833`).
- Attached synthetic PDF (`synthetic_resume.pdf`, 1,830 bytes, zero real PII), checked the Gemini consent checkbox, and clicked **Save Resume Version**.
- `POST /api/workspaces/3aa34582-12a8-4982-840f-d40e7acb7833/resume-versions` -> `201 Created`.
- **Result rendered in UI (`v1`):**
  - **Predicted Role:** `Application Support Engineer`
  - **Top 3 Roles:** `Application Support Engineer (16.3%) · Networking Engineer (9.9%) · Graphics Designer (7.8%)`
  - **Model Badges:** `ML: frf_v1` and `LLM: gemini-3.5-flash-lite`
- **14 Gemini-derived skill scores returned:**
  1. Computer Architecture: `8.5`
  2. Programming Skills: `9.0`
  3. Project Management: `8.0`
  4. Communication Skills: `8.5`
  5. Openness: `9.0`
  6. Conscientiousness: `9.5`
  7. Extraversion: `7.5`
  8. Agreeableness: `8.0`
  9. Emotional Range: `5.0`
  10. Conversation: `8.0`
  11. Openness to Change: `8.5`
  12. Hedonism: `5.0`
  13. Self-enhancement: `6.5`
  14. Self-transcendence: `7.0`
- Clicked **Load into inputs** -> verified all 14 `input[type="number"]` fields populated with `["8.5","9","8","8.5","9","9.5","7.5","8","5","8","8.5","5","6.5","7"]`.

---

## 3. Database Persistence Across Server Restart

- **Status:** PASS
- Stopped the FastAPI uvicorn daemon, inspected `partc_verify.db` directly, restarted uvicorn against the same `partc_verify.db`, and verified `GET /` (`{"message":"Backend running"}`).
- Confirmed persisted rows in SQLite after restart:
  - `users`: `('<verified-google-test-account>', google_sub IS NOT NULL = 1, password_hash IS NULL = 1)`
  - `workspaces`: `('3aa34582-12a8-4982-840f-d40e7acb7833', 'Part C Gemini Verify')`
  - `resume_versions`: `('87b22cc4-61f1-407d-bbca-afaad3bf6aa1', version_number = 1, 'Application Support Engineer', 'frf_v1', 'gemini-3.5-flash-lite')`

---

## 4. Storage Security & Console Check

- **Status:** PASS
- Inspected `Object.keys(localStorage)` -> `[]`
- Inspected `Object.keys(sessionStorage)` -> `[]`
- Confirmed zero `access_token` or JWT values stored in browser web storage.
- **Console errors / failed network requests on final workspace session:** `0` console errors, `0` failed network requests.

---

## 5. Automated Test & Lint Checks (Post-Final-Edit)

- Backend `pytest`: `75 passed, 16 warnings in 35.80s`
- Backend `ruff check app/ --select E9,F63,F7,F82`: `All checks passed!`
- Frontend `npm test`: `10 passed, 0 failed`
- Frontend `npm run build`: `✓ Compiled successfully`, `✓ Generating static pages (7/7)`
