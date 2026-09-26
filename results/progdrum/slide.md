# Task 2b: generalised slide N = mP-s

## 1. Verification: generalised static frame (N = mP-s)

500 random instances per s (s = 1..11), each with a random P > s (P in [s+1,14]), m in [2,10], k in [2,6] (N=mP-s > k+1 enforced by resampling). Compares the literal machine against `static_frame_rows(..., s=s)` for 5 rows beyond row 0 (row 0 seeded from the literal trace).


| s | instances | matched | mismatches |
|---|---|---|---|

| 1 | 500 | 500 | 0 |

| 2 | 500 | 500 | 0 |

| 3 | 500 | 500 | 0 |

| 4 | 500 | 500 | 0 |

| 5 | 500 | 500 | 0 |

| 6 | 500 | 500 | 0 |

| 7 | 500 | 500 | 0 |

| 8 | 500 | 500 | 0 |

| 9 | 500 | 500 | 0 |

| 10 | 500 | 500 | 0 |

| 11 | 500 | 500 | 0 |


No mismatches: the generalised static frame (copy sites read u_{r-1}(x+s), with the last s columns of a copy site reading the same row's columns [0,s-1]) is confirmed identical to the literal machine for every s tested.


## 2. Gadget search across s (k=2,3, P=4..12, m=12)

Total stationary programs found (summed over all P,s): 54320


slide.csv is one row per PROGRAM (program,k,P,s,n_dies,n_memory,n_moves_left,n_moves_right,n_grows,fastest_left_speed_sites_per_row,fastest_right_speed_sites_per_row,interacts,interact_first_row_diff) rather than one row per (program,position) as in gadgets.csv: with 54320 programs (vs. task 2's 2893) a per-position CSV would be ~60MB, over the 10MB budget.


### k=2

| s | programs tested (this s) | class counts (programs w/ occurrence) | fastest left (sites/row) | fastest right (sites/row) | cheapest per class |

|---|---|---|---|---|---|

| 1 | 8158 | dies:25, memory:0, moves_left:0, moves_right:0, grows:25 | - | - | dies:P=6,ones=4,p=`101101`; memory:-; moves_left:-; moves_right:-; grows:P=6,ones=4,p=`101101` |

| 2 | 8158 | dies:467, memory:0, moves_left:238, moves_right:66, grows:78 | 2.050 (P=4,p=`0001`,off=0) | 10.145 (P=11,p=`11110101110`,off=8) | dies:P=4,ones=1,p=`1000`; memory:-; moves_left:P=4,ones=1,p=`1000`; moves_right:P=4,ones=3,p=`1110`; grows:P=7,ones=4,p=`1101010` |

| 3 | 8158 | dies:7569, memory:6078, moves_left:924, moves_right:0, grows:521 | 3.125 (P=6,p=`110000`,off=5) | - | dies:P=4,ones=2,p=`1100`; memory:P=4,ones=3,p=`1110`; moves_left:P=6,ones=1,p=`100000`; moves_right:-; grows:P=4,ones=2,p=`1100` |

| 4 | 8144 | dies:2394, memory:11, moves_left:2240, moves_right:0, grows:83 | 4.267 (P=6,p=`100000`,off=5) | - | dies:P=5,ones=2,p=`11000`; memory:P=11,ones=5,p=`11100101000`; moves_left:P=5,ones=2,p=`11000`; moves_right:-; grows:P=6,ones=4,p=`101101` |

| 5 | 8114 | dies:1976, memory:0, moves_left:1805, moves_right:14, grows:16 | 5.250 (P=10,p=`1000000000`,off=1) | 9.300 (P=10,p=`1111110110`,off=4) | dies:P=6,ones=2,p=`110000`; memory:-; moves_left:P=6,ones=2,p=`110000`; moves_right:P=7,ones=6,p=`1111110`; grows:P=7,ones=4,p=`1011010` |

| 6 | 8052 | dies:5602, memory:1041, moves_left:3795, moves_right:0, grows:650 | 6.450 (P=8,p=`10000000`,off=1) | - | dies:P=7,ones=2,p=`1100000`; memory:P=7,ones=6,p=`1111110`; moves_left:P=7,ones=2,p=`1100000`; moves_right:-; grows:P=7,ones=4,p=`1101100` |

| 7 | 7926 | dies:2642, memory:11, moves_left:1852, moves_right:0, grows:636 | 6.800 (P=8,p=`11000000`,off=1) | - | dies:P=8,ones=2,p=`11000000`; memory:P=9,ones=5,p=`111010100`; moves_left:P=8,ones=2,p=`11000000`; moves_right:-; grows:P=9,ones=4,p=`101101000` |

| 8 | 7672 | dies:2089, memory:0, moves_left:1956, moves_right:4, grows:19 | 8.560 (P=10,p=`1000000000`,off=1) | 9.300 (P=10,p=`1111111110`,off=7) | dies:P=9,ones=2,p=`110000000`; memory:-; moves_left:P=9,ones=2,p=`110000000`; moves_right:P=10,ones=9,p=`1111111110`; grows:P=10,ones=6,p=`1011011010` |

| 9 | 7162 | dies:2887, memory:243, moves_left:2262, moves_right:0, grows:438 | 9.600 (P=12,p=`101000000000`,off=1) | - | dies:P=10,ones=2,p=`1100000000`; memory:P=10,ones=9,p=`1111111110`; moves_left:P=10,ones=2,p=`1100000000`; moves_right:-; grows:P=10,ones=6,p=`1101101100` |

| 10 | 6140 | dies:1333, memory:52, moves_left:878, moves_right:0, grows:161 | 10.750 (P=12,p=`100000000000`,off=1) | - | dies:P=11,ones=2,p=`11000000000`; memory:P=12,ones=8,p=`111111010100`; moves_left:P=11,ones=2,p=`11000000000`; moves_right:-; grows:P=12,ones=6,p=`101101101000` |

| 11 | 4094 | dies:1208, memory:0, moves_left:861, moves_right:0, grows:0 | 11.521 (P=12,p=`001100000000`,off=10) | - | dies:P=12,ones=2,p=`110000000000`; memory:-; moves_left:P=12,ones=2,p=`110000000000`; moves_right:-; grows:- |


### k=3

| s | programs tested (this s) | class counts (programs w/ occurrence) | fastest left (sites/row) | fastest right (sites/row) | cheapest per class |

|---|---|---|---|---|---|

| 1 | 8158 | dies:690, memory:0, moves_left:0, moves_right:128, grows:271 | - | 8.300 (P=9,p=`110010100`,off=0) | dies:P=4,ones=2,p=`1010`; memory:-; moves_left:-; moves_right:P=4,ones=2,p=`1001`; grows:P=5,ones=2,p=`10100` |

| 2 | 8158 | dies:347, memory:0, moves_left:238, moves_right:9, grows:50 | 2.050 (P=4,p=`1000`,off=1) | 15.472 (P=9,p=`101110111`,off=3) | dies:P=4,ones=1,p=`1000`; memory:-; moves_left:P=4,ones=1,p=`1000`; moves_right:P=4,ones=3,p=`1011`; grows:P=5,ones=2,p=`10010` |

| 3 | 8158 | dies:327, memory:0, moves_left:75, moves_right:12, grows:194 | 3.125 (P=6,p=`100000`,off=4) | 18.909 (P=11,p=`11110111111`,off=7) | dies:P=5,ones=2,p=`10100`; memory:-; moves_left:P=6,ones=1,p=`100000`; moves_right:P=6,ones=5,p=`111110`; grows:P=5,ones=2,p=`10100` |

| 4 | 8144 | dies:3463, memory:12, moves_left:2313, moves_right:157, grows:432 | 4.267 (P=6,p=`100000`,off=5) | 10.155 (P=11,p=`11010111111`,off=8) | dies:P=5,ones=2,p=`10100`; memory:P=12,ones=10,p=`111111011110`; moves_left:P=6,ones=1,p=`100000`; moves_right:P=11,ones=6,p=`11110010100`; grows:P=5,ones=2,p=`10100` |

| 5 | 8114 | dies:7239, memory:3063, moves_left:774, moves_right:0, grows:3137 | 5.250 (P=10,p=`1000000000`,off=1) | - | dies:P=6,ones=2,p=`101000`; memory:P=6,ones=5,p=`111110`; moves_left:P=10,ones=1,p=`1000000000`; moves_right:-; grows:P=6,ones=2,p=`101000` |

| 6 | 8052 | dies:4189, memory:285, moves_left:3559, moves_right:24, grows:693 | 6.450 (P=8,p=`10000000`,off=1) | 8.328 (P=9,p=`111101010`,off=1) | dies:P=7,ones=2,p=`1010000`; memory:P=9,ones=3,p=`110100000`; moves_left:P=7,ones=2,p=`1010000`; moves_right:P=8,ones=6,p=`10111011`; grows:P=7,ones=4,p=`1101010` |

| 7 | 7926 | dies:490, memory:0, moves_left:237, moves_right:2, grows:110 | 6.335 (P=10,p=`1001000000`,off=3) | 15.467 (P=9,p=`111111011`,off=4) | dies:P=8,ones=2,p=`10100000`; memory:-; moves_left:P=8,ones=2,p=`10100000`; moves_right:P=9,ones=8,p=`111111011`; grows:P=9,ones=2,p=`101000000` |

| 8 | 7672 | dies:2637, memory:0, moves_left:2322, moves_right:3, grows:191 | 8.560 (P=10,p=`1000000000`,off=1) | 18.905 (P=11,p=`01111111111`,off=8) | dies:P=9,ones=2,p=`101000000`; memory:-; moves_left:P=9,ones=2,p=`101000000`; moves_right:P=11,ones=10,p=`11111111110`; grows:P=10,ones=4,p=`1111000000` |

| 9 | 7162 | dies:1949, memory:24, moves_left:791, moves_right:2, grows:838 | 9.600 (P=12,p=`100000000000`,off=1) | 5.775 (P=12,p=`111110111110`,off=2) | dies:P=10,ones=2,p=`1010000000`; memory:P=11,ones=6,p=`10101101100`; moves_left:P=10,ones=2,p=`1010000000`; moves_right:P=12,ones=10,p=`111110111110`; grows:P=10,ones=4,p=`1010010100` |

| 10 | 6140 | dies:2916, memory:80, moves_left:519, moves_right:0, grows:1576 | 10.750 (P=12,p=`100000000000`,off=1) | - | dies:P=11,ones=2,p=`10100000000`; memory:P=11,ones=10,p=`11111111110`; moves_left:P=11,ones=2,p=`10100000000`; moves_right:-; grows:P=11,ones=4,p=`10100101000` |

| 11 | 4094 | dies:1881, memory:0, moves_left:971, moves_right:0, grows:101 | 11.121 (P=12,p=`111010000000`,off=4) | - | dies:P=12,ones=2,p=`101000000000`; memory:-; moves_left:P=12,ones=2,p=`101000000000`; moves_right:-; grows:P=12,ones=7,p=`110101101010` |
