# CP15 persistent MLflow registration — verification report

Evidence supplied by owner/local coding agent on 2026-11-25. Reviewed code: a35e5ebdae514f6ee52d343f963a72d686e28f65. Tracking commit: e256858ad3c9bafa140476df92cd2d6765c3eca0 (confirmed pushed). CI for reviewed code: https://github.com/TANISH-88/career-platform/actions/runs/45492434617; all three jobs independently confirmed successful.

## Local setup and bootstrap

Working tree initially clean; fast-forward sync from 818b198 to a35e5eb. Existing persistent SQLite database mlflow.db (225,280 bytes before changes), experiment career-prediction and four prior runs preserved.

Commands (PowerShell, local repository root; path normalized for portability):
```powershell
$env:MLFLOW_TRACKING_URI="sqlite:///C:/Users/Tanish/p4/mlflow.db"
backend\fastapi\venv\Scripts\python.exe ml-training/train.py bootstrap --register --output ml-training/m3-output
```

Reported terminal output:
```text
Successfully registered model 'career-rf-m3-champion'.
Created version '1' of model 'career-rf-m3-champion'.
Successfully registered model 'career-rf-legacy'.
Created version '1' of model 'career-rf-legacy'.
[PARITY] Fixture rows: 160
[PARITY] Max probability difference (pipeline vs serving): 0.00e+00
[PARITY] Top-1 role mismatches: 0/160
[PARITY] Top-3 role/probability mismatches: 0/480
[PARITY OK] pipeline.pkl and PredictorService produce identical outputs.
```

Champion holdout accuracy: 0.1972972972972973; macro-F1: 0.16639113268278288. Champion pipeline SHA256: a1d2f27979443f65536cf4c22172b40c8f23e4118f6a3a5eaec3df083691aa9e.

## Independent fresh-process persistence check (local agent evidence)

| Model | Version | Status | Run ID |
|---|---|---|---|
| career-rf-m3-champion | 1 | READY | 360767520c804bcbb70f67d6c73d5dc2 |
| career-rf-legacy | 1 | READY | 688561cc262042f48a07f29a233183f5 |

Both registered model sources existed after restarting Python, with MLmodel, model.pkl, conda.yaml, python_env.yaml and requirements.txt. Champion model.pkl: 5,760,501 bytes; legacy model.pkl: 12,569,814 bytes.

```text
CAREER_PREDICTION_RUN_COUNT: 6
PRIOR_DATA_INTACT: True (4 prior runs + career-rf v1,v2,v3 preserved)
CHAMPION_RELOADED_HOLDOUT: accuracy=0.1972972972972973 macro_f1=0.16639113268278288 ref_match=True local_match=True
LEGACY_RELOADED_PARITY: rows=160 max_diff=0.00e+00 exact_match=True
```

Reloaded champion predictions matched all 740 frozen reference rows. Champion tags identify development personas only, fixed recipe and frozen data/manifest hashes. Historical model has no unseen-persona score; its comparison tag explicitly says not comparable. Existing legacy registry career-rf v1–v3 retained. MLflow warned about missing input examples/signatures; registration and reload succeeded.

## Restrictions and outstanding approval

Local agent reports no frozen data/reference changes, no serving-model changes, no deployment, no merge, and no M4 work. Generated databases, artifact directories and binaries were ignored; local tracking commit changes documentation only. CP15 persistent registration supported by supplied local evidence, not independently executed by ChatGPT. CP17/18 corrections have passing technical evidence in independent-review.md. Tracking remains 16/30 until reviewer closes CP17/18. Final Claude approval pending.
