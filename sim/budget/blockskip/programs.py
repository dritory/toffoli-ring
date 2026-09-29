"""Hand-written normal-form programs for the block-skip ISA.  The ring is the
outer loop; all state (incl. data-pointer home) lives in data cells.  Blocks
`IFZ .. MARK` are pointer-neutral unless stated.  Each program runs on the
behavioural reference AND on the switch-level NMOS machine in lock step.

Two idioms (single skip flag => no nested blocks with a MARK in between):
 * chain: `IFZ a IFZ b .. MARK` = while-style AND chain to ONE mark.
 * two-cell AND gadget with resync (see TM section).
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'compile'))
import ref as R

def enc(prog): return [R.encode(m) for m in prog]

class Asm:
    """Pointer-tracking macro assembler over a cyclic data ring."""
    def __init__(self, home=0):
        self.p = []; self.pos = home
    def e(self, *ms): self.p += list(ms)
    def goto(self, c):
        d = c - self.pos
        self.p += (['NEXT'] * d) if d > 0 else (['PREV'] * -d)
        self.pos = c
    def cnot(self, c, t):            # t ^= c   (neutral)
        self.goto(c); self.e('IFZ'); self.goto(t); self.e('FLIP'); self.goto(c); self.e('MARK')
    def reset(self, c):              # c := 0   (neutral)
        self.goto(c); self.e('IFZ', 'FLIP', 'MARK')
    def setz(self, c):               # c ^= 1
        self.goto(c); self.e('FLIP')

# ------------------------------------------------------------------ programs
def counter_prog(width=8):
    """cells: [h=0, n0..n7], n = NOT bit (value = sum (1-n_i) 2^i).  Home = h.
    Chain `FLIP IFZ NEXT` per bit: carry continues iff n_i became 1.  The
    carry trail is all 1s, h is 0, so a chain of `IFZ PREV` walks home."""
    p = ['NEXT']
    for i in range(width - 1): p += ['FLIP', 'IFZ', 'NEXT']
    p += ['FLIP', 'MARK', 'PREV']
    p += ['IFZ', 'PREV'] * (width - 1)
    p += ['MARK']
    return p

def echo_prog():      # cells [out, in]; home = out.  out := in each pass
    return ['IFZ', 'FLIP', 'MARK', 'NEXT', 'IFZ', 'PREV', 'FLIP', 'NEXT', 'MARK', 'NEXT']

def copy_prog():      # cells [d0 s0 d1 s1 ...]; one bit per pass, advances 2
    return echo_prog()

# --------------------------------------------------------------- BB(2,2) TM
G = 9
NAMES = ['BL', 'T', 'Z', 'U', 'A', 'H', 'BR', 'W', 'DR']
DEFAULT = dict(zip(NAMES, [0, 1, 2, 3, 4, 5, 6, 7, 8]))
# shortest program over all 9! cell orders (subject to H = 2A-U): 262 instructions
LAYOUT = {'BL': 0, 'T': 5, 'Z': 3, 'U': 4, 'A': 6, 'H': 8, 'BR': 7, 'W': 2, 'DR': 1}

def and_gadget(a, c1, c2, z, h):
    """Z ^= c1 & c2, consuming c1 and c2.  Needs cell h == 1 at h = 2*c1 - c2
    and pointer neutral.  Two exits (c1 test failed / not) are resynced onto
    c1 by a step towards the sentinel and a conditional step back."""
    assert h == 2 * c1 - c2
    a.goto(c1); a.e('IFZ', 'FLIP'); a.goto(c2); a.e('IFZ', 'FLIP')
    a.goto(z); a.e('FLIP'); a.goto(c2); a.e('MARK')
    e = c1 - c2
    a.p += (['NEXT'] * e) if e > 0 else (['PREV'] * -e)
    a.e('IFZ')
    a.p += (['PREV'] * e) if e > 0 else (['NEXT'] * -e)
    a.e('MARK'); a.pos = c1

def bb22_prog(L=None):
    L = L or LAYOUT
    BL, T, Z, U, A, H, BR, W, DR = (L[n] for n in NAMES)
    a = Asm(home=T)
    a.cnot(A, W)                                   # W = A
    a.goto(U); a.e('FLIP'); a.cnot(T, U)           # u = not t
    and_gadget(a, A, U, Z, H)                      # Z = A & !t  (A0)
    a.cnot(Z, DR); a.cnot(Z, W); a.cnot(Z, T)      # Dr=A0, W=A1, t|=A0
    a.cnot(Z, BL + G)                              # B token -> right group
    a.reset(Z)
    a.cnot(W, BR - G)                              # A1: B token -> left group
    for src in (BL, BR):                           # B may have arrived either side
        a.cnot(src, A)
        a.reset(U); a.goto(U); a.e('FLIP'); a.cnot(T, U)
        and_gadget(a, A, U, Z, H)                  # Z ^= B & !t   (B0)
        a.reset(src)
    a.cnot(Z, T); a.cnot(Z, W)                     # t|=B0, W = A1^B0 = Dl
    a.cnot(Z, A - G)                               # A token -> left group
    a.reset(Z); a.reset(U)
    a.goto(DR); a.e('IFZ', 'FLIP'); a.e(*(['NEXT'] * G)); a.e('MARK'); a.pos = DR
    a.goto(W); a.e('IFZ', 'FLIP'); a.e(*(['PREV'] * G)); a.e('MARK'); a.pos = W
    a.goto(T)
    return a.p

def bb22_tape(ngroups=6, head=2, L=None):
    L = L or LAYOUT
    d = []
    for g in range(ngroups):
        c = [0] * G; c[L['H']] = 1
        if g == head: c[L['A']] = 1
        d += c
    return d, head * G + L['T']

def tm_view(data, ngroups, L=None):
    L = L or LAYOUT
    tape = [data[g * G + L['T']] for g in range(ngroups)]
    st, hd = 'HALT', None
    for g in range(ngroups):
        if data[g * G + L['A']]: st, hd = 'A', g
        if data[g * G + L['BL']] or data[g * G + L['BR']]: st, hd = 'B', g
    return tape, hd, st

# ------------------------------------------------------------------- running
def lockstep(machine, prog, data, dp, ticks, on_tick=None):
    """Run reference and switch-level machine in lock step, asserting equality
    of all outputs and of data/pointer each tick.  Returns final data, dp."""
    ring = enc(prog); n = len(ring); nd = len(data)
    dr, dc = list(data), list(data); dpr = dpc = dp; Sr = Sc = 0; pp = 0
    for t in range(ticks):
        a = R.tick(Sr, ring[pp], dr[dpr]); b = machine.tick(Sc, ring[pp], dc[dpc])
        assert tuple(a) == tuple(b), ('mismatch', t, a, b)
        if a[0]: dr[dpr] ^= 1; dc[dpc] ^= 1
        dpr = (dpr + a[1] - a[2]) % nd; dpc = (dpc + b[1] - b[2]) % nd
        Sr, Sc = a[3], b[3]; pp = (pp + 1) % n
        assert dr == dc and dpr == dpc
        if on_tick: on_tick(t, pp, dr, dpr)
    return dr, dpr, Sr
