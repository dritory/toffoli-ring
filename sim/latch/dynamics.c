/* Dynamics of the latch-ring model for a list of (f,g) pairs.
 *
 * Model: cyclic ring s of N bits, offset k, latch bit q.
 * Pass: for i = 0..N-1: x=s[(i+k)%N]; a=s[i]; b=s[(i+1)%N];
 *       s[(i+k)%N] = f(q,x,a,b); q = g(q,x,a,b).
 * f,g given as 16-bit truth tables, idx = 8q+4x+2a+b.
 *
 * Modes (argv[1]):
 *   cycles   -- cycle statistics (transient, period) at N=16,20,24, k=2,3,
 *               20 random (s,q) seeds each, cap 1e6 passes.
 *   vacuum   -- classify all-zero s with q=0 and q=1 as fixed/periodic(<=4)/other,
 *               for k=2,3.
 *   interact -- for pairs whose vacuum (chosen q start) is fixed/periodic<=4:
 *               lone-pattern evolution (15 patterns, width<=4) at N=128, 60 passes,
 *               plus glider detection (up to GLIDE_MAXT passes), plus the full
 *               pairwise (P,Q,d) superposition test, d=8..24, k=2,3.
 *
 * Input: a text file, one pair per line: "f_hex g_hex label"
 * Output: CSV to stdout (redirect to file).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

typedef uint32_t u32;
typedef uint64_t u64;

static inline int tt_eval(int tt, int q, int x, int a, int b) {
    int idx = (q << 3) | (x << 2) | (a << 1) | b;
    return (tt >> idx) & 1;
}

/* ---- ring pass, N <= 32, bits packed in a u32 ---- */
static inline u32 do_pass(u32 s, int N, int k, int f_tt, int g_tt, int *qp) {
    int q = *qp;
    for (int i = 0; i < N; i++) {
        int xi = (i + k) % N;
        int bi = (i + 1) % N;
        int x = (s >> xi) & 1;
        int a = (s >> i) & 1;
        int b = (s >> bi) & 1;
        int y = tt_eval(f_tt, q, x, a, b);
        q = tt_eval(g_tt, q, x, a, b);
        if (y) s |= (1u << xi); else s &= ~(1u << xi);
    }
    *qp = q;
    return s;
}

/* ---- ring pass for N up to 200-ish, bits packed in a byte array ---- */
static inline void do_pass_big(unsigned char *s, int N, int k, int f_tt, int g_tt, int *qp) {
    int q = *qp;
    for (int i = 0; i < N; i++) {
        int xi = i + k; if (xi >= N) xi -= N;
        int bi = i + 1; if (bi >= N) bi -= N;
        int x = s[xi], a = s[i], b = s[bi];
        int y = tt_eval(f_tt, q, x, a, b);
        q = tt_eval(g_tt, q, x, a, b);
        s[xi] = (unsigned char)y;
    }
    *qp = q;
}

/* ---------------- epoch-tagged hash table for cycle detection ---------------- */
#define HBITS 21
#define HSIZE (1u << HBITS)
static u32 h_epoch[HSIZE];
static u32 h_key[HSIZE];
static u32 h_step[HSIZE];
static u32 cur_epoch = 0;

static inline u32 hmix(u32 k) {
    k ^= k >> 16; k *= 0x7feb352dU;
    k ^= k >> 15; k *= 0x846ca68bU;
    k ^= k >> 16;
    return k;
}

/* returns previous step index if key seen this epoch, else inserts and returns -1 */
static inline long h_find_or_insert(u32 key, u32 step) {
    u32 h = hmix(key) & (HSIZE - 1);
    while (1) {
        if (h_epoch[h] != cur_epoch) {
            h_epoch[h] = cur_epoch; h_key[h] = key; h_step[h] = step;
            return -1;
        }
        if (h_key[h] == key) return (long)h_step[h];
        h = (h + 1) & (HSIZE - 1);
    }
}

/* cycle detection via hashing every state; returns 1 if found (sets *transient,*period), 0 if cap hit */
static int find_cycle(u32 s0, int q0, int N, int k, int f_tt, int g_tt, long cap,
                       long *transient, long *period) {
    cur_epoch++;
    u32 s = s0; int q = q0;
    for (long t = 0; t <= cap; t++) {
        u32 key = (s << 1) | (u32)q;
        long prev = h_find_or_insert(key, (u32)t);
        if (prev >= 0) { *transient = prev; *period = t - prev; return 1; }
        s = do_pass(s, N, k, f_tt, g_tt, &q);
    }
    return 0;
}

static u32 rng_state = 88172645463325252ULL & 0xFFFFFFFFu;
static u32 xorshift32(void) {
    u32 x = rng_state;
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    rng_state = x;
    return x;
}

/* ================= MODE: cycles ================= */
static void mode_cycles(FILE *pf) {
    printf("f_hex,g_hex,label,k,N,seed,transient,period,capped\n");
    char line[256];
    while (fgets(line, sizeof(line), pf)) {
        unsigned fh, gh; char label[64] = "";
        int nf = sscanf(line, "%x %x %63s", &fh, &gh, label);
        if (nf < 2) continue;
        int Ns[3] = {16, 20, 24};
        for (int ki = 0; ki < 2; ki++) {
            int k = (ki == 0) ? 2 : 3;
            for (int ni = 0; ni < 3; ni++) {
                int N = Ns[ni];
                rng_state = 0x9e3779b9u ^ (fh * 2654435761u) ^ (gh * 40503u) ^ (N * 131u) ^ (k * 7u);
                if (rng_state == 0) rng_state = 1;
                for (int seed = 0; seed < 20; seed++) {
                    u32 s0 = 0;
                    for (int b = 0; b < N; b++) if (xorshift32() & 1) s0 |= (1u << b);
                    int q0 = xorshift32() & 1;
                    long transient = -1, period = -1;
                    int ok = find_cycle(s0, q0, N, k, fh, gh, 1000000, &transient, &period);
                    printf("%04x,%04x,%s,%d,%d,%d,%ld,%ld,%d\n",
                           fh, gh, label, k, N, seed, transient, period, ok ? 0 : 1);
                }
            }
        }
        fflush(stdout);
    }
}

/* ================= vacuum classification ================= */
/* returns: 0 = fixed (s stays all-zero every pass, q reaches a fixed value),
 *          1..4 = periodic with that period (s returns to all-zero AND q returns
 *                 to its starting value after that many passes, first occurrence),
 *          -1 = neither within VCAP passes (diverges / long / grows) */
#define VN 40
#define VCAP 4096
static int vacuum_status(int q_start, int k, int f_tt, int g_tt, long *out_period) {
    /* scan for periodic return (s all-zero AND q==q_start) up to VCAP */
    unsigned char s[VN]; memset(s, 0, sizeof(s));
    int q = q_start;
    for (int t = 1; t <= VCAP; t++) {
        do_pass_big(s, VN, k, f_tt, g_tt, &q);
        int allz = 1;
        for (int i = 0; i < VN; i++) if (s[i]) { allz = 0; break; }
        if (allz && q == q_start) {
            if (t <= 4) { *out_period = t; return (int)t; }
            *out_period = t;
            return -1; /* returns, but period > 4: not usable per spec */
        }
    }
    *out_period = -1;
    return -1;
}

static void mode_vacuum(FILE *pf) {
    printf("f_hex,g_hex,label,k,qstart,status,period\n");
    char line[256];
    while (fgets(line, sizeof(line), pf)) {
        unsigned fh, gh; char label[64] = "";
        int nf = sscanf(line, "%x %x %63s", &fh, &gh, label);
        if (nf < 2) continue;
        for (int ki = 0; ki < 2; ki++) {
            int k = (ki == 0) ? 2 : 3;
            for (int qs = 0; qs <= 1; qs++) {
                long period = -1;
                int st = vacuum_status(qs, k, fh, gh, &period);
                printf("%04x,%04x,%s,%d,%d,%d,%ld\n", fh, gh, label, k, qs, st, period);
            }
        }
        fflush(stdout);
    }
}

/* ================= interaction + glider ================= */
#define BN 128
#define PASSES 60
#define GLIDE_MAXT 160
#define NPAT 30 /* nonzero patterns of width 1..4: sum(2^w - 1, w=1..4) = 26, rounded up */

/* place pattern bits (width w, LSB=cell0) at position pos in a zero array of length BN */
static void place(unsigned char *s, int pos, int pat, int w) {
    for (int i = 0; i < w; i++) s[(pos + i) % BN] = (pat >> i) & 1;
}

static int arreq(const unsigned char *a, const unsigned char *b, int n) {
    return memcmp(a, b, n) == 0;
}

/* try to find a glider: state at pass t equals state at pass 0 shifted by 'sh' cells
 * (cyclic), for some t in [1,GLIDE_MAXT], sh in [-maxsh,maxsh]. Compares against the
 * vacuum-subtracted footprint so a breathing (period<=4) background doesn't confuse it. */
static int find_glider(int k, int f_tt, int g_tt, int q_start, int pat, int w,
                        int *out_t, int *out_shift) {
    unsigned char vac[BN]; memset(vac, 0, sizeof(vac));
    unsigned char cur[BN]; memset(cur, 0, sizeof(cur));
    place(cur, 0, pat, w);
    unsigned char seed_fp[BN];
    memcpy(seed_fp, cur, BN); /* footprint at t=0 equals cur since vac=0 */
    int qv = q_start, qc = q_start;
    int maxsh = 6;
    for (int t = 1; t <= GLIDE_MAXT; t++) {
        do_pass_big(vac, BN, k, f_tt, g_tt, &qv);
        do_pass_big(cur, BN, k, f_tt, g_tt, &qc);
        unsigned char fp[BN];
        for (int i = 0; i < BN; i++) fp[i] = cur[i] ^ vac[i];
        int lim = maxsh * t; if (lim > BN - w - 1) lim = BN - w - 1;
        for (int sh = 1; sh <= lim; sh++) { /* sh=0 is "returns unshifted" (fixed/oscillating in place), not a glider */
            unsigned char shifted[BN]; memset(shifted, 0, sizeof(shifted));
            int any = 0;
            for (int i = 0; i < BN; i++) if (seed_fp[i]) { shifted[(i + sh) % BN] = 1; any = 1; }
            if (!any) continue;
            if (arreq(fp, shifted, BN)) { *out_t = t; *out_shift = sh; return 1; }
        }
    }
    return 0;
}

static void mode_interact(FILE *pf, FILE *vacf) {
    /* read vacuum results to know, per (f,g,k), which qstart to use (prefer period 1,
     * else smallest 2..4; -1 means unusable) */
    printf("f_hex,g_hex,label,k,qstart,vac_period,n_gliders,glider_examples,"
           "n_interact_tested,n_interact_dependent,example_dependent\n");
    char line[512];
    /* map key -> (qstart,period) best found, read all lines first */
    typedef struct { unsigned fh, gh; int k; int qs; long period; } VRec;
    VRec vrecs[100000]; int nv = 0;
    while (fgets(line, sizeof(line), vacf) && nv < 100000) {
        unsigned fh, gh; char label[64]; int k, qs, status; long period;
        if (line[0] == 'f') continue; /* header */
        int n = sscanf(line, "%x,%x,%63[^,],%d,%d,%d,%ld", &fh, &gh, label, &k, &qs, &status, &period);
        if (n < 7) continue;
        if (status < 0) continue; /* not usable */
        vrecs[nv].fh = fh; vrecs[nv].gh = gh; vrecs[nv].k = k; vrecs[nv].qs = qs; vrecs[nv].period = status;
        nv++;
    }

    while (fgets(line, sizeof(line), pf)) {
        unsigned fh, gh; char label[64] = "";
        int nf = sscanf(line, "%x %x %63s", &fh, &gh, label);
        if (nf < 2) continue;
        for (int ki = 0; ki < 2; ki++) {
            int k = (ki == 0) ? 2 : 3;
            /* find best qstart for this (fh,gh,k): prefer smallest period among usable */
            int best_qs = -1; long best_period = 1000000;
            for (int i = 0; i < nv; i++) {
                if (vrecs[i].fh == fh && vrecs[i].gh == gh && vrecs[i].k == k) {
                    if (vrecs[i].period < best_period) { best_period = vrecs[i].period; best_qs = vrecs[i].qs; }
                }
            }
            if (best_qs < 0) {
                printf("%04x,%04x,%s,%d,,,0,,0,0,\n", fh, gh, label, k);
                continue;
            }
            int q_start = best_qs;

            /* enumerate 15 nonzero width<=4 patterns */
            int pats[NPAT], ws[NPAT]; int np = 0;
            for (int w = 1; w <= 4; w++)
                for (int p = 1; p < (1 << w); p++) { pats[np] = p; ws[np] = w; np++; }

            /* gliders */
            int n_gliders = 0;
            char glide_ex[512] = "";
            for (int pi = 0; pi < np; pi++) {
                int t, sh;
                if (find_glider(k, fh, gh, q_start, pats[pi], ws[pi], &t, &sh)) {
                    n_gliders++;
                    if (strlen(glide_ex) < 400) {
                        char buf[64];
                        snprintf(buf, sizeof(buf), "%d/%d:t=%d,sh=%d;", pats[pi], ws[pi], t, sh);
                        strcat(glide_ex, buf);
                    }
                }
            }

            /* lone evolutions at pass=PASSES for all patterns, and vacuum ref */
            unsigned char vacref[BN]; memset(vacref, 0, sizeof(vacref));
            { int qq = q_start; for (int t = 0; t < PASSES; t++) do_pass_big(vacref, BN, k, fh, gh, &qq); }

            unsigned char lone[NPAT][BN];
            for (int pi = 0; pi < np; pi++) {
                unsigned char s[BN]; memset(s, 0, sizeof(s));
                place(s, 0, pats[pi], ws[pi]);
                int qq = q_start;
                for (int t = 0; t < PASSES; t++) do_pass_big(s, BN, k, fh, gh, &qq);
                memcpy(lone[pi], s, BN);
            }

            /* pairwise interaction test over d=8..24 */
            long n_tested = 0, n_dependent = 0;
            int example_found = 0, ex_pi = 0, ex_pj = 0, ex_d = 0;
            for (int d = 8; d <= 24; d++) {
                /* Delta(pi,pj) = combined XOR predicted, for all pi<=pj (P at 0, Q at d) */
                /* store deltas in a small grid to test dependence on both P and Q */
                unsigned char pred[NPAT][NPAT][BN];
                unsigned char comb[NPAT][NPAT][BN];
                int have[NPAT][NPAT];
                memset(have, 0, sizeof(have));
                for (int pi = 0; pi < np; pi++) {
                    for (int pj = 0; pj < np; pj++) {
                        /* skip overlapping placements */
                        if (d < ws[pi]) continue;
                        unsigned char s[BN]; memset(s, 0, sizeof(s));
                        place(s, 0, pats[pi], ws[pi]);
                        place(s, d, pats[pj], ws[pj]);
                        int qq = q_start;
                        for (int t = 0; t < PASSES; t++) do_pass_big(s, BN, k, fh, gh, &qq);
                        memcpy(comb[pi][pj], s, BN);
                        for (int i = 0; i < BN; i++)
                            pred[pi][pj][i] = (unsigned char)(vacref[i] ^ (lone[pi][i] ^ vacref[i]) ^ (lone[pj][i] ^ vacref[i]));
                        have[pi][pj] = 1;
                        n_tested++;
                    }
                }
                /* delta grid */
                for (int pi = 0; pi < np; pi++) {
                    for (int pj = 0; pj < np; pj++) {
                        if (!have[pi][pj]) continue;
                        int differs = !arreq(comb[pi][pj], pred[pi][pj], BN);
                        if (!differs) continue;
                        /* check dependence on both: does delta change when varying pj (fix pi)?
                         * and when varying pi (fix pj)? compare against a couple of alternates. */
                        int dep_on_q = 0, dep_on_p = 0;
                        for (int pj2 = 0; pj2 < np; pj2++) {
                            if (pj2 == pj || !have[pi][pj2]) continue;
                            unsigned char d1[BN], d2[BN];
                            for (int i = 0; i < BN; i++) { d1[i] = comb[pi][pj][i] ^ pred[pi][pj][i]; d2[i] = comb[pi][pj2][i] ^ pred[pi][pj2][i]; }
                            if (!arreq(d1, d2, BN)) { dep_on_q = 1; break; }
                        }
                        for (int pi2 = 0; pi2 < np; pi2++) {
                            if (pi2 == pi || !have[pi2][pj]) continue;
                            unsigned char d1[BN], d2[BN];
                            for (int i = 0; i < BN; i++) { d1[i] = comb[pi][pj][i] ^ pred[pi][pj][i]; d2[i] = comb[pi2][pj][i] ^ pred[pi2][pj][i]; }
                            if (!arreq(d1, d2, BN)) { dep_on_p = 1; break; }
                        }
                        if (dep_on_q && dep_on_p) {
                            n_dependent++;
                            if (!example_found) { example_found = 1; ex_pi = pi; ex_pj = pj; ex_d = d; }
                        }
                    }
                }
            }
            char example_str[64] = "";
            if (example_found) {
                snprintf(example_str, sizeof(example_str), "%d/%d,%d/%d,d=%d",
                         pats[ex_pi], ws[ex_pi], pats[ex_pj], ws[ex_pj], ex_d);
            }
            printf("%04x,%04x,%s,%d,%d,%ld,%d,%s,%ld,%ld,%s\n",
                   fh, gh, label, k, q_start, best_period, n_gliders, glide_ex, n_tested, n_dependent,
                   example_str);
        }
        fflush(stdout);
    }
}

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: %s <mode: cycles|vacuum|interact> pairs.txt [vacuum.csv]\n", argv[0]);
        return 1;
    }
    FILE *pf = fopen(argv[2], "r");
    if (!pf) { perror("pairs file"); return 1; }
    if (strcmp(argv[1], "cycles") == 0) {
        mode_cycles(pf);
    } else if (strcmp(argv[1], "vacuum") == 0) {
        mode_vacuum(pf);
    } else if (strcmp(argv[1], "interact") == 0) {
        if (argc < 4) { fprintf(stderr, "interact needs vacuum.csv\n"); return 1; }
        FILE *vf = fopen(argv[3], "r");
        if (!vf) { perror("vacuum csv"); return 1; }
        mode_interact(pf, vf);
        fclose(vf);
    } else {
        fprintf(stderr, "unknown mode\n"); return 1;
    }
    fclose(pf);
    return 0;
}
