"""Independent hardware-level check of the head-following compiler (follow.py).

Takes only the compiled pass word and the cell layout from follow.py. Runs it on a
level-0 A/B simulator written here from the hardware spec, decodes the TM symbol and
head after every pass, and compares with tm.py's direct Turing machine. One pass must
be exactly one TM step, starting and ending with the pointer on the head group.
"""
import sys, random
import tm as TM
import follow as FW

MACRO = {'F': 'ABB', 'N': 'ABBAAA', 'P': 'BAABBBABBABB', 'CN': 'ABBAAB', 'CP': 'ABBABABAABBB'}

def l0_pass(prog, phys, p):
    n = len(phys); flag = 0
    for ch in prog:
        if flag:
            flag = 0; continue
        phys[p] ^= 1
        flag = phys[p] == 0
        p = (p + 1) % n if ch == 'A' else (p - 1) % n
    assert not flag
    return p

def rules(t):
    out = {s: {} for s in t.states}
    for (s, v), r in t.trans.items(): out[s][v] = r
    return out

def check(t, n_groups, n_steps, poke=None):
    st = t.states; n = len(st)
    word = FW.compile_pass(st, rules(t), n_groups)
    word = word[0] if isinstance(word, tuple) else word
    G = FW.group_width(n); ring = G * n_groups
    l0 = ''.join(MACRO[x] for x in word)
    ref = TM.TMConfig(tape=[0] * n_groups, head=0, state=t.start_state)
    logical = []
    for g in range(n_groups):
        blk = FW.group_rest_tape(n)
        blk[FW.S_BLOCK['s']] = ref.tape[g]; blk[FW.S_BLOCK['sbar']] = 1 - ref.tape[g]
        if g == ref.head:
            j = st.index(ref.state); blk[FW.q_offset(j)] = 1; blk[FW.cell_offset(j, 'qbar')] = 0
        logical += blk
    phys = []
    for b in logical: phys += [b, 1 - b]
    p = 2 * ref.head * G
    for step in range(n_steps):
        if t.is_halting(ref.state): break
        if poke:
            bit = poke(ref)
            if bit is not None:
                s = 2 * (0 * G + FW.S_BLOCK['s']); phys[s] = bit; phys[s + 1] = 1 - bit
        p = l0_pass(l0, phys, p)
        TM.tm_step(t, ref)
        sym = [phys[2 * (g * G + FW.S_BLOCK['s'])] for g in range(n_groups)]
        assert sym == ref.tape, (step, sym, ref.tape)
        assert p == 2 * ref.head * G, (step, p, ref.head)
        j = st.index(ref.state)
        hot = [(g, k, name) for g in range(n_groups) for k in range(n) for name in ('q', 'arrL', 'arrR')
               if phys[2 * (g * G + (FW.q_offset(k) if name == 'q' else FW.cell_offset(k, name)))] == 1]
        assert hot and all((g, st[k]) == (ref.head, ref.state) for g, k, _ in hot), (step, "state token", hot, ref.head, ref.state)
        assert all(phys[2 * i] != phys[2 * i + 1] for i in range(ring)), (step, "dual rail broken")
    return len(l0), step + 1, ref

for ng in (12, 24, 48):
    L, s, ref = check(TM.make_counter_tm(3), ng, 300)
    print(f"counter  groups={ng:2d} ticks/step={L} steps={s} value={TM.counter_value(ref.tape)}")
    L, s, ref = check(TM.make_bb22_tm(), ng, 50)
    print(f"BB(2,2)  groups={ng:2d} ticks/step={L} steps={s} ones={sum(ref.tape)} state={ref.state}")
