"""Run every dependency-free test module without pytest:   python tests/run_pure.py   (from the repo root)"""
import importlib, sys, traceback
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root / "backend"), str(root), str(root / "tests")]
ok = bad = 0
for mod in ("test_engine", "test_ml_pure", "test_isolation_static"):
    m = importlib.import_module(mod)
    for name in sorted(n for n in dir(m) if n.startswith("test_")):
        try:
            getattr(m, name)(); ok += 1
        except Exception:
            bad += 1; print("FAIL", mod, name); traceback.print_exc()
print(f"{ok} passed, {bad} failed"); sys.exit(1 if bad else 0)
