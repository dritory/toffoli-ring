"""
Verified R-level gates used by the TM-step compiler.

Each gate is given as (word, layout, start_idx, description) where `word`
is a list of R letters ('F','N','P','CN','CP'), `layout` is a
gadget_search.py-style layout (list of ('free', name) / ('const', v) /
('dual', name, orientation)) describing the window of logical bits the
gate acts on relative to the pointer's starting offset `start_idx`, and the
gate's documented postcondition is checked by `verify_all()` below against
every valuation of the window's free names.
"""
from gadget_search import step_raw, build_valuations, expand_layout


def parse_cd(word_str):
    """'CCNNNNFNF...' -> ['CN','CN','N',...] using the orchestrator's
    shorthand C=CN, D=CP, F=F, N=N, P=P (one letter per R-word letter)."""
    m = {'F': 'F', 'N': 'N', 'P': 'P', 'C': 'CN', 'D': 'CP'}
    return [m[ch] for ch in word_str]


def parse_r(word_str):
    """Parses a space/comma-free string already written in R's own token
    spelling ('F','N','P','CN','CP' concatenated, 'CN'/'CP' two chars)."""
    out = []
    i = 0
    while i < len(word_str):
        if word_str[i:i + 2] in ('CN', 'CP'):
            out.append(word_str[i:i + 2])
            i += 2
        else:
            out.append(word_str[i])
            i += 1
    return out


# --- CNOT(A -> T): flip T iff A==1, A unchanged. dual rail both sides. -----
CNOT = dict(
    word=parse_r("NFCNNFPPCPNFNF"),
    layout=[('dual', 'A', 'T'), ('dual', 'T', 'T')],
    start_idx=0,
    target=lambda a: {'A': a['A'], 'T': a['T'] ^ a['A']},
    note="found by BFS, sim/compile/find_cnot.py, 12 letters, window 4",
)

# --- TOFFOLI(A,B -> T): flip T iff A==1 and B==1 (dual rail T). -----------
# Layout relative to the pointer at a (offset 0):
#   0:a 1:b 2,3:spare(untouched) 4:g0(scratch) 5:t 6:g1(scratch)
#   7:tbar (dual-rail partner of t, 2 apart) 8,9:spare 10,11,12: consts 0,1,1
# Supplied by the orchestrator; independently re-verified here on all 512
# valuations of (a,b,spare1,spare2,g0,t,g1,spare3,spare4) -- i.e. g0/g1/the
# spares may start at *any* value and come back unchanged, not just 0.
TOFF = dict(
    word=parse_cd("CCNNNNFNFNNNNNDDPPPPPPPPPP" "CNNNNFNFNNNNNDDPPPPPPPPPP"),
    layout=[('free', 'a'), ('free', 'b'), ('free', 'sp1'), ('free', 'sp2'),
            ('free', 'g0'), ('free', 't'), ('free', 'g1'),
            ('free', 'tbar'),  # kept as an independent free bit here; see
                                # verify_toffoli() below for the dual-rail
                                # (tbar == 1-t) check, which gadget_search's
                                # generic 'dual' layout type doesn't need
                                # since we verify this gate with a bespoke
                                # harness instead of gadget_search.search().
            ('free', 'sp3'), ('free', 'sp4'),
            ('const', 0), ('const', 1), ('const', 1)],
    start_idx=0,
    note=("supplied by the orchestrator; independently re-verified, "
          "51 letters, window 13, all 512 valuations (a,b,spares,g0,t,g1 "
          "free, tbar constrained = 1-t at input) pass -- see verify_toffoli()"),
)


# --- CLEAR(c): set c to 0 regardless of its value, dual rail. -------------
# Found by BFS (find_clear_dual.py) after a plain-constants-only search
# (find_clear.py, ~350 configs of 2-6 constant cells, all fully exhausted
# with no hit) came up empty -- exactly like CNOT, CLEAR needs dual rail,
# not extra constants: with c in dual rail (c, c-bar) alone (no markers at
# all), the tiny (2-valuation) BFS finds it in 21 states visited.
CLEAR = dict(
    word=parse_r("FNCPFCP"),
    layout=[('dual', 'c', 'T')],
    start_idx=0,
    target=lambda a: {'c': 0},
    note="found by BFS, sim/compile/find_clear_dual.py, 5 letters, window 2",
)


def verify_clear():
    layout = CLEAR['layout']
    phys, free_names, valuations = build_valuations(layout)
    total = fails = 0
    for assign, w in valuations:
        total += 1
        cur = list(w)
        p = CLEAR['start_idx']
        ok = True
        for letter in CLEAR['word']:
            r = step_raw(letter, cur, p, len(w))
            if r is None:
                ok = False
                break
            p = r
        want = [0, 1]  # c=0, cbar=1
        if not ok or cur != want or p != 0:
            fails += 1
    return total, fails


def verify_toffoli():
    import itertools
    word = TOFF['word']
    N = 13
    total = fails = 0
    for a, b, sp1, sp2, g0, t, g1, sp3, sp4 in itertools.product([0, 1], repeat=9):
        total += 1
        w = [a, b, sp1, sp2, g0, t, g1, 1 - t, sp3, sp4, 0, 1, 1]
        cur = list(w)
        p = 0
        ok = True
        for letter in word:
            r = step_raw(letter, cur, p, N)
            if r is None:
                ok = False
                break
            p = r
        want_t = t ^ (a & b)
        want = list(w)
        want[5] = want_t
        want[7] = 1 - want_t
        if not ok or cur != want or p != 0:
            fails += 1
    return total, fails


def verify_cnot():
    from gadget_search import build_valuations, make_goal_window, step_raw
    layout = CNOT['layout']
    phys, free_names, valuations = build_valuations(layout)
    total = fails = 0
    for assign, w in valuations:
        total += 1
        cur = list(w)
        p = CNOT['start_idx']
        ok = True
        for letter in CNOT['word']:
            r = step_raw(letter, cur, p, len(w))
            if r is None:
                ok = False
                break
            p = r
        want = make_goal_window(phys, CNOT['target'](assign))
        if not ok or cur != list(want) or p != 2:
            fails += 1
    return total, fails


if __name__ == "__main__":
    t, f = verify_cnot()
    print(f"CNOT:  {t-f}/{t} valuations passed  (len={len(CNOT['word'])}, window=4)")
    t, f = verify_clear()
    print(f"CLEAR: {t-f}/{t} valuations passed  (len={len(CLEAR['word'])}, window=2)")
    t, f = verify_toffoli()
    print(f"TOFF:  {t-f}/{t} valuations passed  (len={len(TOFF['word'])}, window=13)")
