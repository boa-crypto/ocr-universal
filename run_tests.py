#!/usr/bin/env python3
"""Lance pytest et écrit le résultat dans tests/_last_run.log."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
env = dict(os.environ)
env["PYTHONPATH"] = f"{ROOT}/src:{ROOT}/tests:." + os.pathsep + env.get("PYTHONPATH", "")
args = sys.argv[1:] or ["tests/", "-q"]
out = os.path.join(ROOT, "tests", "_last_run.log")
with open(out, "w", encoding="utf-8") as f:
    code = subprocess.call([sys.executable, "-m", "pytest"] + args,
                           cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT)
with open(out, encoding="utf-8") as f:
    text = f.read()
print(text[-3000:])
print(f"── code de retour pytest : {code} ──")
sys.exit(code)
