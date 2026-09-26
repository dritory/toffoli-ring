"""
Milestone 1 assembly + verification: compiles the sweep architecture
(sweep.py) for the three test machines (tm.py) and checks it group by group
against the direct TM simulator, and also checks a handful of full level-0
sweeps for the counter, per the task.
"""
import sys
import itertools
import random

import tm as TM
import sweep as SW
import level0 as L0
import level1 as L1


def rules_by_state(t: TM.TM):
    out = {}
    for (q, sym), (nsym, d, nq) in t.trans.items():
        out.setdefault(q, {})[sym] = (nsym, d, nq)
    return out


def step_cyclic(letter, tape, p, n):
    """Same R semantics as gadget_search.step_raw, but on a genuinely
    cyclic tape (wraps mod n) instead of returning None out of bounds --
    this is level 1 (R) on the task's actual cyclic hardware, not a
    bounded search window."""
    if letter == 'F':
        tape[p] ^= 1
        return p
    if letter == 'N':
        return (p + 1) % n
    if letter == 'P':
        return (p - 1) % n
    if letter == 'CN':
        return (p + 1) % n if tape[p] == 1 else p
    if letter == 'CP':
        return (p - 1) % n if tape[p] == 1 else p
    raise ValueError(letter)


def run_word(word, tape, p, ring_size):
    cur = list(tape)
    for letter in word:
        p = step_cyclic(letter, cur, p, ring_size)
    return cur, p


def build_initial_tape(states, n_groups, tm_tape, head, state):
    n = len(states)
    G = SW.group_width(n)
    full = []
    for g in range(n_groups):
        blk = SW.group_rest_tape(n)
        blk[SW.S_BLOCK['s']] = tm_tape[g]
        blk[SW.S_BLOCK['sbar']] = 1 - tm_tape[g]
        if g == head:
            j = states.index(state)
            blk[SW.q_offset(j)] = 1
            blk[SW.cell_offset(j, 'qbar')] = 0
        full.extend(blk)
    return full, G


def decode(tape, states, n_groups, G):
    """Returns (symbol_tape, active, hot) where hot lists every one-hot
    'the state token is here' bit found -- q_j itself, or (between the
    write into a neighbour and that neighbour's own next visit's phase-1
    merge) one of its dual-rail arrival cells, which represents exactly
    the same logical state. `active` is (group, state) if exactly one such
    bit is hot across the whole ring, else None. Also sanity-checks every
    dual-rail pair it looks at along the way."""
    n = len(states)
    symtape = []
    hot = []
    for g in range(n_groups):
        base = g * G
        s = tape[base + SW.S_BLOCK['s']]
        sbar = tape[base + SW.S_BLOCK['sbar']]
        assert sbar == 1 - s, f"s/sbar invariant broken at group {g}"
        symtape.append(s)
        for j in range(n):
            q = tape[base + SW.q_offset(j)]
            qbar = tape[base + SW.cell_offset(j, 'qbar')]
            assert qbar == 1 - q, f"q/qbar invariant broken at group {g} state {j}"
            if q == 1:
                hot.append((g, j, 'q'))
            for arr, arrbar in (('arrL', 'arrLbar'), ('arrR', 'arrRbar')):
                a = tape[base + SW.cell_offset(j, arr)]
                abar = tape[base + SW.cell_offset(j, arrbar)]
                assert abar == 1 - a, (
                    f"{arr}/{arrbar} invariant broken at group {g} state {j}")
                if a == 1:
                    hot.append((g, j, arr))
    active = None
    if len(hot) == 1:
        g, j, kind = hot[0]
        active = (g, states[j])
    return symtape, active, hot


def check_scratch_at_rest(tape, states, n_groups, G, skip_group=None):
    """Every cell that's supposed to be a stable constant, or a scratch
    cell that should be back at its rest value between passes, is checked
    here -- this is the 'assert exactly the expected cells changed'
    discipline the task asks for, applied at the per-sweep granularity."""
    n = len(states)
    rest_block = SW.group_rest_tape(n)
    for g in range(n_groups):
        if g == skip_group:
            continue
        base = g * G
        for name in ['s_const1', 'flip_mk_far', 'flip_mk_mid', 'flip_mk_near']:
            off = SW.S_BLOCK[name]
            assert tape[base + off] == SW.S_REST[name], (
                f"group {g} s-block cell {name} drifted from its rest value")
        for j in range(n):
            for name in ['wm_far', 'wm_mid', 'wm_near',
                         'b1', 'sp2', 'sp3', 'g0', 'fire', 'g1', 'firebar',
                         'sp8', 'sp9', 'm0', 'm1', 'm2',
                         'arrL_const1', 'arrL', 'arrL_gap', 'arrLbar',
                         'arrL_mk0', 'arrL_mk1', 'arrL_mk2',
                         'arrR_mk_far', 'arrR_mk_mid', 'arrR_mk_near',
                         'arrRbar', 'arrR_gap', 'arrR']:
                off = SW.cell_offset(j, name)
                want = rest_block[off]
                got = tape[base + off]
                if name in ('wm_far', 'wm_mid', 'wm_near',
                            'sp2', 'g0', 'fire', 'g1', 'sp8', 'm0', 'm1', 'm2',
                            'arrL_const1', 'arrR_gap',
                            'arrL_mk0', 'arrL_mk1', 'arrL_mk2',
                            'arrR_mk_far', 'arrR_mk_mid', 'arrR_mk_near'):
                    assert got == want, (
                        f"group {g} state {j} cell {name} drifted from its "
                        f"rest/constant value: got {got} want {want}")


def verify_tm(tm_obj: TM.TM, n_groups: int, n_steps: int, io_group=None,
              io_hook=None, verbose=False):
    states = tm_obj.states
    rbs = rules_by_state(tm_obj)
    word, G, ring_size = SW.compile_group_program(states, rbs, n_groups)

    cfg = TM.TMConfig(tape=[0] * n_groups, head=0, state=tm_obj.start_state)
    if io_hook:
        io_hook(cfg)

    tape, G2 = build_initial_tape(states, n_groups, cfg.tape, cfg.head, cfg.state)
    assert G2 == G
    assert len(tape) == ring_size

    ref = cfg.copy()
    steps_done = 0
    halted = False
    checks = 0
    MAX_STEPS_PER_VISIT = 8  # generous bound on how many TM steps can be
                              # folded into one group's visit (compute+use
                              # re-firing a freshly-merged arrival, chained
                              # any number of times by direction=+1 hops)
    MAX_SWEEPS = 4 * (n_steps + n_groups) + 50  # safety cap, not a tuning knob

    sweeps = 0
    visits_since_step = 0
    visits_per_step = []  # group-visits consumed to produce each TM step
    total_visits = 0
    while steps_done < n_steps and not halted and sweeps < MAX_SWEEPS:
        sweeps += 1
        for g in range(n_groups):
            if io_hook and g == io_group:
                io_hook(ref, live_tape=tape, G=G, group=g)
            tape, p = run_word(word, tape, g * G, ring_size)
            # advance to next group's canonical entry (unconditional N^G)
            tape, p = run_word(['N'] * G, tape, p, ring_size)
            visits_since_step += 1
            total_visits += 1
            symtape, active, hot = decode(tape, states, n_groups, G)
            check_scratch_at_rest(tape, states, n_groups, G)
            assert len(hot) <= 1, f"more than one state token hot: {hot}"
            if active is None:
                assert not tm_obj.is_halting(ref.state), (
                    "halted state's token vanished instead of idling")
                continue
            ag, astate = active
            if (ag, astate) == (ref.head, ref.state) and symtape == ref.tape:
                continue  # no TM step happened yet (or head hasn't moved)
            # One or more TM steps happened (a direction=+1 chain can fire
            # more than once within a single group visit): replay tm_step
            # on the reference until it catches up, and require an exact
            # match at that point (not just "eventually").
            matched = False
            for _ in range(MAX_STEPS_PER_VISIT):
                if tm_obj.is_halting(ref.state):
                    break
                TM.tm_step(tm_obj, ref)
                checks += 1
                steps_done += 1
                visits_per_step.append(visits_since_step)
                visits_since_step = 0
                if verbose:
                    print(f"  step {steps_done}: state={ref.state} head={ref.head} tape={ref.tape}")
                if (ag, astate) == (ref.head, ref.state) and symtape == ref.tape:
                    matched = True
                    break
            if not matched:
                raise AssertionError(
                    f"mismatch after group {g}'s visit: "
                    f"compiled=({ag},{astate},{symtape}) "
                    f"reference stuck at ({ref.head},{ref.state},{ref.tape})")
            if tm_obj.is_halting(ref.state):
                halted = True
                break
        if halted:
            break
    assert sweeps < MAX_SWEEPS, "hit the sweep safety cap without progress"
    stats = dict(word=word, G=G, ring_size=ring_size, n_groups=n_groups,
                 visits_per_step=visits_per_step, total_visits=total_visits,
                 sweeps=sweeps)
    return steps_done, checks, halted, ref, stats


L0_TICKS = {'F': 3, 'N': 6, 'P': 12, 'CN': 6, 'CP': 12}


def level0_len(r_word):
    return sum(L0_TICKS[letter] for letter in r_word)


def report_stats(name, tm_obj, n_groups, n_steps, io_group=None, io_hook=None):
    steps, checks, halted, ref, stats = verify_tm(
        tm_obj, n_groups=n_groups, n_steps=n_steps,
        io_group=io_group, io_hook=io_hook, verbose=False)
    G = stats['G']
    per_group_r_len = len(stats['word']) + G  # + the unconditional N^G
    per_group_l0_ticks = level0_len(stats['word']) + G * L0_TICKS['N']
    r_pass_len = per_group_r_len * n_groups
    l0_pass_len = per_group_l0_ticks * n_groups
    vps = stats['visits_per_step']
    avg_ticks = (per_group_l0_ticks * stats['total_visits'] / steps) if steps else float('nan')
    worst_ticks = (max(vps) * per_group_l0_ticks) if vps else float('nan')
    avg_visits = (stats['total_visits'] / steps) if steps else float('nan')
    worst_visits = max(vps) if vps else float('nan')
    return dict(name=name, n_states=len(tm_obj.states), G=G,
                r_pass_len=r_pass_len, l0_pass_len=l0_pass_len,
                steps=steps, checks=checks, halted=halted,
                avg_ticks=avg_ticks, worst_ticks=worst_ticks,
                avg_visits=avg_visits, worst_visits=worst_visits,
                sweeps=stats['sweeps'], ref=ref)


if __name__ == "__main__":
    print("=== tiny synthetic 2-state smoke test (bidirectional, not one of the 3 task machines) ===")
    tiny = TM.TM(
        states=["A", "B"], halt_states=[],
        trans={
            ("A", 0): (1, +1, "B"), ("A", 1): (0, -1, "B"),
            ("B", 0): (1, -1, "A"), ("B", 1): (0, +1, "A"),
        },
        start_state="A",
    )
    steps, checks, halted, ref, stats = verify_tm(tiny, n_groups=4, n_steps=30, verbose=False)
    print(f"steps={steps} checks={checks} halted={halted}")

    print()
    print("=== the three task test machines ===")

    r_counter = report_stats("counter (L=3)", TM.make_counter_tm(3), n_groups=3, n_steps=300)
    print(r_counter['name'], {k: v for k, v in r_counter.items() if k not in ('ref',)})

    echo_tm = TM.make_echo_tm()
    rng = random.Random(12345)

    def echo_io(ref, live_tape=None, G=None, group=None):
        if live_tape is None:
            ref.tape[0] = rng.randint(0, 1)
            return
        if ref.state == 'READ':
            b = rng.randint(0, 1)
            ref.tape[0] = b
            live_tape[SW.S_BLOCK['s']] = b
            live_tape[SW.S_BLOCK['sbar']] = 1 - b

    r_echo = report_stats("echo (n_groups=2)", echo_tm, n_groups=2, n_steps=50,
                          io_group=0, io_hook=echo_io)
    print(r_echo['name'], {k: v for k, v in r_echo.items() if k not in ('ref',)})

    r_bb = report_stats("BB(2,2) (n_groups=12)", TM.make_bb22_tm(), n_groups=12, n_steps=20)
    print(r_bb['name'], {k: v for k, v in r_bb.items() if k not in ('ref',)})
    print("final BB tape", r_bb['ref'].tape, "ones", sum(r_bb['ref'].tape), "state", r_bb['ref'].state)
