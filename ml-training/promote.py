"""M3 safety boundary: no serving artifact writes before approval/deployment phase.

Use train.py candidate to produce a paired-bootstrap eligibility report.
Eligibility is not deployment approval. M4 will implement reviewed promotion.
"""


def promote():
    raise SystemExit("Promotion disabled in M3; review candidate report. No files copied.")


if __name__ == "__main__":
    promote()
