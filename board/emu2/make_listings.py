"""Assemble every program and write listings/<name>.lst (hex digit groups: opcode|restore+select|keep+reg|carry+source|address)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import asm
os.makedirs(os.path.join(HERE, "listings"), exist_ok=True)
for name in ("counter", "snake", "pong", "life", "scroll", "raycast"):
    P = asm.assemble_file(os.path.join(HERE, "programs", name + ".asm"))
    hdr = "; %s: %d words, %d data bytes\n; word | opcode|restore+select|keep+reg|carry+source|address | source\n" % (name, len(P.words), sum(len(b) for _, b in P.data))
    open(os.path.join(HERE, "listings", name + ".lst"), "w").write(hdr + "\n".join(P.listing) + "\n")
    print("listings/%s.lst  %d words" % (name, len(P.words)))
sys.path.insert(0, os.path.join(HERE, "programs"))
import bf
src = open(os.path.join(HERE, "programs", "hello.bf")).read()
P = asm.assemble_text(bf.compile_bf(src), "hello.bf")
open(os.path.join(HERE, "listings", "hello_bf.lst"), "w").write("\n".join(P.listing) + "\n")
open(os.path.join(HERE, "listings", "hello_bf.asm"), "w").write(bf.compile_bf(src))
print("listings/hello_bf.lst  %d words" % len(P.words))
