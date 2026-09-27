# Goal

The fewest discrete components (transistors, resistors, capacitors, diodes; no ICs or relays) that make a universal computer: runs any program with constant-factor slowdown relative to a Turing machine, with runtime I/O through memory cells. Data memory, program storage, clock drive and power are excluded.

Current best: 11 components (6 transistors, 3 resistors, 2 capacitors; master capacitor must be several times larger than the slave, since they share charge), the two-instruction machine (STATUS.md, sim/budget/).

Capacitor-free (static latches, for the first prototype): 20 components (14 transistors, 6 resistors), sim/budget/static/.

Open: (1) minimality proof, (2) physical build, (3) hand-written demos visible at wall-clock speed.
