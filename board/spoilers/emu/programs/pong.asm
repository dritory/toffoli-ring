; Pong on the 16x16 display. Left paddle (column 0): button 0 = up, 1 = down, read from the
; input port (hold to move). The right paddle is a slow computer player that moves at most every
; second frame. The ball moves one cell per frame in x and y. OUT = score, left in the
; high nibble, right in the low nibble. No interrupts.
; Ball position is packed yyyyxxxx; VX = +1/-1, VY = +16/-16, so a move is BP += VX + VY.
        .equ DISP, 0xE0
        .equ OUTP, 0xC0
        .equ BTN,  0xC0
        .equ BP,   0x00
        .equ VX,   0x01
        .equ VY,   0x02
        .equ PL,   0x03         ; paddle top row * 16
        .equ PR,   0x04
        .equ MASK, 0x05
        .equ T,    0x06
        .equ FR,   0x07
        .equ SC,   0x08
        .equ T2,   0x09
        .equ MASKTAB, 0x10

.macro PIXADDR p
        LD A, [\p]
        AND A, 7
        LD B, A
        LD A, [B+MASKTAB]
        ST [MASK], A
        LD A, [\p]
        AND A, 0xF8
        ADD A, 0
        ROR A
        ROR A
        ROR A
        LD B, A
.endm
.macro SETPIX
        LD A, [B+DISP]
        OR A, [MASK]
        ST [B+DISP], A
.endm
.macro CLRPIX
        LD A, [B+DISP]
        OR A, [MASK]
        XOR A, [MASK]
        ST [B+DISP], A
.endm

; paddle of 4 pixels: var = top*16, half = 0 (left column) / 1 (right column)
.macro PAD var, half, op, imm
        LD A, [\var]
        ADD A, 0
        ROR A
        ROR A
        ROR A
        LD B, A
        LD A, [B+DISP+\half]
        \op A, \imm
        ST [B+DISP+\half], A
        LD A, [B+DISP+\half+2]
        \op A, \imm
        ST [B+DISP+\half+2], A
        LD A, [B+DISP+\half+4]
        \op A, \imm
        ST [B+DISP+\half+4], A
        LD A, [B+DISP+\half+6]
        \op A, \imm
        ST [B+DISP+\half+6], A
.endm
.macro DRAWL
        PAD PL, 0, OR, 0x80
.endm
.macro ERASEL
        PAD PL, 0, AND, 0x7F
.endm
.macro DRAWR
        PAD PR, 1, OR, 0x01
.endm
.macro ERASER
        PAD PR, 1, AND, 0xFE
.endm
; ball row inside the paddle (4 rows)? falls through on a hit, jumps to `miss` otherwise
.macro HIT pv, miss
        LD A, [BP]
        AND A, 0xF0
        SUB A, [\pv]
        JNC \miss
        SUB A, 64
        JC \miss
.endm

        .data
        .org MASKTAB
        .byte 0x80,0x40,0x20,0x10,0x08,0x04,0x02,0x01
        .text
        JMP main
        JMP main
main:   LD A, 0
        LD B, 31
clr:    ST [B+DISP], A
        SUB B, 1
        JC clr
        LD A, 80                ; both paddles start at rows 5-8
        ST [PL], A
        ST [PR], A
        LD A, 0x78              ; ball at row 7, column 8, heading right and down
        ST [BP], A
        LD A, 1
        ST [VX], A
        LD A, 16
        ST [VY], A
        LD A, 0
        ST [SC], A
        ST [FR], A
        DRAWL
        DRAWR
tick:   LD A, [BTN]             ; ---- left paddle
        AND A, 1
        JZ lnu
        LD A, [PL]
        JZ ldone                ; already at the top
        ERASEL
        LD A, [PL]
        SUB A, 16
        ST [PL], A
        DRAWL
        JMP ldone
lnu:    LD A, [BTN]
        AND A, 2
        JZ ldone
        LD A, [PL]
        SUB A, 192
        JC ldone                ; already at the bottom
        ERASEL
        LD A, [PL]
        ADD A, 16
        ST [PL], A
        DRAWL
ldone:  LD A, [FR]              ; ---- right paddle (computer), every second frame
        AND A, 1
        JZ rdone
        LD A, [BP]
        AND A, 0xF0
        ST [T], A               ; ball row * 16
        LD A, [PR]
        ADD A, 16
        ST [T2], A
        LD A, [T]
        SUB A, [T2]
        JC rnu                  ; ball not above the paddle's second row
        LD A, [PR]
        JZ rdone
        ERASER
        LD A, [PR]
        SUB A, 16
        ST [PR], A
        DRAWR
        JMP rdone
rnu:    LD A, [PR]
        ADD A, 32
        ST [T2], A
        LD A, [T]
        SUB A, [T2]
        JNC rdone               ; ball not below the paddle's third row
        LD A, [PR]
        SUB A, 192
        JC rdone
        ERASER
        LD A, [PR]
        ADD A, 16
        ST [PR], A
        DRAWR
rdone:  PIXADDR BP              ; ---- ball: erase
        CLRPIX
        LD A, [BP]              ; bounce off the top and bottom rows
        SUB A, 16
        JC nottop
        LD A, 16
        ST [VY], A
        JMP vdone
nottop: SUB A, 224              ; A = BP-16, so BP >= 240 is A >= 224
        JNC vdone
        LD A, 240
        ST [VY], A
vdone:  LD A, [BP]              ; walls / paddles
        AND A, 15
        JZ lostl
        XOR A, 15               ; equality tests chained with XOR: A = bx ^ 15
        JZ lostr
        XOR A, 14               ; A = bx ^ 1
        JNZ h14
        LD A, [VX]
        SUB A, 1
        JZ move
        HIT PL, move
        LD A, 1
        ST [VX], A
        JMP move
h14:    XOR A, 15               ; A = bx ^ 14
        JNZ move
        LD A, [VX]
        SUB A, 1
        JNZ move
        HIT PR, move
        LD A, 255
        ST [VX], A
move:   LD A, [BP]
        ADD A, [VX]
        ADD A, [VY]
        ST [BP], A
draw:   PIXADDR BP
        SETPIX
        LD A, [FR]
        ADD A, 1
        ST [FR], A
        LD A, [SC]
        ST [OUTP], A            ; frame marker: score
        JMP tick
lostl:  LD A, [SC]              ; ball reached column 0: right side scores
        ADD A, 1
        ST [SC], A
        DRAWL                   ; repair the paddle pixel the erase may have cleared
        JMP serve
lostr:  LD A, [SC]
        ADD A, 16
        ST [SC], A
        DRAWR
serve:  LD A, 0x78
        ST [BP], A
        JMP draw
