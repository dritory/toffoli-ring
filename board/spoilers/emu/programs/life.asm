; Conway's Game of Life on the 16x16 display, wrapping at all edges.
; Bit-sliced: every AND/OR/XOR works on 8 cells at once. Row r is display bytes
; 0xE0+2r (left half, bit7 = column 0) and 0xE0+2r+1 (right half).
;
; Phase 1: copy the 16 rows into M[] and build the west (W[]) and east (E[]) neighbour
;          planes with 16-bit rotates through carry; each array has one halo row above and below.
; Phase 2: for each of the 32 display bytes add the 8 neighbour planes with a tree of full
;          adders (bitwise), then new = (weight-2 count == 1) & (weight-1 bit | alive),
;          written straight to the display (the arrays keep the old generation).
        .equ DISP, 0xE0
        .equ OUTP, 0xC0
        .equ X, 0x10
        .equ Y, 0x11
        .equ S1, 0x12
        .equ C1, 0x13
        .equ S2, 0x14
        .equ C2, 0x15
        .equ S3, 0x16
        .equ C3, 0x17
        .equ BIT0, 0x18
        .equ K, 0x19
        .equ T1, 0x1A
        .equ T2, 0x1B
        .equ GEN, 0x1C
        .equ MARR, 0x20         ; 18 rows x 2 bytes (row index = display row + 1)
        .equ WARR, 0x44
        .equ EARR, 0x68
        .equ PAT, 0x90          ; initial pattern (data image), copied to the display

; full adder: s = p^q^r, c = majority(p,q,r); uses X, Y
.macro FA p, q, r, s, c
        LD A, \p
        XOR A, \q
        ST [X], A
        XOR A, \r
        ST [\s], A
        LD A, [X]
        AND A, \r
        ST [Y], A
        LD A, \p
        AND A, \q
        OR A, [Y]
        ST [\c], A
.endm

; copy the two halo rows of an array: row0 <- row16, row17 <- row1
.macro HALO base
        LD A, [\base+32]
        ST [\base], A
        LD A, [\base+33]
        ST [\base+1], A
        LD A, [\base+2]
        ST [\base+34], A
        LD A, [\base+3]
        ST [\base+35], A
.endm

        .data
        .org PAT
        .byte 0x40,0x00, 0x20,0x00, 0xE0,0x00, 0x00,0x00     ; rows 0-3: glider
        .byte 0x00,0x00, 0x00,0x00, 0x00,0x00, 0x00,0x00     ; rows 4-7
        .byte 0x00,0x00, 0x00,0x30, 0x00,0x60, 0x00,0x20     ; rows 8-11: R-pentomino
        .byte 0x00,0x00, 0x00,0x00, 0x00,0x00, 0x00,0x00     ; rows 12-15
        .text
        JMP main
        JMP main
main:   LD B, 31                ; pattern -> display
init:   LD A, [B+PAT]
        ST [B+DISP], A
        SUB B, 1
        JC init
gen:
        LD B, 30                ; ---- phase 1 (rows counted downwards)
p1:     LD A, [B+DISP]          ; left half
        ST [B+MARR+2], A
        LD A, [B+DISP+1]        ; right half
        ST [B+MARR+3], A
        ROR A                   ; C = bit 0 of the right half (wraps to bit 15)
        LD A, [B+DISP]
        ROR A
        ST [B+WARR+2], A
        LD A, [B+DISP+1]
        ROR A
        ST [B+WARR+3], A
        LD A, [B+DISP]
        ROL A                   ; C = bit 7 of the left half (wraps to bit 0)
        LD A, [B+DISP+1]
        ROL A
        ST [B+EARR+3], A
        LD A, [B+DISP]
        ROL A
        ST [B+EARR+2], A
        SUB B, 2
        JC p1
        HALO MARR
        HALO WARR
        HALO EARR
        LD B, 31                ; ---- phase 2 (bytes counted downwards)
p2:     FA [B+WARR], [B+MARR], [B+EARR], S1, C1         ; row above
        FA [B+WARR+2], [B+EARR+2], [B+WARR+4], S2, C2   ; west, east, south-west
        LD A, [B+MARR+4]                                ; south, south-east: half adder
        XOR A, [B+EARR+4]
        ST [S3], A
        LD A, [B+MARR+4]
        AND A, [B+EARR+4]
        ST [C3], A
        FA [S1], [S2], [S3], BIT0, K                    ; weight-1 column
        LD A, [C1]                                      ; weight-2 column: c1+c2+c3+k == 1 ?
        XOR A, [C2]
        ST [T1], A
        LD A, [C1]
        AND A, [C2]
        ST [T2], A
        LD A, [C3]
        XOR A, [K]
        ST [Y], A
        LD A, [C3]
        AND A, [K]
        OR A, [T2]
        XOR A, 0xFF
        ST [T2], A              ; T2 = not (two pairs)
        LD A, [T1]
        XOR A, [Y]
        AND A, [T2]
        ST [T1], A              ; T1 = exactly one carry
        LD A, [BIT0]
        OR A, [B+MARR+2]        ; count odd, or alive
        AND A, [T1]
        ST [B+DISP], A
        SUB B, 1
        JC p2
        LD A, [GEN]             ; generation counter on the OUT port = frame marker
        ADD A, 1
        ST [GEN], A
        ST [OUTP], A
        JMP gen
