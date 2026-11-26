import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from promotion_gate import promotion_gate


def examples():
    y = np.tile([0, 1, 2, 3], 44)
    groups = np.repeat(np.arange(44), 4)
    champion = y.copy()
    champion[::2] = (champion[::2] + 1) % 4
    candidate = champion.copy()
    candidate[::4] = y[::4]
    return y, champion, candidate, groups


def test_identical_rejected():
    y, old, _, g = examples()
    report = promotion_gate(y, old, old, g, True)
    assert not report["promotion_eligible"]
    assert report["observed_gain"] == 0


def test_shuffled_labels_rejected():
    y, old, _, g = examples()
    shuffled = np.random.default_rng(42).permutation(y)
    assert not promotion_gate(y, old, shuffled, g, True)["promotion_eligible"]


def test_half_error_fixer_eligible():
    y, old, new, g = examples()
    result = promotion_gate(y, old, new, g, True)
    assert result["promotion_eligible"]
    assert result["observed_gain"] == pytest.approx(0.25)
    assert result["ci_90_lower"] > 0
    assert result == promotion_gate(y, old, new, g, True)


def test_parity_failure_rejected():
    y, old, new, g = examples()
    assert not promotion_gate(y, old, new, g, False)["promotion_eligible"]


def test_minimum_gain_and_alignment():
    y, old, new, g = examples()
    assert not promotion_gate(y, old, new, g, True, min_gain=0.3)["promotion_eligible"]
    with pytest.raises(ValueError):
        promotion_gate(y, old[:-1], new, g, True)
