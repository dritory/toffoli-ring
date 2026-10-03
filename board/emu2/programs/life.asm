; Conway's Game of Life on a 40 x 30 field (dead border), 8 x 8 pixel cells on the LCD.
; One byte per cell; row y of a buffer is page (base + y), the column is the low address byte,
; so a 3-cell row sum is LOAD A,[X+] / ADD [X+] / ADD [X+].  Two buffers: pages 0x20..0x3F and 0x40..0x5F.
; Only cells that change are redrawn.  LED port: generation counter.
.include "lib/lcd.inc"
WHITE = 0xFFFF
.data
cx:     .byte 0
cy:     .byte 0
sq:     .byte 0
cur:    .byte 0x20              ; base page of the current buffer
y:      .byte 0
xm1:    .byte 0                 ; column - 1 (cells are columns 1..40)
ra:     .byte 0                 ; pages of rows y-1, y, y+1
rb:     .byte 0
rc:     .byte 0
s:      .byte 0
old:    .byte 0
new:    .byte 0
gen:    .byte 0
t:      .byte 0
.org 0x0300
; initial live cells as (column, row) pairs, column 0 ends the list
seed:   .byte 3,2, 4,3, 2,4, 3,4, 4,4                  ; glider
        .byte 21,15, 22,15, 20,16, 21,16, 21,17        ; R-pentomino
        .byte 33,5, 34,5, 35,5                         ; blinker
        .byte 0
.org 0x2000
buf0:   .space 0x2000
.org 0x4000
buf1:   .space 0x2000
.code
        JUMP start
        RETI
start:  CALL init_tables
sd:     LOAD XH, #hi(seed)
        LOAD XL, [sq]
        LOAD A, [X+]
        STORE [cx], A
        TEST #255
        JUMP Z, run
        LOAD A, [X+]
        STORE [cy], A
        STORE [sq], XL
        ADD #0x20               ; page of row cy in buffer 0
        MOVE XH, A
        LOAD XL, [cx]
        LOAD A, #1
        STORE [X], A
        LOAD A, [cx]
        SUB #1
        STORE [xm1], A
        LOAD A, [cy]
        STORE [y], A
        LOAD X, #WHITE
        CALL draw_cell
        JUMP sd

run:
frame:  LOAD A, [FRAME]
        TEST #1
        JUMP Z, frame
        LOAD A, #1
        STORE [y], A
row:    LOAD A, [cur]
        ADD [y]
        STORE [rb], A
        SUB #1
        STORE [ra], A
        ADD #2
        STORE [rc], A
        LOAD A, #0
        STORE [xm1], A
col:    LOAD XH, [ra]           ; 3 x 3 sum, centre included
        LOAD XL, [xm1]
        LOAD A, [X+]
        ADD [X+]
        ADD [X+]
        LOAD XH, [rc]
        LOAD XL, [xm1]
        ADD [X+]
        ADD [X+]
        ADD [X+]
        LOAD XH, [rb]
        LOAD XL, [xm1]
        ADD [X+]
        ADD [X+]
        ADD [X+]
        STORE [s], A
        LOAD XL, [xm1]
        LOAD A, [X+]
        LOAD A, [X]             ; the cell itself
        STORE [old], A
        LOAD A, [s]
        CMP #3
        JUMP Z, born
        CMP #4
        JUMP NZ, die
        LOAD A, [old]           ; sum 4: keeps its state
        JUMP wr
born:   LOAD A, #1
        JUMP wr
die:    LOAD A, #0
wr:     STORE [new], A
        LOAD A, [rb]
        XOR #0x60               ; same row in the other buffer
        MOVE XH, A
        LOAD XL, [xm1]
        LOAD A, [X+]
        LOAD A, [new]
        STORE [X], A
        XOR [old]
        JUMP Z, same
        LOAD A, [new]
        TEST #255
        LOAD X, #WHITE
        JUMP NZ, dr
        LOAD X, #0
dr:     CALL draw_cell
same:   LOAD A, [xm1]
        ADD #1
        STORE [xm1], A
        CMP #40
        JUMP NZ, col
        LOAD A, [y]
        ADD #1
        STORE [y], A
        CMP #31
        JUMP NZ, row
        LOAD A, [cur]
        XOR #0x60
        STORE [cur], A
        LOAD A, [gen]
        ADD #1
        STORE [gen], A
        STORE [LED], A
        JUMP frame

draw_cell:                      ; X = colour; cell column [xm1], row [y] - 1
        LCDCMD 0x2A
        LOAD A, [xm1]
        MULH #8
        STORE [LCD_DATA], A
        LOAD A, [xm1]
        MUL #8
        STORE [LCD_DATA], A
        LOAD A, [xm1]
        MULH #8
        STORE [LCD_DATA], A
        LOAD A, [xm1]
        MUL #8
        ADD #7
        STORE [LCD_DATA], A
        LCDCMD 0x2B
        LCDBYTE 0
        LOAD A, [y]
        SUB #1
        MUL #8
        STORE [t], A
        STORE [LCD_DATA], A
        LCDBYTE 0
        LOAD A, [t]
        ADD #7
        STORE [LCD_DATA], A
        LCDCMD 0x2C
        LOAD C, #64
px:     STORE [LCD_DATA], XH
        STORE [LCD_DATA], XL
        DJNZ px
        RET
.include "lib/init_tables.inc"
