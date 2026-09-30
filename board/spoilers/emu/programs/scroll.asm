; Scrolling text. The message (capital letters and spaces) is in data RAM; a 5x7 column font for
; A-Z is in the data image (5 bytes per letter, bit 0 = top row, drawn on display rows 4-10).
; Each frame the picture moves one pixel to the left; the new right-hand column comes from the
; font (or a blank gap column after every letter). Rows are shifted with rotate-through-carry:
; the carry carries the pixel that moves from the right half to the left half.
        .equ DISP, 0xE0
        .equ OUTP, 0xC0
        .equ CP,   0x00         ; index of the current character
        .equ CC,   0x01         ; column within the character (5 = gap)
        .equ COLB, 0x02         ; bits of the column being shifted in
        .equ T,    0x03
        .equ T2,   0x04
        .equ TEXT, 0x10
        .equ FONT, 0x38

.macro ROWG r                   ; row that receives a font bit
        LD A, [COLB]
        ROR A                   ; C = next font bit (top first)
        ST [COLB], A
        LD A, [DISP+2*\r+1]
        ROL A                   ; new bit in at column 15, column 8 out in C
        ST [DISP+2*\r+1], A
        LD A, [DISP+2*\r]
        ROL A
        ST [DISP+2*\r], A
.endm
.macro ROWP r                   ; row that receives a blank
        LD A, [DISP+2*\r+1]
        ADD A, 0                ; clear carry
        ROL A
        ST [DISP+2*\r+1], A
        LD A, [DISP+2*\r]
        ROL A
        ST [DISP+2*\r], A
.endm

        .data
        .org TEXT
        .ascii "HELLO TOFFOLI RING "
        .byte 0
        .org FONT
        .byte 0x7E,0x11,0x11,0x11,0x7E     ; A
        .byte 0x7F,0x49,0x49,0x49,0x36     ; B
        .byte 0x3E,0x41,0x41,0x41,0x22     ; C
        .byte 0x7F,0x41,0x41,0x22,0x1C     ; D
        .byte 0x7F,0x49,0x49,0x49,0x41     ; E
        .byte 0x7F,0x09,0x09,0x09,0x01     ; F
        .byte 0x3E,0x41,0x49,0x49,0x7A     ; G
        .byte 0x7F,0x08,0x08,0x08,0x7F     ; H
        .byte 0x00,0x41,0x7F,0x41,0x00     ; I
        .byte 0x20,0x40,0x41,0x3F,0x01     ; J
        .byte 0x7F,0x08,0x14,0x22,0x41     ; K
        .byte 0x7F,0x40,0x40,0x40,0x40     ; L
        .byte 0x7F,0x02,0x0C,0x02,0x7F     ; M
        .byte 0x7F,0x04,0x08,0x10,0x7F     ; N
        .byte 0x3E,0x41,0x41,0x41,0x3E     ; O
        .byte 0x7F,0x09,0x09,0x09,0x06     ; P
        .byte 0x3E,0x41,0x51,0x21,0x5E     ; Q
        .byte 0x7F,0x09,0x19,0x29,0x46     ; R
        .byte 0x46,0x49,0x49,0x49,0x31     ; S
        .byte 0x01,0x01,0x7F,0x01,0x01     ; T
        .byte 0x3F,0x40,0x40,0x40,0x3F     ; U
        .byte 0x1F,0x20,0x40,0x20,0x1F     ; V
        .byte 0x3F,0x40,0x38,0x40,0x3F     ; W
        .byte 0x63,0x14,0x08,0x14,0x63     ; X
        .byte 0x07,0x08,0x70,0x08,0x07     ; Y
        .byte 0x61,0x51,0x49,0x45,0x43     ; Z
        .text
        JMP main
        JMP main
main:   LD A, 0
        ST [CP], A
        ST [CC], A
frame:  LD A, [CC]              ; ---- fetch the next column
        ST [T], A
        SUB A, 5
        JZ gap
        LD B, [CP]
        LD A, [B+TEXT]
        SUB A, ' '
        JZ gap
        SUB A, 'A'-' '
        ST [T2], A
        ADD A, 0                ; clear carry, then A*4 (A < 32 so nothing shifts out)
        ROL A
        ROL A
        ADD A, [T2]             ; * 5
        ADD A, [T]              ; + column
        LD B, A
        LD A, [B+FONT]
        JMP got
gap:    LD A, 0
got:    ST [COLB], A
        ROWP 0                  ; ---- shift the 16 rows
        ROWP 1
        ROWP 2
        ROWP 3
        ROWG 4
        ROWG 5
        ROWG 6
        ROWG 7
        ROWG 8
        ROWG 9
        ROWG 10
        ROWP 11
        ROWP 12
        ROWP 13
        ROWP 14
        ROWP 15
        LD A, [CC]              ; ---- advance
        ADD A, 1
        ST [CC], A
        SUB A, 6
        JNZ done
        LD A, 0
        ST [CC], A
        LD A, [CP]
        ADD A, 1
        ST [CP], A
        LD B, A
        LD A, [B+TEXT]
        JNZ done
        ST [CP], A              ; end of text (A = 0): wrap around
done:   LD A, [CP]
        ST [OUTP], A            ; frame marker
        JMP frame
