"""Paired persona-cluster bootstrap; no deployment side effects."""
import numpy as np
import pandas as pd


def promotion_gate(y_true, champion_pred, candidate_pred, personas, parity_passed,
                   min_gain=0.02, seed=42, n_resamples=2000):
    """Row accuracy gain; resample whole personas with replacement."""
    truth, old, new, groups = map(np.asarray, (y_true, champion_pred, candidate_pred, personas))
    if any(a.ndim != 1 for a in (truth, old, new, groups)):
        raise ValueError("Expected one-dimensional arrays")
    if len(truth) == 0 or not (len(truth) == len(old) == len(new) == len(groups)):
        raise ValueError("Predictions must align with the same holdout rows")
    if pd.isna(groups).any() or pd.isna(truth).any() or pd.isna(old).any() or pd.isna(new).any():
        raise ValueError("Missing labels or personas")
    if not 0 <= min_gain <= 1 or n_resamples < 1:
        raise ValueError("Invalid gate parameters")
    _, inverse = np.unique(groups, return_inverse=True)
    delta = (new == truth).astype(int) - (old == truth).astype(int)
    sizes = np.bincount(inverse)
    gains = np.bincount(inverse, weights=delta)
    if len(sizes) < 2:
        raise ValueError("At least two personas required")
    rng = np.random.default_rng(seed)
    draw = rng.integers(0, len(sizes), size=(n_resamples, len(sizes)))
    sampled = gains[draw].sum(axis=1) / sizes[draw].sum(axis=1)
    lower, upper = np.quantile(sampled, [0.05, 0.95])
    observed = float(delta.mean())
    parity = bool(parity_passed)
    return {
        "champion_accuracy": float((old == truth).mean()),
        "candidate_accuracy": float((new == truth).mean()),
        "observed_gain": observed, "ci_90_lower": float(lower),
        "ci_90_upper": float(upper), "min_gain": float(min_gain),
        "bootstrap_seed": int(seed), "bootstrap_resamples": int(n_resamples),
        "holdout_personas": int(len(sizes)), "parity_passed": parity,
        "promotion_eligible": bool(observed >= min_gain and lower > 0 and parity),
    }
