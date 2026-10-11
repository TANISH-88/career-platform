"""
promote.py - Explicit promotion step to promote candidate models to serving folder.

Runs serving parity gate (check_parity.py) before copying.
Refuses to promote if parity fails.

Usage:
    python ml-training/promote.py
"""

import pathlib
import shutil
import sys

from check_parity import check_parity


def promote() -> None:
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    src_dir = repo_root / "ml-training" / "artifacts"
    dest_dir = repo_root / "backend" / "fastapi" / "models"

    # --- Parity gate: must pass before any files are copied ---
    print("[PROMOTE] Running serving parity gate...")
    ok = check_parity(src_dir)
    if not ok:
        print("[PROMOTE ABORTED] Parity gate failed. No files were copied.")
        sys.exit(1)
    print("[PROMOTE] Parity gate passed.\n")

    dest_dir.mkdir(parents=True, exist_ok=True)

    artifacts = ["frf.pkl", "scaler.pkl", "pca.pkl"]
    for filename in artifacts:
        src_file = src_dir / filename
        if not src_file.exists():
            raise FileNotFoundError(
                f"Candidate artifact not found: {src_file}. Run train.py first."
            )
        dest_file = dest_dir / filename
        shutil.copy2(src_file, dest_file)
        print(f"[PROMOTED] {src_file.name} -> {dest_file}")


if __name__ == "__main__":
    promote()
