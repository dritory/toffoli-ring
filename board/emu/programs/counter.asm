; Binary counter: a 16-bit counter is shown in row 0 (bit 15 on the left);
; every frame the older values scroll down one row, so the display is a
; waterfall of the count history. One frame = one loop; OUT = low count byte.
        .equ DISP, 0xE0
        .equ OUTP, 0xC0

        .data
cnt_l:  .byte 0
cnt_h:  .byte 0

        .text
        JMP main            ; 0: reset
        JMP main            ; 1: interrupt vector (unused, interrupts stay disabled)
main:
        LD B, 29            ; copy bytes 29..0 to +2 (row r -> r+1), bottom first
scroll: LD A, [B+DISP]
        ST [B+DISP+2], A
        SUB B, 1
        JC scroll           ; C=1 while B did not wrap below 0, so byte 0 is copied too
        LD A, [cnt_l]
        ADD A, 1
        ST [cnt_l], A
        JNC nocarry
        LD A, [cnt_h]
        ADD A, 1
        ST [cnt_h], A
nocarry:
        LD A, [cnt_h]
        ST [DISP], A
        LD A, [cnt_l]
        ST [DISP+1], A
        ST [OUTP], A        ; frame marker
        JMP main
