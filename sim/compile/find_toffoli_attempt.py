"""
Search attempt for a TOFFOLI-like gadget: flip T iff (A==1 AND B==1),
leaving A and B unchanged, over {F,N,P,CN,CP}.

This is the gate the TM-step construction actually needs (state-bit AND
symbol-bit -> conditional write/move), and unlike CNOT it was NOT found.
This script reproduces a *bounded* version of the search (small enough to
finish in well under the 2-CPU / few-minute budget this session had); design
.md also reports a larger, longer-running attempt (window=6, dual rail on
all three of A,B,T, no spacer, max word length 30, up to 40,000,000 BFS
states) that was still exploring depth ~14 (10.9M states visited, all at
or below depth 14) when it was stopped for time -- i.e. inconclusive, not
a proof of nonexistence. Both runs are negative results within the explored
bounds, reported honestly in design.md as the open obstruction.
"""
import time
from gadget_search import search, verify


def toffoli_target(assign):
    return {'A': assign['A'], 'B': assign['B'], 'T': assign['T'] ^ (assign['A'] & assign['B'])}


configs = [
    ("A,B,T all dual, no spacer",
     [('dual', 'A', 'T'), ('dual', 'B', 'T'), ('dual', 'T', 'T')]),
    ("A,B,T all dual, 1 spacer(0) before T",
     [('dual', 'A', 'T'), ('dual', 'B', 'T'), ('const', 0), ('dual', 'T', 'T')]),
    ("A,B,T single-rail (no dual), no spacer",
     [('free', 'A'), ('free', 'B'), ('free', 'T')]),
]

MAXLEN = 16
MAXVIS = 400_000
for name, layout in configs:
    t0 = time.time()
    res, nv = search(layout, 0, toffoli_target, MAXLEN, max_visited=MAXVIS)
    dt = time.time() - t0
    print(f"{name}: found={res is not None} visited={nv} time={dt:.1f}s (len<= {MAXLEN}, cap={MAXVIS})")
    if res is not None:
        print("  word:", ''.join(res), "verify:", verify(layout, 0, toffoli_target, res))
