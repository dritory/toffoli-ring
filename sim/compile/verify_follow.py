"""Milestone 2 verification: the pointer follows the head, one pass = one TM step.

R level: after every pass the WHOLE ring must equal, cell for cell, the tape
expected from tm.py's reference config (symbols, the state token in the new
head group's arrL/arrR/q, every other cell at rest), and the pointer must sit
at head*G. Before the conditional move of every pass, every permanent
constant in the whole ring is audited (the chains read them).
Level 0: the pass word expanded with MACRO runs on the dual-rail tape with
run_l0 (copied verbatim from verify_level0_independent.py, whose import runs
its main), compared with the R run after every pass.
"""
import sys, random, time
import tm as TM
import follow as F
from verify_sweep import rules_by_state, run_word

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


def expected_tape(states, n_groups, cfg, kind):
    """kind: 'q' (token in q), 'arrL' or 'arrR' (token still in arrival cell)."""
    n = len(states); G = F.group_width(n)
    full = []
    for g in range(n_groups):
        blk = F.group_rest_tape(n)
        blk[F.S_BLOCK['s']] = cfg.tape[g]
        blk[F.S_BLOCK['sbar']] = 1 - cfg.tape[g]
        if g == cfg.head:
            j = states.index(cfg.state)
            bar = {'q': 'qbar', 'arrL': 'arrLbar', 'arrR': 'arrRbar'}[kind]
            blk[F.cell_offset(j, kind)] = 1
            blk[F.cell_offset(j, bar)] = 0
        full.extend(blk)
    return full


def audit_consts(tape, n, n_groups, G):
    ct = F.const_table(n)
    for g in range(n_groups):
        for off, v in ct.items():
            assert tape[g * G + off] == v, ("constant drifted", g, off)


def run(tm_obj, n_groups, max_steps, io_hook=None, level0=True):
    states = tm_obj.states; n = len(states)
    rbs = rules_by_state(tm_obj)
    word, G, ring = F.compile_pass(states, rbs, n_groups)
    gword, _, _ = F.compile_group_program(states, rbs, n_groups)
    chain = word[len(gword):]
    assert word[:len(gword)] == gword
    l0 = ''.join(MACRO[x] for x in word)
    ref = TM.TMConfig(tape=[0] * n_groups, head=0, state=tm_obj.start_state)
    kind = 'q'
    tape = expected_tape(states, n_groups, ref, kind)
    phys = []
    for b in tape: phys += [b, 1 - b]
    p = 0; passes = 0; l0_checks = 0
    idle = 0  # extra passes run after halting: the HALT token must just idle
    while passes < max_steps and idle < 3:
        if tm_obj.is_halting(ref.state): idle += 1
        if io_hook: io_hook(ref, tape, phys, G)
        p_prev = p
        # R level, in two halves so the constants can be audited mid-pass
        tape, p1 = run_word(gword, tape, p, ring)
        assert p1 == p
        audit_consts(tape, n, n_groups, G)
        tape, p = run_word(chain, tape, p, ring)
        # reference step
        _, d, _ = tm_obj.trans[(ref.state, ref.tape[ref.head])]
        TM.tm_step(tm_obj, ref)
        kind = {+1: 'arrL', -1: 'arrR', 0: 'q'}[d]
        assert p == ref.head * G, ("pointer", passes, p, ref.head * G)
        assert tape == expected_tape(states, n_groups, ref, kind), ("tape", passes)
        if level0:
            pp = run_l0(l0, phys, 2 * p_prev)
            assert pp == 2 * p, ("level-0 pointer", passes, pp, 2 * p)
            assert all(phys[2*i] == tape[i] and phys[2*i+1] == 1 - tape[i]
                       for i in range(ring)), ("level-0 tape", passes)
            l0_checks += 1
        passes += 1
    return dict(G=G, R_len=len(word), l0_ticks=len(l0), passes=passes, idle_after_halt=idle, l0_checks=l0_checks,
                halted=tm_obj.is_halting(ref.state), ref=ref)


def main():
    rng = random.Random(12345)

    def echo_io(ref, tape, phys, G):
        # poke a fresh input bit into group 0's symbol before every READ
        if ref.state == 'READ' and ref.head == 0:
            b = rng.randint(0, 1)
            ref.tape[0] = b
            for i, v in ((F.S_BLOCK['s'], b), (F.S_BLOCK['sbar'], 1 - b)):
                tape[i] = v; phys[2*i] = v; phys[2*i+1] = 1 - v

    level0 = '--no-l0' not in sys.argv
    for name, mk, steps, hook in (("counter", lambda: TM.make_counter_tm(3), 300, None),
                                  ("echo", TM.make_echo_tm, 50, echo_io),
                                  ("BB(2,2)", TM.make_bb22_tm, 1000, None)):
        for ng in (12, 24, 48):
            t0 = time.time()
            r = run(mk(), ng, steps, hook, level0)
            ref = r.pop('ref')
            print(name, ng, r, "tape_ones", sum(ref.tape), "state", ref.state,
                  "%.0fs" % (time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
