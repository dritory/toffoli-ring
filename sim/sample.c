/* Sampled orbit periods for larger N (Brent's cycle finding, exact period of
 * the orbit through a random state). Usage: sample N k samples [seed]
 * Requires N <= 64. Prints one period per line, then summary.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

static inline uint64_t pass(uint64_t s, int n, int k) {
    uint64_t m = (n == 64) ? ~0ULL : ((1ULL << n) - 1);
    for (int i = 0; i < n; i++) {
        int i1 = (i + 1 == n) ? 0 : i + 1;
        if (((s >> i) & 1) && ((s >> i1) & 1)) {
            int t = i + k; if (t >= n) t -= n;
            s ^= (1ULL << t);
        }
    }
    return s & m;
}
static uint64_t rng = 88172645463325252ULL;
static uint64_t xs(void) { rng ^= rng << 13; rng ^= rng >> 7; rng ^= rng << 17; return rng; }

int main(int argc, char **argv) {
    int n = atoi(argv[1]), k = atoi(argv[2]), samples = atoi(argv[3]);
    if (argc > 4) rng ^= strtoull(argv[4], 0, 10) * 0x9E3779B97F4A7C15ULL;
    uint64_t limit = (argc > 5) ? strtoull(argv[5], 0, 10) : 4000000000ULL;
    uint64_t mask = (n == 64) ? ~0ULL : ((1ULL << n) - 1);
    double sumlog = 0; uint64_t maxp = 0; int ok = 0;
    for (int i = 0; i < samples; i++) {
        uint64_t s0 = xs() & mask;
        /* the map is a bijection so the orbit of s0 is a pure cycle:
           count steps until return. */
        uint64_t s = pass(s0, n, k), p = 1;
        while (s != s0 && p < limit) { s = pass(s, n, k); p++; }
        if (s != s0) { printf("%d >%llu\n", i, (unsigned long long)limit); continue; }
        printf("%d %llu\n", i, (unsigned long long)p);
        ok++;
        if (p > maxp) maxp = p;
        sumlog += __builtin_log2((double)p);
    }
    printf("summary N=%d k=%d samples_ok=%d maxperiod=%llu mean_log2period=%.2f\n",
           n, k, ok, (unsigned long long)maxp, ok ? sumlog / ok : 0.0);
    return 0;
}
