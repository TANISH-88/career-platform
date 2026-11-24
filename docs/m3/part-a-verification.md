# M3 Part A verification — CI #51

Verified commit: 0846c90794439f31c6fc7e453721c12c38e78aea
Branch: m3/part-a-corrected
CI: https://github.com/TANISH-88/career-platform/actions/workflows/ci.yml?query=branch%3Am3%2Fpart-a-corrected

Evidence supplied by repository owner: CI #51 green; Backend Tests & Lint, Frontend Build, and Docker Build & Smoke Test all passed.
- Backend: 49 passed, 17 warnings in 10.03s.
- M3 tests: 4 passed (cleaned source/quarantine, label mapping, frozen split, tampered CSV rejected).
- Legacy DVC tests: 3 skipped (original CareerMapping1.csv absent).
- Serving parity: 160 fixture rows; maximum probability difference 0.00e+00; 0/160 top-1 role mismatches; 0/480 top-3 role/probability mismatches.
- Total: 53 passed, 0 failed, 3 skipped.
- Cleaned data: 3,116 rows; 1,000 quarantined; 6,063 duplicate occurrences removed; 218 personas, 16 roles. 174 development personas / 2,376 rows; 44 holdout personas / 740 rows.
- SHA256: e774de4698a08ba9357a224190a54292d92d0cba35c66a1e25d366f66438499f.
- Approved quota adjustment: at least one persona per role in each split, rather than impossible 2/8 requirement.
- Role names corrected to LabelEncoder order; Software tester normalized to Software Tester.
- Old branch m3/part-a diverged due to stale history; corrected branch was verified 11 commits ahead, 0 behind main before this report. Main untouched.
- CP13/14: technical verification complete on review branch. Final reviewer sign-off pending. Owner authorized proceeding to Part B.
