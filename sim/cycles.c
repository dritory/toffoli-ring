/* Exhaustive cycle structure of the pass map T_{N,k} on {0,1}^N.
 * Usage: cycles N k          (N <= 30 practical)
 * Prints: number of cycles, max period, histogram of periods, fixed points.
 * Bit i of the state word is ring cell i.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

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

int main(int argc, char **argv) {
    int n = atoi(argv[1]), k = atoi(argv[2]);
    uint64_t total = 1ULL << n;
    uint8_t *seen = calloc(total / 8 + 1, 1);
    /* period histogram via a hash map would be overkill; store periods in a
       dynamic array of (period,count) pairs */
    uint64_t maxp = 0, ncycles = 0;
    size_t cap = 1024, cnt = 0;
    uint64_t *per = malloc(cap * sizeof(uint64_t));
    uint64_t *num = malloc(cap * sizeof(uint64_t));
    for (uint64_t s0 = 0; s0 < total; s0++) {
        if (seen[s0 >> 3] & (1 << (s0 & 7))) continue;
        uint64_t s = s0, p = 0;
        do {
            seen[s >> 3] |= (1 << (s & 7));
            s = pass(s, n, k);
            p++;
        } while (s != s0);
        ncycles++;
        if (p > maxp) maxp = p;
        size_t j;
        for (j = 0; j < cnt; j++) if (per[j] == p) { num[j]++; break; }
        if (j == cnt) {
            if (cnt == cap) { cap *= 2; per = realloc(per, cap * 8); num = realloc(num, cap * 8); }
            per[cnt] = p; num[cnt] = 1; cnt++;
        }
    }
    /* sort histogram by period */
    for (size_t a = 0; a < cnt; a++) for (size_t b = a + 1; b < cnt; b++)
        if (per[b] < per[a]) { uint64_t t = per[a]; per[a] = per[b]; per[b] = t; t = num[a]; num[a] = num[b]; num[b] = t; }
    printf("N=%d k=%d states=%llu cycles=%llu maxperiod=%llu distinct_periods=%zu\n",
           n, k, (unsigned long long)total, (unsigned long long)ncycles, (unsigned long long)maxp, cnt);
    printf("hist:");
    for (size_t j = 0; j < cnt; j++) printf(" %llu:%llu", (unsigned long long)per[j], (unsigned long long)num[j]);
    printf("\n");
    return 0;
}
