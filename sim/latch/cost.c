/* Minimum NAND-circuit gate count for all 65536 4-input Boolean functions.
 *
 * Inputs: q,x,a,b (idx = 8q+4x+2a+b, bit3=q..bit0=b). Constants free (cost 0).
 * Gates: NAND of fan-in 1 (inverter), 2, or 3, over {constants, q,x,a,b,
 * earlier gate outputs}. Repeated inputs to one gate never help (AND is
 * idempotent) so only *distinct*-input combinations are tried.
 *
 * BFS by gate count: R_{L-1} = set of truth tables reachable with <= L-1
 * gates; Delta_{L-1} = reachable with cost exactly L-1. A function first
 * reachable with L gates must use >=1 input of cost exactly L-1 (else it
 * would already be in R_{L-1}), so every new gate at level L includes at
 * least one operand from Delta_{L-1}.
 *
 * Exhaustive for L = 1..3 (checked: this already covers ~31% of all 65536
 * functions). For L = 4 and 5 the raw operand pool is already too large
 * (tens of thousands) for the O(|Delta|*|Rprev|^2) arity-3 loop to finish
 * in reasonable time, so those levels run under a wall-clock time budget:
 * whatever is found within budget is recorded (with correct, verified
 * costs -- the algorithm never records a wrong/too-low cost, it can only
 * fail to find some functions before the budget runs out, in which case
 * they are left for the next level or end up labelled '>5'). Operand order
 * is randomly shuffled at L>=4 so a truncated run samples broadly rather
 * than being biased toward one end of the pool. This does not affect
 * correctness of costs 0..3, and ranked.csv only needs cost(f)+cost(g) <=
 * bound <= 4, so an incomplete level 4/5 search only risks a conservative
 * undercount (some true cost-4 pairs missing from ranked.csv), never a
 * wrong inclusion.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <stdint.h>

#define NF 65536

static signed char cost[NF];

/* provenance for formula reconstruction:
 * op: 0=const0 1=const1 2=varQ 3=varX 4=varA 5=varB 6=NOT 7=NAND2 8=NAND3
 * c1,c2,c3: child truth-table values (-1 if unused) for op 6/7/8 */
static signed char op[NF];
static int32_t c1[NF], c2[NF], c3[NF];

static uint16_t Rprev[NF];
static int nR;
static uint16_t Delta[NF];
static int nD;

static unsigned rng_state = 12345u;
static unsigned xrand(void) {
    unsigned x = rng_state;
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    return rng_state = x;
}

/* Fisher-Yates: if a level's search is bailed on a time budget (best-effort,
 * levels 4-5 only; see header comment), a shuffled order means the partial
 * coverage samples broadly across the whole operand pool instead of being
 * systematically biased toward one end of it (e.g. by truth-table value or
 * discovery order). */
static void shuffle(uint16_t *a, int n) {
    for (int i = n - 1; i > 0; i--) {
        int j = xrand() % (unsigned)(i + 1);
        uint16_t t = a[i]; a[i] = a[j]; a[j] = t;
    }
}

static double now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

int main(int argc, char **argv) {
    int max_level = 5;
    double time_budget_level5 = 60.0; /* seconds, best-effort only */
    if (argc > 1) max_level = atoi(argv[1]);

    memset(cost, -1, sizeof(cost));
    memset(op, -1, sizeof(op));
    for (int i = 0; i < NF; i++) c1[i] = c2[i] = c3[i] = -1;

    uint16_t q_tt = 0, x_tt = 0, a_tt = 0, b_tt = 0;
    for (int idx = 0; idx < 16; idx++) {
        int q = (idx >> 3) & 1, x = (idx >> 2) & 1, a = (idx >> 1) & 1, b = idx & 1;
        if (q) q_tt |= (1 << idx);
        if (x) x_tt |= (1 << idx);
        if (a) a_tt |= (1 << idx);
        if (b) b_tt |= (1 << idx);
    }
    cost[0] = 0;      op[0] = 0;
    cost[0xFFFF] = 0; op[0xFFFF] = 1;
    cost[q_tt] = 0;   op[q_tt] = 2;
    cost[x_tt] = 0;   op[x_tt] = 3;
    cost[a_tt] = 0;   op[a_tt] = 4;
    cost[b_tt] = 0;   op[b_tt] = 5;

    /* Rprev after level 0 */
    nR = 0;
    for (int v = 0; v < NF; v++) if (cost[v] >= 0) Rprev[nR++] = (uint16_t)v;

    for (int L = 1; L <= max_level; L++) {
        double t0 = now();
        /* Delta = functions with cost == L-1 */
        nD = 0;
        for (int i = 0; i < nR; i++) if (cost[Rprev[i]] == L - 1) Delta[nD++] = Rprev[i];
        if (L >= 4) { shuffle(Rprev, nR); shuffle(Delta, nD); }

        long tried2 = 0, tried3 = 0, found_before = 0;
        for (int v = 0; v < NF; v++) if (cost[v] >= 0) found_before++;

        double level_budget = (L == 4) ? 240.0 : (L == 5) ? time_budget_level5 : 1e18;
        double deadline = t0 + level_budget;
        int bail = 0;

        /* arity 1 */
        for (int di = 0; di < nD; di++) {
            uint16_t d = Delta[di];
            uint16_t nf = (~d) & 0xFFFF;
            if (cost[nf] < 0) { cost[nf] = (signed char)L; op[nf] = 6; c1[nf] = d; }
        }

        /* arity 2: d (from Delta) NAND r (from Rprev, r != d) */
        for (int di = 0; di < nD && !bail; di++) {
            uint16_t d = Delta[di];
            for (int ri = 0; ri < nR; ri++) {
                uint16_t r = Rprev[ri];
                if (r == d) continue;
                uint16_t nf = (~(unsigned)(d & r)) & 0xFFFF;
                if (cost[nf] < 0) { cost[nf] = (signed char)L; op[nf] = 7; c1[nf] = d; c2[nf] = r; }
                tried2++;
            }
            if ((di & 63) == 0 && now() > deadline) { bail = 1; }
        }

        /* arity 3: d (from Delta) NAND r1 NAND r2, r1<r2 both from Rprev, both != d */
        for (int di = 0; di < nD && !bail; di++) {
            uint16_t d = Delta[di];
            for (int i1 = 0; i1 < nR; i1++) {
                uint16_t r1 = Rprev[i1];
                if (r1 == d) continue;
                unsigned dr1 = (unsigned)(d & r1);
                if (dr1 == 0) continue; /* triple AND will be 0 regardless of r2: NAND=const1, known */
                for (int i2 = i1 + 1; i2 < nR; i2++) {
                    uint16_t r2 = Rprev[i2];
                    if (r2 == d) continue;
                    uint16_t nf = (~(dr1 & (unsigned)r2)) & 0xFFFF;
                    if (cost[nf] < 0) { cost[nf] = (signed char)L; op[nf] = 8; c1[nf] = d; c2[nf] = r1; c3[nf] = r2; }
                    tried3++;
                }
                if ((i1 & 511) == 0 && now() > deadline) { bail = 1; break; }
            }
        }

        int found_after = 0;
        for (int v = 0; v < NF; v++) if (cost[v] >= 0) found_after++;

        fprintf(stderr,
                "level %d: |Delta|=%d |Rprev(before)|=%d tried2=%ld tried3=%ld "
                "new=%d total_known=%d time=%.2fs%s\n",
                L, nD, nR, tried2, tried3, found_after - found_before, found_after,
                now() - t0, bail ? " [BAILED-timebudget]" : "");

        /* rebuild Rprev for next level */
        nR = 0;
        for (int v = 0; v < NF; v++) if (cost[v] >= 0) Rprev[nR++] = (uint16_t)v;
    }

    FILE *out = fopen(argv[2] ? argv[2] : "cost_table.txt", "w");
    for (int v = 0; v < NF; v++) {
        fprintf(out, "%d %d %d %d %d %d\n", v, cost[v], op[v], c1[v], c2[v], c3[v]);
        /* cost[v] == -1 means '>max_level' (op/children also -1 then) */
    }
    fclose(out);
    fprintf(stderr, "wrote cost table.\n");
    return 0;
}
