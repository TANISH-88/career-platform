"""
promote.py - Explicit promotion step to promote candidate models to serving folder.

Usage:
    python ml-training/promote.py
"""

import pathlib
import shutil


def promote() -> None:
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    src_dir = repo_root / "ml-training" / "artifacts"
    dest_dir = repo_root / "backend" / "fastapi" / "models"

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
