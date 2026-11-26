# P1 Part B2 — Live Browser Verification Evidence

**Date:** 2026-11-27  
**Branch:** `p1/accounts`  
**Frontend Target:** `http://localhost:3000` (`next start` production build)  
**Backend Target:** `http://127.0.0.1:8000` (`uvicorn app.main:app` with clean Alembic-migrated SQLite DB at `7e7a0f2e3301`)  
**Browser:** Google Chrome `158.0.8127.38` via Chrome DevTools (`DevToolsActivePort` on `9222`)

---

## Verified Flows

### 1. Anonymous Home & Prediction (`GET /`, `POST /api/predict`)
- Loaded `http://localhost:3000/` unauthenticated cleanly with navbar links `FuturePredict`, `Quick Predict`, `Sign in`, `Get Started`.
- Confirmed **no false session-expired banner** rendered on initial anonymous visit (`alert` region empty).
- Filled all 14 skill spinbuttons (`7`) and clicked `Predict` -> `POST /api/predict [200]`, rendering `"Project Manager"` alongside the prompt `"Sign in or create an account to save predictions in workspaces."`.
- Expected unauthenticated boot probe `POST /api/auth/refresh` returned `401 Unauthorized`.

### 2. Google Sign-In Status (`GET /login`)
- Loaded `http://localhost:3000/login`.
- **Live Google Sign-In unavailable locally:** Rendered fallback notice:
  `Google Sign-In unavailable in local config (set NEXT_PUBLIC_GOOGLE_CLIENT_ID to enable).`
- Live Google OAuth verification remains **untested in local dev** because `GOOGLE_CLIENT_ID` / `NEXT_PUBLIC_GOOGLE_CLIENT_ID` are unset in local `.env` / `.env.local` (covered via mocked token tests in backend `test_auth.py` and frontend `authAndWorkspaces.test.mjs`).

### 3. Registration & Authenticated State (`GET /register`)
- Registered `browser_verify@example.com` (`BrowserPassword123!`), receiving `POST /api/auth/register [201]`, `POST /api/auth/login [200]`, `GET /api/auth/me [200]`, `GET /api/workspaces?include_archived=false [200]`.
- Redirected to `/workspaces` showing `ACTIVE WORKSPACES (0)` and updated navbar (`FuturePredict`, `Quick Predict`, `Workspaces`, `Sign out`).
- Initial `GET /api/workspaces/last-active` returned `404` as expected before any workspace existed.

### 4. Workspace Creation, CP21 Resume Versions UI & Manual Prediction (`/workspaces/<id>`)
- Created `Browser Verify Workspace` (`POST /api/workspaces [201]`) -> routed to `/workspaces/b5f41c02-8e41-4c94-b8f9-1c67018495e7`.
- Verified CP21 **Resume Versions** card (`"Upload Resume & Compare AI + ML Readings"`) rendered `0/10 versions`, unchecked consent box, and **disabled** `Save Resume Version` button when consent is unchecked.
- Filled all 14 skill fields (`7`) and clicked `Save & Predict in Workspace` -> `POST /api/workspaces/.../predict [200]`, `GET /api/workspaces/.../history [200]`, `GET /api/workspaces/.../resume-versions [200]`, `GET /api/workspaces/last-active [200]`.
- Rendered `LATEST PREDICTION · FRF_V1` (`Project Manager` `13.9%`, `Networking Engineer` `11.5%`, `Application Support Engineer` `11.3%`) and `Manual Prediction History (1)` with `Load skills`.

### 5. Session Persistence Across Full Reload
- Performed a full browser page reload on `/workspaces/b5f41c02-8e41-4c94-b8f9-1c67018495e7`.
- Zero console errors on reload.
- Browser sent the `HttpOnly` cookie and `POST /api/auth/refresh [200]` returned `Set-Cookie: refresh_token=...; HttpOnly; Max-Age=604800; Path=/; SameSite=lax` plus a fresh in-memory `access_token`.
- User stayed signed in (`Workspaces`, `Sign out`) and all 14 skill values (`7`) and `Manual Prediction History (1)` reloaded cleanly.
- **Note on storage inspection:** `chrome_devtools/evaluate_script` timed out waiting on user permission, so `localStorage`/`sessionStorage` contents were not evaluated via DevTools JS injection during the live run; memory-only storage is enforced in `my-app/lib/apiClient.mjs` and verified in `my-app/tests/authAndWorkspaces.test.mjs`.

### 6. "Continue Where You Left Off" Popup & Continuation
- Navigated back to `http://localhost:3000/` while signed in.
- Verified popup appeared: `WELCOME BACK` / `Continue where you left off` / `Browser Verify Workspace` / `Last opened ...` / `Continue` / `All workspaces`.
- Clicked `Continue` -> routed back to `/workspaces/b5f41c02-8e41-4c94-b8f9-1c67018495e7` and restored skills + `Manual Prediction History (1)`.

### 7. Archive, Restore, Sign Out & Re-Login
- Archived `Browser Verify Workspace` on `/workspaces` (`POST .../archive [200]`, `ACTIVE WORKSPACES (0)`), checked `Show archived` (`ARCHIVED WORKSPACES (1)` with `Restore` and `Delete` actions), and clicked `Restore` (`POST .../unarchive [200]`, back in `ACTIVE WORKSPACES (1)`).
- Clicked `Sign out` (`POST /api/auth/logout [200]`), confirmed signed-out landing on `/` with no false session-expired alert.
- Signed back in at `/login` (`POST /api/auth/login [200]`), reopened `/workspaces/b5f41c02-8e41-4c94-b8f9-1c67018495e7`, and confirmed persisted prediction history + skill inputs.

---

## Console & Stability Summary
- Zero uncaught JavaScript exceptions or React runtime errors across the entire walkthrough.
- Expected HTTP resource logs only on unauthenticated `POST /api/auth/refresh` (`401`) and empty `GET /api/workspaces/last-active` (`404`).
- Non-blocking browser DOM/a11y warnings noted on form field label/autocomplete attributes.
