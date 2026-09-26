import sys, time, json
sys.path.insert(0, "/home/user/toffoli-ring/sim/progdrum")
from gadget import step_row, run_to_fixed, pattern_to_bits, popcount_pattern, M_BLOCKS

def scan(k, P):
    M = M_BLOCKS * P
    survivors = []
    for pattern in range(1, 2 ** P - 1):
        bits = pattern_to_bits(pattern, P)
        prog_full = bits * M_BLOCKS
        bg0, r0 = run_to_fixed(prog_full, k, M, [0] * M, 4 * P)
        bg1, r1 = run_to_fixed(prog_full, k, M, [1] * M, 4 * P)
        if bg0 is not None or bg1 is not None:
            survivors.append((pattern, bg0, r0, bg1, r1))
    return survivors

if __name__ == "__main__":
    t0 = time.time()
    total = 0
    for k in (2, 3):
        for P in range(4, 15):
            s = scan(k, P)
            total += len(s)
            print(f"k={k} P={P}: {len(s)}/{2**P-2} survive", flush=True)
    print("total survivors", total, "time", time.time() - t0)
