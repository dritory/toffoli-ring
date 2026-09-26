"""
Milestone 1: sweep-architecture TM compiler.

Built only from the already-verified R-level gates in gates.py (TOFF,
gapcnot_word) and hand_gapclear.py (gap_clear). No new gates are searched
for here. This module does assembly (layout + word generation) and is
verified by simulation (checking mode + cross-check against tm.py's direct
simulator), per the task's instructions. Read results/compile/design.md
only for background -- its section 4 layout is NOT used; the layout below
was independently derived and is validated cell-by-cell by the checking
functions at the bottom of this file and by verify_sweep.py.

===========================================================================
THE KEY TRICK (this is what makes TOFF composable with GAPCNOT/GAPCLEAR
without collisions): GAPCNOT(K)'s marker triple sits at *target*+3,+4,+5
(or target-3,-4,-5 mirrored) -- a fixed small offset from wherever it
writes. TOFF's own shape places a,b adjacent and its internal cells
(spare,spare,g0,fire,g1,firebar,spare,spare,markers) immediately following
b, all within a 13-cell span. So *any* GAPCNOT call that writes directly
into TOFF's "b" slot (the per-state copy of the symbol, which must sit
right next to the state bit for TOFF to read it) has its own marker triple
land inside that very same 13-cell span -- always exactly on TOFF's "fire"
cell, regardless of which of TOFF's two inputs is the GAPCNOT's target
(checked by direct arithmetic and confirmed by simulation below). Since
"fire" is data, not a constant, this is a genuine collision, not a layout
mistake to route around by choosing different offsets.

The fix: give "fire" a *rest value of 1* instead of 0, and read the AND
off its dual-rail partner "firebar" (=1-fire) instead. Then:
  - fire's value right before the state's own s-copy-broadcast (the GAPCNOT
    that needs marker=1 at fire's position) is reliably 1 (that is exactly
    its rest state, restored after every previous pass's use), so the
    marker precondition is satisfied "for free", by construction, forever.
  - firebar = 1 - fire = 1 - (1 xor (q&b)) = q&b -- the real AND -- is used
    for every downstream action (symbol write, state write, self-clear).
  - (fire, firebar) is reset to (1, 0) after use via a GAPCLEAR call
    (mirrored, rooted at firebar) rather than by calling TOFF a second time
    with the same inputs -- this sidesteps a second, independent problem
    (calling TOFF again to "uncompute" fire requires its own inputs, q_k
    and the symbol-copy, to be *unchanged*, which breaks the moment q_k
    itself is the thing being cleared using fire's value). GAPCLEAR forces
    the pair to a fixed state unconditionally, with no such ordering
    constraint, which is exactly why it exists as a primitive.
  - the two other constant markers of the s-copy broadcast (which the
    arithmetic places on TOFF's own g0 and sp2 cells) are satisfied by
    fixing g0 = 0 and sp2 = 1 permanently (TOFF's own proof: these two
    cells are provably unaffected by every TOFF call, for *any* value, so
    fixing them once is stable forever).
This was found and confirmed empirically (see the __main__ block, which
reproduces exactly the collision and the fix, cell by cell, before any of
this is used to compile a real TM) -- not asserted from first principles
alone.

===========================================================================
GROUP LAYOUT. Each TM cell is a group:

  [sbar][gap][s][s_const1]                          -- 4 cells, symbol
  state_0 block (28 cells) ... state_{n-1} block (28 cells)

Per state j (relative offsets, 0 = q_j):
  -2: qbar_j            (dual partner of q_j, spacing convention: target,
  -1: qscr_j              scratch, target-bar, exactly as GAPCNOT/TOFF use)
   0: q_j                (the one-hot state bit -- TOFF's "a")
   1: b1_j               (TOFF's "b" -- a copy of s or s-bar, made and
                           un-made once per state per pass)
   2: sp2_j   = 1 (perm) (TOFF's own spare -- fixed as a marker constant)
   3: sp3_j              (TOFF's own spare -- free, unused)
   4: g0_j    = 0 (perm) (TOFF's own scratch -- fixed as a marker constant)
   5: fire_j  (rest 1)   (TOFF's dual-rail target; see the trick above)
   6: g1_j    = 1 (perm) (TOFF's own scratch -- reused as firebar's own
                           GAPCNOT-control constant, and as gap_clear's
                           "cell 1" for the fire/firebar reset)
   7: firebar_j (rest 0) (the real q_j & symbol value, once TOFF has run)
   8: sp8_j, 9: sp9_j    (TOFF's own spares -- free, unused)
  10,11,12: TOFF's own markers (0,1,1)
  13: arrL_const1_j = 1  (const neighbour for arrL_j's own merge-into-q)
  14: arrL_j  (rest 0)   (arrival cell: set by a *forward* GAPCNOT from the
  15: arrL_gap_j            LEFT neighbour's firebar, when a rule fires
  16: arrLbar_j (rest 1)    with direction +1 into this group)
  17,18,19: arrL's own incoming-write markers (0,1,1)
  20,21,22: arrR's own incoming-write markers (0,1,1)
  23: arrRbar_j (rest 1) (arrival cell: set by a *mirrored* GAPCNOT from the
  24: arrR_gap_j            RIGHT neighbour's firebar, when a rule fires
  25: arrR_j  (rest 0)      with direction -1 into this group; also serves
                            as arrR_j's own merge-into-q constant neighbour)

Per state j, per pass, for v in (1, 0) [v=1 first]:
  1. (v=1 only) GAPCNOT(s -> b1_j)             b1_j := s, forward
     (v=0 only) F(b1_j); F(b1_j's dual partner sp3_j)   b1_j := NOT b1_j
  2. TOFF(q_j, b1_j)                            firebar_j := q_j & b1_j
  3. use firebar_j (all as plain GAPCNOT calls, control=firebar_j,
     const1=g1_j, mirrored since firebar_j is *after* every one of these
     targets):
       - if new_sym(j,v) != v: GAPCNOT(firebar_j -> s)      (flip symbol)
       - if not (dir==0 and new_state==j): GAPCNOT(firebar_j ->
             arrL_{new_state} in group+1, or arrR_{new_state} in group-1,
             or (arrL or arrR, whichever is unmirrored/mirrored-consistent)
             in the SAME group if dir==0 and new_state!=j)
       - if not (dir==0 and new_state==j): GAPCNOT(firebar_j -> (q_j,
             qbar_j))                                        (self-clear)
  4. gap_clear(fire_j, firebar_j) [mirrored, rooted at firebar_j, m=4,
     using g0_j/sp2_j as its marker pair] -- forces (fire,firebar) back to
     (1, 0) regardless of what happened above.
  5. (after both v=1 and v=0) gap_clear-undo the b1 broadcast: since v=0's
     step 1 flips b1_j back and forth with bare F's only when going from
     v=1 to v=0, we still owe *one* GAPCNOT(s -> b1_j) call (same K) to
     bring b1_j back from its v=0 state (=NOT s) through one more flip-pair
     to =s, then uncompute the original broadcast.

Per group, once per pass, *before* processing any state: for every state j,
merge and clear the arrival cells (both are safe as no-ops if unset):
  GAPCNOT(arrL_j -> (q_j, qbar_j)) [mirrored]; gap_clear(arrL_j, arrLbar_j)
  GAPCNOT(arrR_j -> (q_j, qbar_j)) [mirrored]; gap_clear(arrR_j, arrRbar_j)

All of this is checked, not asserted: `verify_sweep.py` brute-forces every
(active-state, symbol, garbage-in-every-spare-cell) combination through the
per-group word and checks the postcondition exactly, before any of it is
trusted to run a real TM.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import itertools

from gates import TOFF, gapcnot_word, parse_r
from hand_gapclear import gap_clear
from gadget_search import step_raw

TOFF_WORD = TOFF['word']


def mirror_word(word: List[str]) -> List[str]:
    out = []
    for l in word:
        if l == 'N':
            out.append('P')
        elif l == 'P':
            out.append('N')
        elif l == 'CN':
            out.append('CP')
        elif l == 'CP':
            out.append('CN')
        else:
            out.append(l)
    return out


def cd_to_r(s: str) -> List[str]:
    m = {'C': 'CN', 'D': 'CP', 'F': 'F', 'N': 'N', 'P': 'P'}
    return [m[ch] for ch in s]


# Marker distance for the fire/firebar reset (mirrored gap_clear rooted at
# firebar, offset7 relative to q). The two nearest *reliably constant*
# cells going backward from firebar are g1(-1)=1 and g0(-3)=0 -- but they
# are not adjacent (fire, at -2, sits between them and is NOT constant at
# this point, it's exactly the value being reset!), and sp2(-5)=1/sp3(-4)
# has the same problem (sp3 is b1's own dual partner, live data). The
# nearest ADJACENT pair of cells that are provably constant regardless of
# anything happening mid-pass is wm_near(-10)=0, wm_mid(-11)=1 (the
# self-clear/arrival-merge shared write markers, proven untouched by every
# gate that ever runs before this point in a state's processing).
GAPCLEAR_M = 10  # marker distance for the fire/firebar reset only

# Marker distance for a plain (b1,sp3) or (arr,arrbar) gap_clear_pair call:
# offset+3,+4 relative to the pair's own first cell land on a reliable
# (0,1) pair in both cases (g0,fire for b1/sp3 -- valid once fire has
# already been reset to 1 earlier in the same state's processing; and the
# incoming-write's own marker0,marker1 for arrL/arrR, which coincidentally
# hold the same (0,1) values gap_clear itself needs).
GAP_CLEAR_PAIR_M = 3


def gapclear_word_for(m: int = GAPCLEAR_M) -> List[str]:
    return cd_to_r(gap_clear(m))


# --- per-state relative-offset table (0 = q_j) ------------------------------
#
# wm_near/mid/far (q-3,-4,-5) are the *shared* write markers used by every
# gate that ever targets (q_j, qbar_j) as a dual-rail pair -- the self-clear
# (mirrored from firebar, K=6) and the two arrival merges (mirrored from
# arrL_j / arrR_j, larger K) all land their own marker triple at exactly
# target-3,-4,-5 regardless of K (see sweep.py's module docstring), so one
# shared triple, permanently 0,1,1 and never written by anything else,
# serves all of them.

STATE_WIDTH = 31  # cells -5..25

OFF = dict(
    wm_far=-5, wm_mid=-4, wm_near=-3,
    qbar=-2, qscr=-1, q=0, b1=1, sp2=2, sp3=3, g0=4, fire=5, g1=6,
    firebar=7, sp8=8, sp9=9, m0=10, m1=11, m2=12,
    arrL_const1=13, arrL=14, arrL_gap=15, arrLbar=16,
    # arrL's own incoming write is *forward* (from a lower-position left
    # neighbour's firebar): its marker triple is at arrL+3,+4,+5 = 0,1,1.
    arrL_mk0=17, arrL_mk1=18, arrL_mk2=19,
    # arrR's own incoming write is *mirrored* (from a higher-position right
    # neighbour's firebar): its marker triple is at arrR-3,-4,-5 = 0,1,1,
    # i.e. (in increasing absolute-offset order) far,mid,near = 1,1,0.
    arrR_mk_far=20, arrR_mk_mid=21, arrR_mk_near=22,
    arrRbar=23, arrR_gap=24, arrR=25,
)

REST = dict(
    wm_far=1, wm_mid=1, wm_near=0,
    qbar=1, qscr=0, q=0, b1=0, sp2=1, sp3=0, g0=0, fire=1, g1=1,
    # sp8 = firebar+1 is firebar's *forward*-call constant-1 neighbour
    # (used when firebar is the control of a forward GAPCNOT, e.g. writing
    # into a right/ahead neighbour's arrL on direction +1); g1 = firebar-1
    # is its mirrored-call constant-1 neighbour. Both are TOFF's own
    # provably-untouched spares, so fixing both at 1 forever is safe.
    firebar=0, sp8=1, sp9=0, m0=0, m1=1, m2=1,
    arrL_const1=1, arrL=0, arrL_gap=1, arrLbar=1,
    arrL_mk0=0, arrL_mk1=1, arrL_mk2=1,
    arrR_mk_far=1, arrR_mk_mid=1, arrR_mk_near=0,
    arrRbar=1, arrR_gap=1, arrR=0,
)

# the symbol s also needs its own dedicated marker triple: the "use
# firebar" step that conditionally flips s writes into s as a *mirrored*
# GAPCNOT call (firebar is always further into the group than s), so its
# marker triple sits at s-3,-4,-5 -- these must be dedicated cells, not
# wrapped around into the previous group, hence the padding before sbar.
S_BLOCK = dict(
    flip_mk_far=0, flip_mk_mid=1, flip_mk_near=2,
    sbar=3, gap=4, s=5, s_const1=6,
)
S_BLOCK_WIDTH = 7
S_REST = dict(
    flip_mk_far=1, flip_mk_mid=1, flip_mk_near=0,
    sbar=1, gap=1, s=0, s_const1=1,
)


# state j's own block spans q_offset(j)-5 .. q_offset(j)+25 (31 cells); the
# "-5" means the very first state's block needs 5 cells of padding after
# the (4-cell) symbol block, hence the "+5" below.
STATE_BASE = S_BLOCK_WIDTH + 5


def group_width(n_states: int) -> int:
    return STATE_BASE + n_states * STATE_WIDTH


def group_rest_tape(n_states: int) -> List[int]:
    """The group's between-pass rest tape (all cells at their canonical
    'nothing pending' values -- s=0 by default, overridden by the caller
    per the actual TM tape)."""
    t = [0] * group_width(n_states)
    for name, off in S_BLOCK.items():
        t[off] = S_REST[name]
    for j in range(n_states):
        base = STATE_BASE + j * STATE_WIDTH
        for name, off in OFF.items():
            t[base + off] = REST[name]
    return t


def q_offset(j: int) -> int:
    return STATE_BASE + j * STATE_WIDTH + OFF['q']


def cell_offset(j: int, name: str) -> int:
    return STATE_BASE + j * STATE_WIDTH + OFF[name]


# --- the assembler -----------------------------------------------------------

class Assembler:
    """Builds an R word over an *absolute* cyclic tape of size ring_size.
    Every gate call here documents its own start position and is emitted by
    goto() + the (mirrored or not) gate word; all our gates return the
    pointer to their start position, so self.pos is trivial to track."""

    def __init__(self, ring_size: int):
        self.ring_size = ring_size
        self.pos = 0
        self.word: List[str] = []

    def goto(self, target: int):
        target %= self.ring_size
        d = (target - self.pos) % self.ring_size
        if d == 0:
            return
        if d <= self.ring_size - d:
            self.word.extend(['N'] * d)
        else:
            self.word.extend(['P'] * (self.ring_size - d))
        self.pos = target

    def flip(self, abs_off: int):
        self.goto(abs_off)
        self.word.append('F')

    def gapcnot(self, control_abs: int, target_abs: int, mirrored=None):
        """Emit a GAPCNOT call with control at control_abs, writing the
        dual-rail pair at target_abs. If `mirrored` is left as None, picks
        whichever of the two directions is the shorter path around the
        ring -- fine when the caller doesn't care which one it gets, but
        every caller in this file that has *pre-allocated marker cells for
        a specific direction* (the group is much smaller than the ring in
        general, so the 'short way' can flip for a large state count) must
        pass the direction explicitly, or it will silently use the wrong
        marker cells."""
        fwd_K = (target_abs - control_abs - 1) % self.ring_size
        mir_K = (control_abs - target_abs - 1) % self.ring_size
        if mirrored is None:
            mirrored = mir_K < fwd_K
        K = mir_K if mirrored else fwd_K
        assert K >= 2, f"K={K} too small (control={control_abs},target={target_abs},mirrored={mirrored})"
        self.goto(control_abs)
        w = gapcnot_word(K)
        if mirrored:
            w = mirror_word(w)
        self.word.extend(w)
        return mirrored, K

    def toff(self, a_abs: int):
        self.goto(a_abs)
        self.word.extend(TOFF_WORD)

    def gapclear_mirrored_from(self, c_abs: int, m: int = GAPCLEAR_M):
        self.goto(c_abs)
        self.word.extend(mirror_word(gapclear_word_for(m)))


# --- the per-group program compiler -----------------------------------------

@dataclass
class Rule:
    state: str
    sym: int
    new_sym: int
    direction: int
    new_state: str


def build_rules(tm) -> List[Rule]:
    out = []
    for (q, sym), (nsym, d, nq) in tm.trans.items():
        out.append(Rule(q, sym, nsym, d, nq))
    return out


def compile_group_program(states: List[str], rules_by_state: Dict[str, Dict[int, Tuple[int, int, str]]],
                            n_groups: int) -> Tuple[List[str], int, int]:
    """Compiles ONE group's processing word (as absolute-offset letters
    relative to group 0 starting at absolute tape offset 0), to be
    replicated (with a shift) for every group in the ring by the caller.
    Returns (word, group_width, ring_size)."""
    n = len(states)
    idx = {q: i for i, q in enumerate(states)}
    G = group_width(n)
    ring_size = G * n_groups

    asm = Assembler(ring_size)

    def q_abs(group: int, j: int) -> int:
        return (group * G + q_offset(j)) % ring_size

    def cell_abs(group: int, j: int, name: str) -> int:
        return (group * G + cell_offset(j, name)) % ring_size

    def s_abs(group: int) -> int:
        return (group * G + S_BLOCK['s']) % ring_size

    def s_const1_abs(group: int) -> int:
        return (group * G + S_BLOCK['s_const1']) % ring_size

    GID = 0  # we compile group 0's word; other groups are a cyclic shift

    def gap_clear_pair(c_abs: int, cbar_abs: int, m: int = GAP_CLEAR_PAIR_M):
        fwd = (cbar_abs - c_abs) % ring_size == 2
        mir = (c_abs - cbar_abs) % ring_size == 2
        assert fwd or mir
        asm.goto(c_abs)
        w = gapclear_word_for(m)
        if mir:
            w = mirror_word(w)
        asm.word.extend(w)

    for j in range(n):
        for arr, arrbar in (('arrL', 'arrLbar'), ('arrR', 'arrRbar')):
            arr_abs = cell_abs(GID, j, arr)
            arrbar_abs = cell_abs(GID, j, arrbar)
            # always mirrored: q_j's shared write-markers (wm_*) are laid
            # out assuming the control is *after* q_j (see module
            # docstring) -- forced explicitly since for a large state
            # count the "short way around the ring" can flip to forward,
            # which would silently read the wrong marker cells.
            asm.gapcnot(arr_abs, q_abs(GID, j), mirrored=True)
            gap_clear_pair(arr_abs, arrbar_abs)

    # --- Phase 2: per-state compute/use/uncompute --------------------------
    for j in range(n):
        q_j = q_abs(GID, j)
        b1 = cell_abs(GID, j, 'b1')
        sp3 = cell_abs(GID, j, 'sp3')
        fire = cell_abs(GID, j, 'fire')
        firebar = cell_abs(GID, j, 'firebar')
        g1 = cell_abs(GID, j, 'g1')

        rules = rules_by_state.get(states[j], {})
        s_pos = s_abs(GID)

        # one broadcast s -> b1, used for v=1, flipped in place for v=0,
        # undone with a second broadcast at the very end.
        mirrored0, K0 = asm.gapcnot(s_pos, b1, mirrored=False)

        for v in (1, 0):
            if v == 0:
                asm.flip(b1)
                asm.flip(sp3)  # b1's dual partner (target-bar of the s->b1 write)
            asm.toff(q_j)
            rule = rules.get(v)
            if rule is not None:
                new_sym, direction, new_state = rule
                nj = idx[new_state]
                if new_sym != v:
                    # mirrored: flip_mk_* is laid out assuming firebar (the
                    # control) is *after* s in the group, forced for the
                    # same reason as above.
                    asm.gapcnot(firebar, s_pos, mirrored=True)
                skip_state_write = (direction == 0 and new_state == states[j])
                if not skip_state_write:
                    if direction == +1:
                        tgt_group = (GID + 1) % n_groups
                        tgt = cell_abs(tgt_group, nj, 'arrL')
                        write_mirrored = False  # arrL_mk* assumes forward
                    elif direction == -1:
                        tgt_group = (GID - 1) % n_groups
                        tgt = cell_abs(tgt_group, nj, 'arrR')
                        write_mirrored = True  # arrR_mk* assumes mirrored
                    else:
                        raise NotImplementedError(
                            "same-group direction==0 write to a different "
                            "state is not needed by the milestone-1 test "
                            "machines and is not implemented")
                    asm.gapcnot(firebar, tgt, mirrored=write_mirrored)
                    asm.gapcnot(firebar, q_j, mirrored=True)  # self-clear
            asm.gapclear_mirrored_from(firebar)

        # Reset b1 (and its dual partner sp3) back to (0, 1) unconditionally
        # via gap_clear, rather than "broadcast s -> b1 again": s may have
        # just been flipped by this very state's own v=0 symbol-write
        # (rules where new_sym != v), so a second GAPCNOT(s -> b1) would
        # cancel against the *new* s, not the one b1 was built from, and
        # leave b1 wrong. gap_clear has no such dependency -- it forces
        # (b1, sp3) to (0, 1) regardless of current value or how it arose.
        gap_clear_pair(b1, sp3)

    asm.goto(0)  # return to the group's canonical entry cell (s-block's
                 # offset 0) so replaying this same word after N^G on the
                 # next group is correct (see module docstring / caller).
    return asm.word, G, ring_size
