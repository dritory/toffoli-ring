/*
 * Exhaustive search for HANDOVER-B.md section 6 (stateless pairs), using a
 * window guaranteed large enough to make "prune on leaving" exact for any
 * word of length <= 12: per group width g, R = ceil(6/g) + 1 groups on each
 * side of the current group (g=1: R=7 -> 15 groups; g=2: R=4 -> 9 groups;
 * g=3: R=3 -> 7 groups), because a length-12 word can move a branch at most
 * 6 cells from its start and still return, and every target's own effect
 * stays within g cells.
 *
 * Bitset-parallel over the 2^n_groups logical-bit valuations: for each of
 * the W = n_groups*g window positions we keep a V-bit bitset "cell content
 * there, per valuation" and a V-bit bitset "pointer here, per valuation".
 * One bundle application updates all V valuations at once with bitwise
 * ops -- no per-valuation Python loop.
 *
 * Output: results/twoop/stateless_full_complete.csv, same schema as the
 * earlier stateless_full.csv / stateless_full_w5.csv.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef uint64_t u64;

/* ---------------- bundles & pairs (mirrors model.py exactly) ---------- */

typedef struct { int flip; int dir; int cond; int order; /* 0=FM,1=MF */ } Bundle;
typedef struct { Bundle A; Bundle B; } Pair;

static void gen_bundles(int dir, Bundle out[9]) {
    int conds[3] = {-1, 0, 1};
    int idx = 0;
    for (int ci = 0; ci < 3; ci++) {
        int cond = conds[ci];
        out[idx++] = (Bundle){0, dir, cond, 0};
        out[idx++] = (Bundle){1, dir, cond, 0};
        out[idx++] = (Bundle){1, dir, cond, 1};
    }
}

static int gen_pairs(Pair out[64]) {
    Bundle plus[9], minus[9];
    gen_bundles(+1, plus);
    gen_bundles(-1, minus);
    int n = 0;
    for (int a = 0; a < 9; a++) {
        for (int b = 0; b < 9; b++) {
            Bundle A = plus[a], B = minus[b];
            if (A.cond == -1 && B.cond == -1) continue;
            if (!A.flip && !B.flip) continue;
            out[n].A = A;
            out[n].B = B;
            n++;
        }
    }
    return n;
}

static void bundle_str(Bundle b, char *buf) {
    char move[16];
    if (b.cond == -1) sprintf(move, "%s", b.dir == 1 ? "+1" : "-1");
    else sprintf(move, "%s?%d", b.dir == 1 ? "+1" : "-1", b.cond);
    if (!b.flip) { strcpy(buf, move); return; }
    if (b.order == 0) sprintf(buf, "flip;%s", move);
    else sprintf(buf, "%s;flip", move);
}

/* ---------------- encodings (mirrors model.py's gen_encodings order) --- */

typedef struct { const char *family; int g; const char *pattern; } Enc;

static Enc ENCODINGS[19] = {
    {"none", 1, "x"},
    {"dual", 2, "xn"},
    {"dual", 2, "nx"},
    {"scratch", 2, "x1"},
    {"scratch", 2, "1x"},
    {"scratch", 2, "x0"},
    {"scratch", 2, "0x"},
    {"period3", 3, "x01"},
    {"period3", 3, "01x"},
    {"period3", 3, "1x0"},
    {"period3", 3, "x10"},
    {"period3", 3, "10x"},
    {"period3", 3, "0x1"},
    {"period3", 3, "x00"},
    {"period3", 3, "00x"},
    {"period3", 3, "0x0"},
    {"period3", 3, "x11"},
    {"period3", 3, "11x"},
    {"period3", 3, "1x1"},
};

static void pattern_str(const char *patt, int g, char *buf) {
    buf[0] = '(';
    int p = 1;
    for (int i = 0; i < g; i++) {
        if (i) buf[p++] = ',';
        buf[p++] = patt[i];
    }
    buf[p++] = ')';
    buf[p] = '\0';
}

/* ---------------- per-g-family window configuration -------------------- */

typedef struct {
    int g;
    int n_groups;
    int mid_index;
    int W;
    long long V;
    int nwords;
    u64 **B; /* B[i] is a bitset (nwords words) over valuations: bit v set iff group i's logical bit is 1 in valuation v */
} GConfig;

static void build_gconfig(GConfig *gc, int g, int R) {
    gc->g = g;
    gc->n_groups = 2 * R + 1;
    gc->mid_index = R;
    gc->W = gc->n_groups * g;
    gc->V = 1LL << gc->n_groups;
    gc->nwords = (int)(gc->V / 64); /* exact: n_groups >= 6 in all our configs */
    gc->B = malloc(sizeof(u64 *) * gc->n_groups);
    for (int i = 0; i < gc->n_groups; i++) {
        gc->B[i] = calloc(gc->nwords, sizeof(u64));
        for (long long v = 0; v < gc->V; v++) {
            if ((v >> i) & 1LL) {
                gc->B[i][v / 64] |= (1ULL << (v % 64));
            }
        }
    }
}

/* ---------------- state: cell[p*nwords+k], ptrpos[p*nwords+k] ---------- */

static u64 *alloc_state(int W, int nwords) {
    return calloc((size_t)W * nwords, sizeof(u64));
}

/* Apply one bundle to (cell, ptrpos) in place. Returns 1 if some valuation's
 * pointer would leave the window (caller must discard this whole word). */
static int apply_letter(Bundle b, u64 *cell, u64 *ptrpos, int W, int nwords) {
    u64 *new_ptrpos = calloc((size_t)W * nwords, sizeof(u64));
    u64 *movers = malloc(sizeof(u64) * nwords);
    u64 *nonmovers = malloc(sizeof(u64) * nwords);
    int leaked = 0;

    if (b.flip && b.order == 0) { /* FM: flip current cell first */
        for (int p = 0; p < W; p++) {
            u64 *pp = &ptrpos[p * nwords];
            int nz = 0;
            for (int k = 0; k < nwords; k++) if (pp[k]) { nz = 1; break; }
            if (!nz) continue;
            u64 *cc = &cell[p * nwords];
            for (int k = 0; k < nwords; k++) cc[k] ^= pp[k];
        }
    }

    for (int p = 0; p < W; p++) {
        u64 *pp = &ptrpos[p * nwords];
        int nz = 0;
        for (int k = 0; k < nwords; k++) if (pp[k]) { nz = 1; break; }
        if (!nz) continue;
        u64 *cc = &cell[p * nwords];
        for (int k = 0; k < nwords; k++) {
            u64 mv;
            if (b.cond == -1) mv = pp[k];
            else if (b.cond == 1) mv = pp[k] & cc[k];
            else mv = pp[k] & (~cc[k]);
            movers[k] = mv;
            nonmovers[k] = pp[k] & (~mv);
        }
        int mv_nz = 0;
        for (int k = 0; k < nwords; k++) if (movers[k]) { mv_nz = 1; break; }
        int tp = p + b.dir;
        if (mv_nz) {
            if (tp < 0 || tp >= W) {
                leaked = 1;
            } else {
                u64 *np = &new_ptrpos[tp * nwords];
                for (int k = 0; k < nwords; k++) np[k] |= movers[k];
            }
        }
        {
            u64 *np = &new_ptrpos[p * nwords];
            for (int k = 0; k < nwords; k++) np[k] |= nonmovers[k];
        }
        if (b.flip && b.order == 1) { /* MF: flip arrival cell now */
            if (mv_nz && !(tp < 0 || tp >= W)) {
                u64 *ctp = &cell[tp * nwords];
                for (int k = 0; k < nwords; k++) ctp[k] ^= movers[k];
            }
            int nm_nz = 0;
            for (int k = 0; k < nwords; k++) if (nonmovers[k]) { nm_nz = 1; break; }
            if (nm_nz) {
                for (int k = 0; k < nwords; k++) cc[k] ^= nonmovers[k];
            }
        }
    }

    if (!leaked) memcpy(ptrpos, new_ptrpos, sizeof(u64) * (size_t)W * nwords);
    free(new_ptrpos);
    free(movers);
    free(nonmovers);
    return leaked;
}

/* ---------------- target checking -------------------------------------- */

static const char *TARGETS[6] = {"FLIP", "NEXT", "PREV", "CFLIP", "CNEXT", "CPREV"};

/* returns 1 iff ALL valuations satisfy `target` in the given final state */
static int check_target(int target_idx, u64 *cell, u64 *ptrpos, GConfig *gc,
                         const char *pattern, int xslot, int start_ptr) {
    int W = gc->W, nwords = gc->nwords, g = gc->g, n_groups = gc->n_groups, mid = gc->mid_index;
    u64 *fail = calloc(nwords, sizeof(u64));

    /* encoding validity for every group */
    for (int i = 0; i < n_groups; i++) {
        int xp = i * g + xslot;
        for (int j = 0; j < g; j++) {
            char st = pattern[j];
            int p = i * g + j;
            u64 *cp = &cell[p * nwords];
            if (st == '0') {
                for (int k = 0; k < nwords; k++) fail[k] |= cp[k];
            } else if (st == '1') {
                for (int k = 0; k < nwords; k++) fail[k] |= ~cp[k];
            } else if (st == 'n') {
                u64 *cx = &cell[xp * nwords];
                for (int k = 0; k < nwords; k++) fail[k] |= cp[k] ^ (~cx[k]);
            }
        }
    }

    /* non-mid groups unchanged */
    for (int i = 0; i < n_groups; i++) {
        if (i == mid) continue;
        int xp = i * g + xslot;
        u64 *cx = &cell[xp * nwords];
        u64 *Bi = gc->B[i];
        for (int k = 0; k < nwords; k++) fail[k] |= cx[k] ^ Bi[k];
    }

    int xp_mid = mid * g + xslot;
    u64 *cxm = &cell[xp_mid * nwords];
    u64 *Bm = gc->B[mid];
    const char *t = TARGETS[target_idx];

    if (strcmp(t, "FLIP") == 0) {
        for (int k = 0; k < nwords; k++) fail[k] |= cxm[k] ^ (~Bm[k]);
        u64 *pp = &ptrpos[start_ptr * nwords];
        for (int k = 0; k < nwords; k++) fail[k] |= ~pp[k];
    } else if (strcmp(t, "NEXT") == 0) {
        for (int k = 0; k < nwords; k++) fail[k] |= cxm[k] ^ Bm[k];
        int want = start_ptr + g;
        u64 *pp = &ptrpos[want * nwords];
        for (int k = 0; k < nwords; k++) fail[k] |= ~pp[k];
    } else if (strcmp(t, "PREV") == 0) {
        for (int k = 0; k < nwords; k++) fail[k] |= cxm[k] ^ Bm[k];
        int want = start_ptr - g;
        u64 *pp = &ptrpos[want * nwords];
        for (int k = 0; k < nwords; k++) fail[k] |= ~pp[k];
    } else if (strcmp(t, "CFLIP") == 0) {
        for (int k = 0; k < nwords; k++) fail[k] |= cxm[k];
        u64 *pp = &ptrpos[start_ptr * nwords];
        for (int k = 0; k < nwords; k++) fail[k] |= ~pp[k];
    } else if (strcmp(t, "CNEXT") == 0) {
        for (int k = 0; k < nwords; k++) fail[k] |= cxm[k] ^ Bm[k];
        int want = start_ptr + g;
        u64 *ppw = &ptrpos[want * nwords];
        u64 *pps = &ptrpos[start_ptr * nwords];
        for (int k = 0; k < nwords; k++) fail[k] |= (Bm[k] & ~ppw[k]) | ((~Bm[k]) & ~pps[k]);
    } else if (strcmp(t, "CPREV") == 0) {
        for (int k = 0; k < nwords; k++) fail[k] |= cxm[k] ^ Bm[k];
        int want = start_ptr - g;
        u64 *ppw = &ptrpos[want * nwords];
        u64 *pps = &ptrpos[start_ptr * nwords];
        for (int k = 0; k < nwords; k++) fail[k] |= (Bm[k] & ~ppw[k]) | ((~Bm[k]) & ~pps[k]);
    }

    int ok = 1;
    for (int k = 0; k < nwords; k++) if (fail[k]) { ok = 0; break; }
    free(fail);
    return ok;
}

/* ---------------- BFS over words for one (pair, pattern, rest) --------- */

typedef struct Node {
    char word[13];
    u64 *cell;
    u64 *ptrpos;
} Node;

static void search_combo(Pair pair, const char *pattern, int g, int rest, GConfig *gc,
                          char found[6][13], int *found_len) {
    int W = gc->W, nwords = gc->nwords;
    int xslot = (int)(strchr(pattern, 'x') - pattern);
    int start_ptr = gc->mid_index * g + rest;

    for (int t = 0; t < 6; t++) { found[t][0] = '\0'; found_len[t] = -1; }

    u64 *cell0 = alloc_state(W, nwords);
    u64 *ptrpos0 = alloc_state(W, nwords);
    for (int i = 0; i < gc->n_groups; i++) {
        for (int j = 0; j < g; j++) {
            int p = i * g + j;
            char st = pattern[j];
            u64 *cp = &cell0[p * nwords];
            if (st == 'x') memcpy(cp, gc->B[i], sizeof(u64) * nwords);
            else if (st == 'n') { for (int k = 0; k < nwords; k++) cp[k] = ~gc->B[i][k]; }
            else if (st == '1') { for (int k = 0; k < nwords; k++) cp[k] = ~0ULL; }
            /* '0' stays zero */
        }
    }
    for (int k = 0; k < nwords; k++) ptrpos0[start_ptr * nwords + k] = ~0ULL;

    Node *cur = malloc(sizeof(Node));
    cur[0].word[0] = '\0';
    cur[0].cell = cell0;
    cur[0].ptrpos = ptrpos0;
    int cur_n = 1;

    int all_found = 0;
    for (int length = 1; length <= 12 && !all_found; length++) {
        Node *next = malloc(sizeof(Node) * (size_t)cur_n * 2);
        int next_n = 0;
        for (int ni = 0; ni < cur_n; ni++) {
            for (int li = 0; li < 2; li++) {
                Bundle b = (li == 0) ? pair.A : pair.B;
                char letter = (li == 0) ? 'A' : 'B';
                u64 *cc = alloc_state(W, nwords);
                u64 *pp = alloc_state(W, nwords);
                memcpy(cc, cur[ni].cell, sizeof(u64) * (size_t)W * nwords);
                memcpy(pp, cur[ni].ptrpos, sizeof(u64) * (size_t)W * nwords);
                int leaked = apply_letter(b, cc, pp, W, nwords);
                if (leaked) { free(cc); free(pp); continue; }
                Node *node = &next[next_n++];
                strcpy(node->word, cur[ni].word);
                int wl = (int)strlen(node->word);
                node->word[wl] = letter;
                node->word[wl + 1] = '\0';
                node->cell = cc;
                node->ptrpos = pp;
                for (int t = 0; t < 6; t++) {
                    if (found_len[t] >= 0) continue;
                    if (check_target(t, cc, pp, gc, pattern, xslot, start_ptr)) {
                        strcpy(found[t], node->word);
                        found_len[t] = length;
                    }
                }
            }
        }
        for (int ni = 0; ni < cur_n; ni++) { free(cur[ni].cell); free(cur[ni].ptrpos); }
        free(cur);
        cur = next;
        cur_n = next_n;
        all_found = 1;
        for (int t = 0; t < 6; t++) if (found_len[t] < 0) all_found = 0;
        if (cur_n == 0) break;
    }
    for (int ni = 0; ni < cur_n; ni++) { free(cur[ni].cell); free(cur[ni].ptrpos); }
    free(cur);
}

/* ---------------- driver ------------------------------------------------ */

int main(void) {
    Pair pairs[64];
    int npairs = gen_pairs(pairs);
    fprintf(stderr, "npairs=%d\n", npairs);

    GConfig gc1, gc2, gc3;
    build_gconfig(&gc1, 1, 7);
    build_gconfig(&gc2, 2, 4);
    build_gconfig(&gc3, 3, 3);
    fprintf(stderr, "g=1: n_groups=%d W=%d V=%lld nwords=%d\n", gc1.n_groups, gc1.W, gc1.V, gc1.nwords);
    fprintf(stderr, "g=2: n_groups=%d W=%d V=%lld nwords=%d\n", gc2.n_groups, gc2.W, gc2.V, gc2.nwords);
    fprintf(stderr, "g=3: n_groups=%d W=%d V=%lld nwords=%d\n", gc3.n_groups, gc3.W, gc3.V, gc3.nwords);

    FILE *out = fopen("/home/user/toffoli-ring/results/twoop/stateless_full_complete.csv", "w");
    fprintf(out, "pair_idx,A,B,pair_label,family,encoding,g,rest,target,macro,length\n");

    for (int pi = 0; pi < npairs; pi++) {
        char astr[32], bstr[32], label[80];
        bundle_str(pairs[pi].A, astr);
        bundle_str(pairs[pi].B, bstr);
        sprintf(label, "A=(%s) B=(%s)", astr, bstr);

        for (int ei = 0; ei < 19; ei++) {
            Enc *e = &ENCODINGS[ei];
            GConfig *gc = e->g == 1 ? &gc1 : (e->g == 2 ? &gc2 : &gc3);
            char encstr[16];
            pattern_str(e->pattern, e->g, encstr);
            for (int rest = 0; rest < e->g; rest++) {
                char found[6][13];
                int found_len[6];
                search_combo(pairs[pi], e->pattern, e->g, rest, gc, found, found_len);
                for (int t = 0; t < 6; t++) {
                    if (found_len[t] >= 0) {
                        fprintf(out, "%d,\"%s\",\"%s\",\"%s\",%s,\"%s\",%d,%d,%s,%s,%d\n",
                                pi, astr, bstr, label, e->family, encstr, e->g, rest,
                                TARGETS[t], found[t], found_len[t]);
                    } else {
                        fprintf(out, "%d,\"%s\",\"%s\",\"%s\",%s,\"%s\",%d,%d,%s,none<=12,\n",
                                pi, astr, bstr, label, e->family, encstr, e->g, rest,
                                TARGETS[t]);
                    }
                }
            }
        }
        fprintf(stderr, "pair %d/%d done\n", pi + 1, npairs);
    }

    fclose(out);
    return 0;
}
