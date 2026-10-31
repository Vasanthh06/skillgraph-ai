# ml/
PyTorch Two-Tower and SASRec models plus pure-Python data prep, ranking and evaluation.

**Status:** model code written but untrained and untested (no torch in the authoring sandbox, no real activity data). The running app uses rules plus a recency heuristic; `/recommendations` reports this under `model_status`.
Pure modules (build_dataset, rank, metrics) are tested in tests/test_ml_pure.py.
