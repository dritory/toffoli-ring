"""Independent level-0 check of the sweep compiler.

Runs the compiled programs on the physical two-instruction machine (A/B letters,
skip flag, dual-rail tape) with a simulator written from the hardware spec only,
and compares the decoded logical tape with the R-level run after every group visit.
Uses sweep.py only to obtain the compiled R word and verify_sweep.py only for the
R-level reference run and the initial tape.
"""
import sys
import tm as TM
import sweep as SW
import verify_sweep as VS

MACRO = {'F': 'ABB', 'N': 'ABBAAA', 'P': 'BAABBBABBABB', 'CN': 'ABBAAB', 'CP': 'ABBABABAABBB'}

def run_l0(prog, phys, p):
    n = len(phys); flag = 0
    for ch in prog:
        if flag:
            flag = 0; continue
        phys[p] ^= 1
        flag = 1 if phys[p] == 0 else 0
        p = (p + 1) % n if ch == 'A' else (p - 1) % n
    if flag:
        raise AssertionError("flag left set at end of group program")
    return p

def check(tm_obj, n_groups, max_visits, io_group=None, io_hook=None, label=""):
    states = tm_obj.states
    word, G, ring = SW.compile_group_program(states, VS.rules_by_state(tm_obj), n_groups)
    visit = word + ['N'] * G
    l0 = ''.join(MACRO[x] for x in visit)
    cfg = TM.TMConfig(tape=[0] * n_groups, head=0, state=tm_obj.start_state)
    if io_hook: io_hook(cfg)
    logical, _ = VS.build_initial_tape(states, n_groups, cfg.tape, cfg.head, cfg.state)
    phys = []
    for b in logical: phys += [b, 1 - b]
    ticks = 0; visits = 0; halted = False
    for v in range(max_visits):
        g = v % n_groups
        if io_hook and g == io_group:
            io_hook(cfg, live_tape=logical, G=G, group=g)
            for i, b in enumerate(logical): phys[2*i] = b; phys[2*i+1] = 1 - b
        logical, p_r = VS.run_word(visit, logical, g * G, ring)
        p_phys = run_l0(l0, phys, 2 * g * G)
        ticks += len(l0); visits += 1
        assert p_phys == 2 * p_r, (label, v, p_phys, p_r)
        assert all(phys[2*i] == logical[i] and phys[2*i+1] == 1 - logical[i] for i in range(ring)), (label, "tape mismatch at visit", v)
        symtape, active, hot = VS.decode(logical, states, n_groups, G)
        if active is None and hot == []:
            pass
        if active and tm_obj.is_halting(active[1]):
            halted = True; break
    return dict(label=label, visits=visits, ticks=ticks, halted=halted, G=G, l0_len=len(l0))

if False:
    bb = TM.bb22() if hasattr(TM, 'bb22') else None
    names = [n for n in dir(TM) if not n.startswith('_')]
    print("tm.py exports:", [n for n in names if n.islower()])

def main():
    import time
    t0 = time.time()
    r = check(TM.make_bb22_tm(), n_groups=12, max_visits=12 * 40, label="BB(2,2)")
    print(r, "%.0fs" % (time.time() - t0))
    t0 = time.time()
    r = check(TM.make_counter_tm(3), n_groups=3, max_visits=3 * 150, label="counter L=3")
    print(r, "%.0fs" % (time.time() - t0))

main()
