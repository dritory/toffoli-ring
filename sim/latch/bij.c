/* Exhaustive bijectivity check of the pass map on (s,q) for N=8..12, k=2,3.
 * Reads pairs "f_hex g_hex label" from argv[1], writes "f_hex g_hex yes|no". */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

static inline int tt_eval(int tt, int q, int x, int a, int b) {
    int idx = (q << 3) | (x << 2) | (a << 1) | b;
    return (tt >> idx) & 1;
}

static inline uint32_t do_pass(uint32_t s, int N, int k, int f_tt, int g_tt, int *qp) {
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

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: %s pairs.txt\n", argv[0]); return 1; }
    FILE *pf = fopen(argv[1], "r");
    if (!pf) { perror("pairs"); return 1; }
    char line[256];
    int Ns[5] = {8, 9, 10, 11, 12};
    int ks[2] = {2, 3};
    /* max state space: N=12 -> 2^13 = 8192 states (s,q) combined key */
    static uint8_t seen[1u << 13];
    while (fgets(line, sizeof(line), pf)) {
        unsigned fh, gh; char label[64] = "";
        int nf = sscanf(line, "%x %x %63s", &fh, &gh, label);
        if (nf < 2) continue;
        int bijective = 1;
        for (int ni = 0; ni < 5 && bijective; ni++) {
            int N = Ns[ni];
            for (int ki = 0; ki < 2 && bijective; ki++) {
                int k = ks[ki];
                uint32_t total = (1u << N) * 2u;
                memset(seen, 0, total);
                for (uint32_t m = 0; m < (1u << N) && bijective; m++) {
                    for (int q0 = 0; q0 <= 1; q0++) {
                        int q = q0;
                        uint32_t out_s = do_pass(m, N, k, (int)fh, (int)gh, &q);
                        uint32_t key = (out_s << 1) | (uint32_t)q;
                        if (seen[key]) { bijective = 0; break; }
                        seen[key] = 1;
                    }
                }
            }
        }
        printf("%04x %04x %s\n", fh, gh, bijective ? "yes" : "no");
    }
    fclose(pf);
    return 0;
}
