# M3 cleaned data and frozen holdout

- Source: initial commit b82171031aa0d47a3030c86cebad0b22cf5871eb, data/CareerMapping1.csv (10,179 rows); compared against the tracked CareerMap source.
- Integer technical rows: 9,179; source multiset disagreement: zero.
- Fractional technical rows: 1,000, quarantined; 6,063 exact duplicate occurrences removed.
- 3,116 rows, 218 personas, 16 roles; original row index retained as row_id.
- Only target spelling normalization: Software tester -> Software Tester, matching public API spelling. Backend class order corrected to alphabetical LabelEncoder order. Existing model binaries unchanged.
- Persona ID: SHA-1 of ten personality values formatted to six decimal places and joined by a pipe.
- Holdout: 44/218 personas (740 rows), development 174 personas (2,376 rows). Rank personas by SHA256 of seed 42, colon, persona ID. Visit roles in ascending persona count, breaking ties by role name; select first ranked eligible persona if role not covered, ensuring every role retains a development persona. Fill remaining slots in rank order using same constraint. A shared persona spans Business Analyst and Customer Service Executive.
- Original quota (2 holdout / 8 dev per role) is impossible; owner approved at least one per role on both sides. API Specialist has only two personas. Per-role scores will be uncertain.
- Manifest binds exact CSV bytes with SHA256. Never regenerate the holdout during training. Part B will connect train.py to load_frozen_split.
- CI #51 passed all four frozen-data tests; see docs/m3/part-a-verification.md. No promotion or deployment.

