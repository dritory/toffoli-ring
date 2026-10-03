"""Python vs JS: hash of the full CPU state (pc,a,c,x,sp,rsp,z,c + every write) every cycle,
checked every `chunk` cycles, plus final memory / LCD / LED digests.
Usage: python3 tests/test_equiv.py [random_count] ; benchmark programs: equiv_program()."""
import sys, os, json, random, subprocess, tempfile, zlib
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import emu, isa

def py_run(spec):
    cpu = emu.CPU(spec["words"], [(a, bytes(b)) for a, b in spec["data"]], tick_cycles=spec["tick"], fast_tables=spec["fast"])
    cpu.wlog = []
    ev = spec.get("events", []); ei = 0; chunk = spec.get("chunk", 1000)
    h = 0x811C9DC5; out = []
    for _ in range(spec["cycles"]):
        while ei < len(ev) and ev[ei][0] <= cpu.cycle:
            cpu.set_buttons(ev[ei][1]); ei += 1
        cpu.step()
        for v in cpu.state(): h = ((h ^ v) * 16777619) & 0xFFFFFFFF
        for a, v in cpu.wlog:
            h = ((h ^ a) * 16777619) & 0xFFFFFFFF; h = ((h ^ v) * 16777619) & 0xFFFFFFFF
        cpu.wlog.clear()
        if cpu.cycle % chunk == 0: out.append("H %d %d" % (cpu.cycle, h))
    lb = b"".join(p.to_bytes(2, "big") for p in cpu.lcd.fb)
    out.append("F " + " ".join(map(str, [cpu.cycle, h, zlib.crc32(bytes(cpu.mem)), zlib.crc32(lb), cpu.led, cpu.pc, cpu.a, cpu.x])))
    return out

def js_run(spec):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(spec, f); name = f.name
    try:
        r = subprocess.run(["node", os.path.join(ROOT, "runjs.js"), name], capture_output=True, text=True, check=True)
    finally:
        os.unlink(name)
    return r.stdout.strip().split("\n")

def compare(spec, label=""):
    a, b = py_run(spec), js_run(spec)
    if a == b: return True
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            print("MISMATCH", label, "first differing summary line", i, x, "|", y); break
    return False

def random_spec(rng):
    n = rng.randint(20, 300); words = []
    for _ in range(n):
        op = rng.randrange(16)
        addr = rng.choice([rng.randrange(n), rng.randrange(0x200, 0x240), rng.randrange(256), 0xFF00 + rng.choice([0, 1, 2, 3, 4, 0x10, 0x11, 0x20, 0x30, 0x31, 0x32, 0x33])])
        if op in (isa.JUMP, isa.CALL, isa.DJNZ): addr = rng.randrange(n)
        w = isa.encode(op, R=rng.randrange(2), S=rng.randrange(8), K=int(rng.random() < .8), G=rng.randrange(8),
                       Y=rng.randrange(2), O=rng.choice([0, 1, 2, 3, 4, 5, 6, 7, 0, 1]), addr=addr)
        words.append(w)
    words[1] = isa.encode(isa.LOAD, G=isa.R_X, O=0, addr=0x200)
    if rng.random() < .7 and n > 5:
        words[2] = isa.encode(isa.LOAD, G=0, O=0, addr=rng.randrange(1, 16))
        words[3] = isa.encode(isa.STORE, G=0, O=1, addr=isa.IRQ_EN)
    ev, c = [], 0
    for _ in range(rng.randrange(8)):
        c += rng.randrange(1, 3000); ev.append([c, rng.randrange(16)])
    return dict(words=words, data=[[0x200, [rng.randrange(256) for _ in range(64)]]], cycles=20000,
                tick=rng.choice([1, 7, 1000]), fast=rng.random() < .5, events=ev, chunk=250)

def equiv_program(words, data, cycles, events=(), tick=1, fast=True, label=""):
    spec = dict(words=list(words), data=[[a, list(b)] for a, b in data], cycles=cycles, tick=tick,
                fast=fast, events=[list(e) for e in events], chunk=5000)
    return compare(spec, label)

def check_constants():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(dict(consts=1), f); name = f.name
    k = json.loads(subprocess.run(["node", os.path.join(ROOT, "runjs.js"), name], capture_output=True, text=True, check=True).stdout)
    os.unlink(name)
    for key, val in k.items():
        assert getattr(isa, key) == val, (key, getattr(isa, key), val)
    print("memory-map constants: %d identical in isa.py and emu.js" % len(k))

if __name__ == "__main__":
    check_constants()
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    rng = random.Random(12345); bad = 0
    for i in range(n):
        if not compare(random_spec(rng), "random#%d" % i): bad += 1
    print("random programs: %d/%d identical" % (n - bad, n))
    sys.exit(1 if bad else 0)
