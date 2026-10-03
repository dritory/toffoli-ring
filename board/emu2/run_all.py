"""Run every check: unit tests, Python-vs-JS equivalence, program checks, measurements, listings."""
import sys, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
steps = [["tests/test_unit.py"], ["tests/test_equiv.py", "40"], ["tests/test_programs_equiv.py"],
         ["programs/check_snake.py"], ["programs/check_pong.py"], ["programs/check_life.py"],
         ["programs/check_scroll.py"], ["programs/check_bf.py"], ["programs/check_raycast.py"], ["make_listings.py"]]
if "--measure" in sys.argv: steps.append(["measure.py"])
for s in steps:
    print("==", " ".join(s), flush=True)
    r = subprocess.run([sys.executable] + s, cwd=HERE)
    if r.returncode: sys.exit("FAILED: " + " ".join(s))
print("all checks passed")
