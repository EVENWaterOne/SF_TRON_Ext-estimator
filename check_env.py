"""Environment availability check.
Run with Isaac Sim: & "E:\IsaacSim-5.1.0\python.bat" check_env.py
"""

import sys

checks = []

def check(name, fn):
    try:
        result = fn()
        checks.append((name, True, str(result)))
        print(f"  [OK] {name}: {result}")
    except Exception as e:
        checks.append((name, False, str(e)))
        print(f"  [FAIL] {name}: {e}")

print("=== Environment Check ===\n")

check("Python version", lambda: sys.version.split()[0])
check("PyTorch", lambda: __import__("torch").__version__)
check("PyTorch CUDA available", lambda: __import__("torch").cuda.is_available())
check("CUDA device", lambda: __import__("torch").cuda.get_device_name(0) if __import__("torch").cuda.is_available() else "N/A")
check("isaacsim", lambda: __import__("isaacsim"))
check("isaaclab", lambda: __import__("isaaclab"))

passed = sum(1 for _, ok, _ in checks if ok)
total = len(checks)
print(f"\n{passed}/{total} checks passed.")
if passed < total:
    print("Some checks failed — see above for details.")
    sys.exit(1)
