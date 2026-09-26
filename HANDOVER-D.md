# Handover D: the 4-, 8-, 16- and 32-transistor computers

Goal: for each budget X in {4, 8, 16, 32}, the most capable computer whose CPU fits in X transistors, with a compiler, a demo, and a score card. Nothing above 32.

## 1. Rules

**What counts.** Transistors in the CPU. DTL: diodes and resistors are free; every transistor is counted, including inverters, restoring amplifiers and latch transistors. A diode gate may feed at most two further diode levels before a transistor must restore it (state the rule you use and keep it fixed).

**Memory interface (excluded from the count).** Data memory offers: the read bit r of the cell under the pointer, a toggle strobe, and move strobes (+1, −1). Program memory is a ring of instructions advancing one per tick and supplies each opcode bit in both polarities. Clock: the drum or program-ring drive supplies the clock phases (two non-overlapping phases if needed), not counted. Anything that generates strobes from (opcode, r, CPU state) is CPU and is counted.

**What "can do" means.** Every machine must be universal, with runtime I/O through memory-mapped cells. Score card:
* ticks per Brainfuck instruction, averaged over a fixed suite: increment an 8-bit counter, copy a byte, compare two bytes, echo input to output;
* physical memory bits per logical bit;
* program bits per Brainfuck instruction;
* whether a human can write it by hand.

## 2. Working hypothesis: the budget buys CPU state

With free diode logic and dual-rail opcodes, decoding and combinational logic are nearly free. The cost is state: one clocked bit (master-slave latch) is about 4 transistors, plus inverters where a complement is not already available. So 4/8/16/32 transistors ≈ 1/2/4/8 bits of CPU state. First task: confirm or break this with real schematics.

Candidates per budget (hypotheses, to be priced and compiled):
* **4: one state bit, the skip flag.** The verified two-instruction machine (flip; skip next iff the cell is now 0; move by opcode). Also check whether the reference 4-op machine (FLIP, NEXT, PREV, SKIPZ) fits in the same 4 transistors when opcodes are dual-rail from program memory: it needs no dual-rail data and runs about 8× fewer ticks per operation.
* **8: two state bits.** Skip flag plus a block-skip mode: an instruction starts skipping and an END instruction stops it, giving real if-blocks instead of branch-flip-merge gadgets. Alternative: skip flag plus a one-bit accumulator or carry.
* **16: four state bits.** Nested block skips via a small depth counter, so Brainfuck loops compile directly with bounded nesting; or a bit-serial ALU with carry and accumulator.
* **32: eight state bits.** A small counter or register: e.g. an addressable program counter with a conditional jump (then program memory need not be a ring), or a byte-serial data path. Pick whichever wins the score card.

## 3. Tasks

1. Schematic and count for the verified two-instruction machine under the rules above. Write a switch-level simulator (transistors as switches, diodes as ideal, resistive pull-ups) with the two clock phases and the memory interface, and show it executes the verified macros identically to `sim/compile/verify_level0_independent.py`'s simulator. Report the exact transistor count. Do the same for the 4-op machine.
2. Price list: transistor cost of each feature (skip flag, block-skip mode, depth counter bit, accumulator bit, carry, program counter bit, conditional jump), each confirmed by a switch-level simulated schematic.
3. For each budget: choose the design from the price list, specify the ISA, write the compiler (Brainfuck subset to the ISA), run the benchmark suite in the simulator, fill in the score card.
4. Final table: budget, ISA, transistor count, score card, and one plaque line per machine.

## 4. Deliverables

`results/budget/` with the schematics (netlist text), simulators, compilers, benchmark logs, and a one-page summary table. Every claimed count must come from a simulated schematic, not an estimate.
