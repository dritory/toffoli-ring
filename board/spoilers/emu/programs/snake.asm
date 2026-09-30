; Snake on a 16x16 torus. Four buttons steer through the interrupt: the handler only
; records the requested direction, the main loop moves one cell per frame.
; Position is packed yyyyxxxx, so the display byte is 0xE0 + (pos >> 3)
; and the pixel mask is 0x80 >> (pos & 7). The body is a 64-entry ring buffer of positions.
; Button 0 = up, 1 = down, 2 = left, 3 = right. Maximum snake length 63.
        .equ DISP, 0xE0
        .equ OUTP, 0xC0
        .equ PEND, 0xC1
        .equ IEP,  0xC2
        .equ DIR,  0x00
        .equ ND,   0x01
        .equ HEAD, 0x02
        .equ FOOD, 0x03
        .equ HIDX, 0x04
        .equ TIDX, 0x05
        .equ MASK, 0x06
        .equ T,    0x07
        .equ RND,  0x08
        .equ SVA,  0x09
        .equ TP,   0x0A
        .equ NEWH, 0x0B
        .equ TPOS, 0x0C
        .equ LEN,  0x0D
        .equ MASKTAB, 0x10      ; 8 bytes: 0x80 >> i
        .equ DELTA, 0x18        ; per direction: -16, +16, -1, +1
        .equ KEEP,  0x1C        ; bits taken from the new position (rows keep their row when moving sideways)
        .equ RING, 0x40

; B = display byte offset of pixel \p, MASK = its bit mask
.macro PIXADDR p
        LD A, [\p]
        AND A, 7
        LD B, A
        LD A, [B+MASKTAB]
        ST [MASK], A
        LD A, [\p]
        AND A, 0xF8
        ADD A, 0                ; clear carry, then pos>>3 (the low 3 bits are already zero)
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
.macro TESTPIX                  ; Z=1 if the pixel is off
        LD A, [B+DISP]
        AND A, [MASK]
.endm

        .data
        .org RND
        .byte 0xA5
        .org MASKTAB
        .byte 0x80,0x40,0x20,0x10,0x08,0x04,0x02,0x01
        .byte 0xF0,0x10,0xFF,0x01           ; DELTA
        .byte 0xFF,0xFF,0x0F,0x0F           ; KEEP
        .text
        JMP main
        JMP isr
main:   LD A, 0                 ; clear display
        LD B, 31
clr:    ST [B+DISP], A
        SUB B, 1
        JC clr
        LD A, 3
        ST [DIR], A
        ST [ND], A
        LD A, 5
        ST [LEN], A
        ST [HIDX], A
        LD A, 0
        ST [TIDX], A
        LD A, 131               ; snake: row 8, columns 3..7, heading right
        ST [RING], A
        LD A, 132
        ST [RING+1], A
        LD A, 133
        ST [RING+2], A
        LD A, 134
        ST [RING+3], A
        LD A, 135
        ST [RING+4], A
        ST [HEAD], A
        LD A, 140               ; food at row 8, column 12
        ST [FOOD], A
        PIXADDR RING
        SETPIX
        PIXADDR RING+1
        SETPIX
        PIXADDR RING+2
        SETPIX
        PIXADDR RING+3
        SETPIX
        PIXADDR RING+4
        SETPIX
        PIXADDR FOOD
        SETPIX
        LD A, 0x0F              ; drop stale button requests, enable the interrupt
        ST [PEND], A
        LD A, 1
        ST [IEP], A

tick:   LD A, [ND]              ; ---- one frame
        XOR A, [DIR]
        SUB A, 1                ; requested direction is the opposite of the current one?
        JZ keep
        LD A, [ND]
        ST [DIR], A
keep:   LD B, [DIR]
        LD A, [HEAD]
        ADD A, [B+DELTA]
        AND A, [B+KEEP]
        ST [T], A
        LD A, [B+KEEP]
        XOR A, 0xFF
        AND A, [HEAD]
        OR A, [T]
        ST [NEWH], A            ; new head position
        SUB A, [FOOD]
        JZ eat
        LD B, [TIDX]            ; no food: erase the tail
        LD A, [B+RING]
        ST [TPOS], A
        LD A, [TIDX]
        ADD A, 1
        AND A, 63
        ST [TIDX], A
        PIXADDR TPOS
        CLRPIX
        PIXADDR NEWH            ; bumped into the body?
        TESTPIX
        JNZ dead
        SETPIX
        JMP push
eat:    LD A, [LEN]             ; grow: keep the tail, pick a new food cell with an 8-bit LFSR
        ADD A, 1
        ST [LEN], A
nf:     LD A, [RND]
        ADD A, 0
        ROR A
        JNC nf1
        XOR A, 0xB8
nf1:    ST [RND], A
        ST [FOOD], A
        PIXADDR FOOD
        TESTPIX
        JNZ nf                  ; occupied, try the next value
        SETPIX
push:   LD B, [HIDX]            ; append the new head to the ring
        LD A, [NEWH]
        ST [B+RING], A
        ST [HEAD], A
        LD A, [HIDX]
        ADD A, 1
        AND A, 63
        ST [HIDX], A
        LD A, [LEN]
        ST [OUTP], A            ; frame marker: length on the output LEDs
        JMP tick

dead:   LD B, 31                ; flash the whole display once, then restart
fl:     LD A, [B+DISP]
        XOR A, 0xFF
        ST [B+DISP], A
        SUB B, 1
        JC fl
        JMP main

isr:    ST [SVA], A             ; A and B are not saved by hardware; this handler never touches B
        LD A, [PEND]
        ST [PEND], A            ; acknowledge the requests seen
        ST [TP], A
        AND A, 1
        JZ i1
        LD A, 0
        ST [ND], A
i1:     LD A, [TP]
        AND A, 2
        JZ i2
        LD A, 1
        ST [ND], A
i2:     LD A, [TP]
        AND A, 4
        JZ i3
        LD A, 2
        ST [ND], A
i3:     LD A, [TP]
        AND A, 8
        JZ i4
        LD A, 3
        ST [ND], A
i4:     LD A, [SVA]
        RETI
