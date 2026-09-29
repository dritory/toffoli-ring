"""FT4 gate library on encoding (x,1) (g=2: cell0 = x, cell1 = const 1), pointer rests on
cell0 of the current group.  Words come from gsearch/gate.py (exact for arbitrary
neighbour contents).  Composite Toffoli = CMOVK+ ; CNOT(0->+1) ; BACKL, layout
[spacer=0][x][y][t]."""
import itertools
from macro import B, run
FT4 = [B(('F','T0')), B(('P',)), B(('M',)), B((), True)]
FT, N, P, MK = '0', '1', '2', '3'
W = dict(
  NOT='03', RESET='003',
  CNOTp='1032023110320203',          # control at 0, target group +1
  CNOTm='2031013220310103',          # target group -1
  CMOVp='10320102231013',            # if x: x:=0, ptr += 1 group
  CMOVKp='030113', CMOVKm='030223',
  BACKL='2203022311',                # if left group ==1: ptr -= 1 group
  NEXT='11', PREV='22')
W['TOFF'] = W['CMOVKp'] + W['CNOTp'] + W['BACKL']
G = 2
def enc(xs):
    t = []
    for x in xs: t += [x, 1]
    return t
def apply(word, tape, ptr):
    S = 0; n = len(tape)
    for ch in word:
        b = FT4[int(ch)]
        t, p, S, ok = run(b, sum(v << i for i, v in enumerate(tape)), ptr, S, n)
        assert ok, 'out of window'
        tape = [(t >> i) & 1 for i in range(n)]; ptr = p
    assert S == 0
    return tape, ptr
def check(name, offs_groups, fn, dptr=0, pad=1, lo=None):
    """offs_groups: group offsets the gate reads; fn(dict off->bit) -> (dict off->newbit, dptr)."""
    lo = min(offs_groups + [0]) - pad; hi = max(offs_groups + [0]) + pad
    ng = hi - lo + 1; ok = True
    for xs in itertools.product((0, 1), repeat=ng):
        val = {o: xs[o - lo] for o in offs_groups}
        upd, dp = fn(val)
        xs2 = list(xs)
        for o, v in upd.items(): xs2[o - lo] = v
        tape, ptr = apply(W[name], enc(xs), -lo * G)
        if tape != enc(xs2) or ptr != (-lo + dp) * G: ok = False; break
    print(name, len(W[name]), 'ticks', 'OK' if ok else 'FAIL')
    return ok
if __name__ == '__main__':
    check('NOT', [0], lambda x: ({0: x[0]^1}, 0))
    check('RESET', [0], lambda x: ({0: 0}, 0))
    check('CNOTp', [0,1], lambda x: ({1: x[1]^x[0]}, 0))
    check('CNOTm', [0,-1], lambda x: ({-1: x[-1]^x[0]}, 0))
    check('CMOVp', [0], lambda x: ({0:0},1) if x[0] else ({},0))
    check('CMOVKp', [0], lambda x: ({},1) if x[0] else ({},0))
    check('CMOVKm', [0], lambda x: ({},-1) if x[0] else ({},0))
    check('BACKL', [-1,0], lambda x: ({},-1) if x[-1] else ({},0))
    check('NEXT', [0], lambda x: ({},1)); check('PREV', [0], lambda x: ({},-1))
    # Toffoli with spacer group (s=0) at offset -1: controls x@0,y@1, target t@2
    lo = -1 - 1; hi = 2 + 1; ok = True
    for xs in itertools.product((0, 1), repeat=hi - lo + 1):
        xs = list(xs); xs[-1 - lo] = 0                      # spacer = logical 0
        v = {o: xs[o - lo] for o in (-1, 0, 1, 2)}
        xs2 = list(xs); xs2[2 - lo] ^= v[0] & v[1]
        tape, ptr = apply(W['TOFF'], enc(xs), -lo * G)
        if tape != enc(xs2) or ptr != -lo * G: ok = False; break
    print('TOFF', len(W['TOFF']), 'ticks', 'OK' if ok else 'FAIL')
