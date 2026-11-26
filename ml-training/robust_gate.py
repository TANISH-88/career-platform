"""Paired fixed-seed gate, macro-F1 guard and equal-persona weighting."""
import numpy as np
from sklearn.metrics import f1_score
from promotion_gate import promotion_gate

SEEDS = (42, 0, 1, 7, 13, 21, 99, 123, 456, 789, 2024)


def robust_gate(y, frozen, candidate, personas, old_by_seed, new_by_seed,
                parity, min_gain=0.02, n_resamples=2000):
    y, frozen, candidate, personas = map(np.asarray, (y, frozen, candidate, personas))
    old, new = np.asarray(old_by_seed), np.asarray(new_by_seed)
    if old.shape != (len(SEEDS), len(y)) or new.shape != old.shape:
        raise ValueError("Fixed matched seed predictions required")
    if not np.array_equal(old[0], frozen) or not np.array_equal(new[0], candidate):
        raise ValueError("Primary predictions must match seed 42")
    primary = promotion_gate(y, frozen, candidate, personas, parity,
                             min_gain=min_gain, n_resamples=n_resamples)
    def macro(pred):
        return float(f1_score(y, pred, labels=np.arange(16), average="macro", zero_division=0))
    primary_macro_gain = macro(candidate) - macro(frozen)
    delta = (new == y).astype(float) - (old == y).astype(float)
    _, group_index = np.unique(personas, return_inverse=True)
    sizes = np.bincount(group_index)
    per_persona = np.stack([np.bincount(group_index, weights=row) / sizes for row in delta])
    rng = np.random.default_rng(42)
    seed_draws = rng.integers(0, len(SEEDS), (n_resamples, len(SEEDS)))
    persona_draws = rng.integers(0, len(sizes), (n_resamples, len(sizes)))
    boot = per_persona[seed_draws[:, :, None], persona_draws[:, None, :]].mean(axis=(1, 2))
    lower, upper = np.quantile(boot, [0.05, 0.95])
    row_gains = delta.mean(axis=1)
    macro_gains = [macro(n) - macro(o) for o, n in zip(old, new)]
    primary["single_seed_eligible"] = primary["promotion_eligible"]
    primary.update({"matched_seeds": list(SEEDS), "seed_row_gains": row_gains.tolist(),
                    "mean_seed_row_gain": float(row_gains.mean()),
                    "mean_equal_persona_gain": float(per_persona.mean()),
                    "joint_seed_persona_ci_90": [float(lower), float(upper)],
                    "primary_macro_f1_gain": primary_macro_gain,
                    "mean_seed_macro_f1_gain": float(np.mean(macro_gains)),
                    "promotion_eligible": bool(primary["single_seed_eligible"] and
                        row_gains.mean() >= min_gain and per_persona.mean() >= min_gain and
                        lower > 0 and primary_macro_gain >= -1e-12 and
                        np.mean(macro_gains) >= -1e-12)})
    return primary
