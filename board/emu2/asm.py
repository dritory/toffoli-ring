"""Assembler for the ENCODING.md machine. One source line = one word (macros are marked).
Syntax: dest first.  LOAD A, #5 | LOAD A, [var] | LOAD A, [X+] | LOAD C, A | LOAD X, #label
        ADD #1 | ADC [x] | CMP C | SHL | JUMP NZ, loop | CALL f | RET | RETI | DJNZ loop
        STORE [var], A | STORE [X+], A | PUSH A | POP C | MUL #3 | DIV [d]
Directives: .code .data .org .equ NAME=expr .byte .word .space n[,fill] .string "x"
            .include "f" .macro NAME / .endm (args \\1..\\9)"""
import re, sys, os
from isa import *


class AsmError(Exception):
    pass


CONDS = {"NEVER": C_NEVER, "Z": C_Z, "C": C_C, "ZC": C_ZC, "": C_ALWAYS, "ALWAYS": C_ALWAYS,
         "NZ": C_NZ, "NC": C_NC, "HI": C_HI, "EQ": C_Z, "NE": C_NZ, "LT": C_C, "GE": C_NC,
         "LE": C_ZC, "GT": C_HI}
REGS = {"A": R_A, "C": R_C, "XL": R_XL, "XH": R_XH, "X": R_X, "SP": R_SP, "RSP": R_RSP, "F": R_F}
REGSRC = {"A": S_A, "C": S_C, "XL": S_XL, "XH": S_XH}
ARITH = {"ADD": (ADD, 0, 1), "ADC": (ADD, 1, 1), "SUB": (SUB, 0, 1), "SBC": (SUB, 1, 1),
         "CMP": (SUB, 0, 0), "AND": (AND, 0, 1), "OR": (OR, 0, 1), "XOR": (XOR, 0, 1),
         "TEST": (AND, 0, 0)}          # name -> (opcode, carry, keep)
SHIFTS = {"SHL": (SHL, 0), "ROL": (SHL, 1), "SHR": (SHR, 0), "ROR": (SHR, 1)}
LOOKS = {"MUL": T_MUL, "MULH": T_MULH, "DIV": T_DIV, "MOD": T_MOD}


class Program:
    def __init__(self):
        self.words = []; self.data = []; self.symbols = {}; self.regions = []
        self.listing = []; self.lines = {}   # word index -> (file, lineno, text)

    def data_image(self):
        return [(a, bytes(b)) for a, b in self.data]


def split_args(s):
    out, cur, depth, q = [], "", 0, None
    for ch in s:
        if q:
            cur += ch
            if ch == q: q = None
        elif ch in "'\"": q = ch; cur += ch
        elif ch in "([": depth += 1; cur += ch
        elif ch in ")]": depth -= 1; cur += ch
        elif ch == "," and depth == 0: out.append(cur.strip()); cur = ""
        else: cur += ch
    if cur.strip(): out.append(cur.strip())
    return out


def strip_comment(line):
    q = None
    for i, ch in enumerate(line):
        if q:
            if ch == q: q = None
        elif ch in "'\"": q = ch
        elif ch == ";": return line[:i]
    return line


class Assembler:
    def __init__(self):
        self.sym = {k: v for k, v in vars(__import__("isa")).items()
                    if k in ("BTN IRQ_EN IRQ_CAUSE FRAME RNG LCD_CMD LCD_DATA LED TBL0 BTN_UP BTN_DOWN BTN_LEFT BTN_RIGHT "
                             "LCD_W LCD_H STACK_PAGE").split()}
        self.sym.update(TBL1=TBL0 + 1, TBL2=TBL0 + 2, TBL3=TBL0 + 3)
        self.macros = {}
        self.p = Program()

    # ---- expressions ----
    def ev(self, expr, where, pc=0, final=True):
        env = dict(self.sym)
        env.update(lo=lambda v: v & 255, hi=lambda v: (v >> 8) & 255, __builtins__={})
        env["__pc"] = pc
        e = expr.replace("$", "__pc")
        try:
            return int(eval(e, env))
        except NameError as ex:
            if final: raise AsmError("%s: undefined symbol in '%s'" % (where, expr))
            return None
        except Exception as ex:
            raise AsmError("%s: bad expression '%s' (%s)" % (where, expr, ex))

    # ---- source expansion: includes and macros ----
    def expand(self, path, text, out, depth=0):
        if depth > 20: raise AsmError("include/macro nesting too deep")
        cur = None
        for n, raw in enumerate(text.splitlines(), 1):
            where = "%s:%d" % (os.path.basename(path), n)
            line = strip_comment(raw).strip()
            m = re.match(r"\.macro\s+(\w+)", line, re.I)
            if m:
                cur = (m.group(1).upper(), []); continue
            if re.match(r"\.endm", line, re.I):
                self.macros[cur[0]] = cur[1]; cur = None; continue
            if cur: cur[1].append(raw); continue
            m = re.match(r'\.include\s+"([^"]+)"', line, re.I)
            if m:
                fn = os.path.join(os.path.dirname(path) or ".", m.group(1))
                self.expand(fn, open(fn).read(), out, depth + 1); continue
            lab = re.match(r"^(\w+):\s*(.*)$", line)
            body = lab.group(2) if lab else line
            head = body.split(None, 1)
            if head and head[0].upper() in self.macros:
                if lab: out.append((where, raw, lab.group(1) + ":", None))
                args = split_args(head[1]) if len(head) > 1 else []
                name = head[0].upper()
                sub = []
                self.nmac = getattr(self, "nmac", 0) + 1
                for bl in self.macros[name]:
                    bl = bl.replace("\\@", "_m%d" % self.nmac)
                    for i, a in enumerate(args, 1): bl = bl.replace("\\%d" % i, a)
                    sub.append(bl)
                tmp = []
                self.expand(path, "\n".join(sub), tmp, depth + 1)
                for w2, r2, l2, m2 in tmp:
                    out.append((where, r2.strip(), l2, m2 or "macro " + name))
                continue
            out.append((where, raw, line, None))

    # ---- passes ----
    def assemble(self, text, path="<src>"):
        items = []
        self.expand(path, text, items)
        # pass 1: addresses
        pc = 0; dp = DATA_BASE; sect = "code"; recs = []
        regions = []; lastlab = None
        for where, raw, line, mac in items:
            if not line: recs.append((where, raw, None, None, 0, mac)); continue
            labs = []
            while True:
                m = re.match(r"^([A-Za-z_]\w*):\s*(.*)$", line)
                if not m: break
                labs.append(m.group(1)); line = m.group(2)
            for l in labs:
                if l in self.sym: raise AsmError("%s: duplicate symbol %s" % (where, l))
                self.sym[l] = pc if sect == "code" else dp
                if sect == "data": lastlab = [l, dp, dp]; regions.append(lastlab)
            m = re.match(r"^([A-Za-z_]\w*)\s*=\s*(.*)$", line)
            if m:
                self.sym[m.group(1)] = self.ev(m.group(2), where, pc); recs.append((where, raw, None, None, 0, mac)); continue
            if not line:
                recs.append((where, raw, None, None, 0, mac)); continue
            parts = line.split(None, 1); mn = parts[0].upper(); rest = parts[1] if len(parts) > 1 else ""
            if mn.startswith("."):
                a = split_args(rest)
                if mn == ".CODE": sect = "code"
                elif mn == ".DATA": sect = "data"
                elif mn == ".ORG":
                    v = self.ev(a[0], where, pc)
                    if sect == "code": pc = v
                    else: dp = v; lastlab = None
                elif mn == ".EQU":
                    nm, _, ex = rest.partition("=") if "=" in rest else (a[0], "", a[1])
                    self.sym[nm.strip()] = self.ev(ex, where, pc)
                elif mn in (".BYTE", ".WORD", ".SPACE", ".STRING"):
                    if sect != "data": raise AsmError("%s: %s only in .data (program memory is not readable)" % (where, mn))
                    size = (len(a) if mn == ".BYTE" else 2 * len(a) if mn == ".WORD" else
                            self.ev(a[0], where) if mn == ".SPACE" else len(eval(a[0])))
                    recs.append((where, raw, ("data", mn, a, dp), None, size, mac))
                    if lastlab: lastlab[2] = dp + size
                    else: regions.append(["<anon>", dp, dp + size])
                    dp += size; continue
                else: raise AsmError("%s: unknown directive %s" % (where, mn))
                recs.append((where, raw, None, None, 0, mac)); continue
            if sect != "code": raise AsmError("%s: instruction in .data" % where)
            recs.append((where, raw, ("code", mn, split_args(rest)), None, pc, mac)); pc += 1
        # region sanity
        occ = sorted((lo, hi, nm) for nm, lo, hi in regions if hi > lo)
        for (l1, h1, n1), (l2, h2, n2) in zip(occ, occ[1:]):
            if l2 < h1: raise AsmError("data regions overlap: %s [%04X,%04X) and %s [%04X,%04X)" % (n1, l1, h1, n2, l2, h2))
        for lo, hi, nm in occ:
            if lo < STACK_PAGE + 256 and hi > STACK_PAGE: raise AsmError("data region %s overlaps the data stack page" % nm)
            if hi > DEV_BASE: raise AsmError("data region %s overlaps the device page" % nm)
        self.p.regions = [(lo, hi) for lo, hi, nm in occ] + [(STACK_PAGE, STACK_PAGE + 256)]
        self.p.symbols = dict(self.sym)
        # pass 2: encode
        P = self.p; words = {}
        for where, raw, d, _, pcv, mac in recs:
            if d is None:
                if raw.strip(): P.listing.append(" " * 27 + raw.rstrip())
                continue
            if d[0] == "data":
                _, mn, a, addr = d; bs = []
                if mn == ".BYTE": bs = [self.ev(x, where) & 255 for x in a]
                elif mn == ".WORD":
                    for x in a: v = self.ev(x, where); bs += [v & 255, (v >> 8) & 255]
                elif mn == ".SPACE": bs = [self.ev(a[1], where) & 255 if len(a) > 1 else 0] * pcv
                else: bs = list(eval(a[0]).encode("latin1"))
                P.data.append((addr, bs))
                P.listing.append("D %04X %-20s %s" % (addr, " ".join("%02X" % b for b in bs[:6]) + (" .." if len(bs) > 6 else ""), raw.rstrip()))
                continue
            w = self.encode(d[1], d[2], where, pcv)
            words[pcv] = w; P.lines[pcv] = (where, raw)
            P.listing.append("%04X %s  %s%s" % (pcv, groups(w), raw.strip().ljust(0), "   [%s]" % mac if mac else ""))
        n = (max(words) + 1) if words else 0
        P.words = [words.get(i, 0) for i in range(n)]
        return P

    # ---- operands ----
    def operand(self, t, where, pc, allow_regs=("A", "C", "XL", "XH")):
        t = t.strip(); u = t.upper()
        if t.startswith("#"):
            v = self.ev(t[1:], where, pc); return (S_CONST, v, "const")
        if u == "[X]": return (S_X, 0, "x")
        if u in ("[X+]", "[X ++]"): return (S_XINC, 0, "xinc")
        if t.startswith("[") and t.endswith("]"):
            v = self.ev(t[1:-1], where, pc)
            if not 0 <= v < 65536: raise AsmError("%s: address out of range" % where)
            return (S_ABS, v, "abs")
        if u in REGSRC:
            return (REGSRC[u], 0, "reg")
        if u in REGS: raise AsmError("%s: register %s cannot be a calculation operand (only A, C, XL, XH)" % (where, u))
        raise AsmError("%s: operand '%s' needs # (constant), [..] (memory) or a register" % (where, t))

    def const8(self, v, where):
        if not -128 <= v <= 255: raise AsmError("%s: constant %d does not fit 8 bits" % (where, v))
        return v & 255

    def encode(self, mn, a, where, pc):
        def need(n):
            if len(a) != n: raise AsmError("%s: %s takes %d operand(s)" % (where, mn, n))
        if mn == "NOP": need(0); return encode(JUMP, S=C_ALWAYS, addr=pc + 1)
        if mn == "NOT": need(0); return encode(XOR, K=1, O=S_CONST, addr=0xFF)
        if mn == "RETI": need(0); return encode(RET, R=1, S=C_ALWAYS)
        if mn in ARITH or mn in LOOKS:
            if len(a) == 2 and a[0].upper() == "A": a = a[1:]
            need(1)
            O, v, kind = self.operand(a[0], where, pc)
            if kind == "const": v = self.const8(v, where)
            if mn in LOOKS: return encode(LOOKUP, S=LOOKS[mn], K=1, O=O, addr=v)
            op, y, k = ARITH[mn]
            return encode(op, K=k, Y=y, O=O, addr=v)
        if mn in SHIFTS:
            if len(a) == 1 and a[0].upper() == "A": a = []
            need(0); op, y = SHIFTS[mn]; return encode(op, K=1, Y=y)
        if mn in ("LOAD", "MOVE"):
            need(2); g = a[0].upper()
            if g not in REGS: raise AsmError("%s: bad destination register %s" % (where, a[0]))
            G = REGS[g]
            if G == R_X:
                if not a[1].startswith("#"): raise AsmError("%s: LOAD X takes a 16-bit constant only (#addr); use XL/XH otherwise" % where)
                v = self.ev(a[1][1:], where, pc)
                if not -32768 <= v <= 0xFFFF: raise AsmError("%s: constant out of 16 bits" % where)
                return encode(LOAD, G=G, O=S_CONST, addr=v & 0xFFFF)
            O, v, kind = self.operand(a[1], where, pc)
            if kind == "const": v = self.const8(v, where)
            if O == S_XINC and G in (R_XL, R_XH): raise AsmError("%s: LOAD %s,[X+] is ambiguous (X changes twice)" % (where, g))
            return encode(LOAD, G=G, O=O, addr=v)
        if mn == "STORE":
            need(2); r = a[1].upper()
            if r not in REGS or r == "X": raise AsmError("%s: STORE source must be A, C, XL, XH, SP, RSP or F" % where)
            O, v, kind = self.operand(a[0], where, pc)
            if kind not in ("abs", "x", "xinc"):
                raise AsmError("%s: STORE target must be [addr], [X] or [X+]" % where)
            return encode(STORE, G=REGS[r], O=O, addr=v)
        if mn in ("PUSH", "POP"):
            need(1); r = a[0].upper()
            if r not in REGS or r == "X": raise AsmError("%s: %s takes A, C, XL, XH, SP, RSP or F (not whole X)" % (where, mn))
            if mn == "POP" and r in ("SP", "RSP"): raise AsmError("%s: POP %s is not allowed" % (where, r))
            return encode(PUSH if mn == "PUSH" else POP, G=REGS[r])
        if mn in ("JUMP", "CALL", "RET", "DJNZ"):
            cond = C_ALWAYS
            if mn == "DJNZ":
                need(1)
            elif mn == "RET":
                if len(a) > 1: raise AsmError("%s: RET [cond]" % where)
                if a: cond = self.cond(a[0], where)
            else:
                if len(a) == 2: cond = self.cond(a[0], where); a = a[1:]
                need(1)
            if mn == "RET": return encode(RET, S=cond)
            v = self.ev(a[0], where, pc)
            if not 0 <= v < 65536: raise AsmError("%s: target out of range" % where)
            return encode({"JUMP": JUMP, "CALL": CALL, "DJNZ": DJNZ}[mn], S=0 if mn == "DJNZ" else cond, addr=v)
        raise AsmError("%s: unknown instruction %s" % (where, mn))

    def cond(self, s, where):
        s = s.strip().upper()
        if s not in CONDS: raise AsmError("%s: unknown condition %s" % (where, s))
        return CONDS[s]


def assemble_file(path):
    return Assembler().assemble(open(path).read(), path)


def assemble_text(text, name="<src>"):
    return Assembler().assemble(text, name)


if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(__doc__)
    try:
        P = assemble_file(sys.argv[1])
    except AsmError as e:
        sys.exit("error: %s" % e)
    out = "\n".join(P.listing)
    if len(sys.argv) > 2: open(sys.argv[2], "w").write(out + "\n")
    else: print(out)
    print("; %d words, %d data bytes" % (len(P.words), sum(len(b) for _, b in P.data)), file=sys.stderr)
