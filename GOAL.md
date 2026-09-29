# Goal

The fewest components for a computer that runs structured programs directly. By the structured program theorem (Böhm–Jacopini) every program is one loop of if-blocks; the program ring is that loop, and the CPU provides the if-blocks with a block skip ("if the cell is 0, skip until the next MARK"). Instructions: FLIP, NEXT, PREV, IFZ, MARK. Each instruction costs one tick; each outer-loop iteration costs one ring pass. Data memory, program storage, clock drive and power are excluded from the count.

Current results (results/budget/blockskip.md, verified: truth table, 500 random programs tick by tick, DC voltage checks):
* NMOS with resistor pull-ups: 10 transistors, 6 resistors, plus 6 indicator LEDs (5 V, logic-level NMOS).
* LED diode-transistor logic: 3 transistors, 9 resistors, 15 LEDs that do the logic (12 V, standard-threshold NMOS).
* Programs: 8-bit counter 40 ticks per increment, echo 10 ticks, 8-bit copy 80 ticks, BB(2,2) 262 ticks per Turing-machine step.

History and earlier results below.

## Earlier goal

The fewest discrete components (transistors, resistors, capacitors, diodes; no ICs or relays) that make a universal computer: runs any program with constant-factor slowdown relative to a Turing machine, with runtime I/O through memory cells. Data memory, program storage, clock drive and power are excluded.

Current best: 11 components (6 transistors, 3 resistors, 2 capacitors; master capacitor must be several times larger than the slave, since they share charge), the two-instruction machine (STATUS.md, sim/budget/).

Capacitor-free (static latches, for the first prototype): 20 components (14 transistors, 6 resistors), sim/budget/static/. Pure transistor, fully complementary CMOS: 28 transistors, no ratio requirement, near-zero standby power, sim/budget/cmos/.

Open: (1) minimality proof, (2) physical build, (3) hand-written demos visible at wall-clock speed.

## Prior art (checked 2026-09-27, web search only)

* Qibec (Michai Ramakers, 2016): 1-bit, 1-instruction discrete-transistor CPU (invert, then jump if zero). About 650 transistors in total; the core is 8 transistors, the rest is address bus and program counter.
* Carbon-nanotube OISC (2013): 178 transistors.
* Hobby builds: subleq CPU about 680 transistors (2025), TraNOR 1897 MOSFETs, Megaprocessor 15,300.

Consequence: "smallest CPU core" is not a clear record (Qibec's core is 8 transistors). The defensible claim is about the whole machine minus bit storage: this design needs no address registers or program counter because the data pointer and the program advance by ±1 / +1 only. That shifts cost into the memory's shift mechanics, which must be stated on the plaque.

## Prior art, second search (2026-09-29)

* Neon lamp + photoconductor logic: NOR, flip-flops and ring counters date from the 1950s (Electronics, April 1953); modern makers have rebuilt gates and a D flip-flop.
* A CPU-less computer whose only ALU is one NOR gate made of 2 transistors and 1 resistor; sequencing lives in ROM and counters.
* Minimal TTL chip-count CPUs (CSCvon8, 17 chips; "1 square inch TTL CPU").
* Closest architecture, from memory, not re-checked here: Motorola MC14500B, a 1-bit industrial control unit with a skip-if-zero instruction, run from an external program counter as a cyclic PLC-style scan.

Elimination view: known designs drop the ALU (NOR-gate computer), the instruction set (OISC), or the core size (Qibec). None found drops all of: program counter (program is a physical loop), data addresses (tape with ±1 moves), ALU (toggle only), and jumps (block skip plus the structured program theorem), leaving one bit of CPU state. That combination is the candidate novelty; claim it as "not found in prior art searched", not as a first.
