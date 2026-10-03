; Raycaster demake: 160 x 100 view (16 x 16 map, flat-coloured walls) on the LCD, DDA per column.
; Angles: 1024 per turn (16-bit, high byte 0..3).  Positions: 16-bit, high byte = map cell, low byte = 1/256 cell.
; Distances along the ray: 16 bit, 1/256 cell.  All trigonometry and reciprocals are ordinary data tables
; (see rc_data.py); LOOKUP MUL / MULH do the 8 x 8 products (side distances, fish-eye fix, shifts by 4).
; Buttons (polled each frame): UP walk, DOWN walk back, LEFT / RIGHT turn.
.include "lib/lcd.inc"
CEIL = 0x2965
FLOOR = 0x4A69
BARC = 0x4208
VX0 = 80                        ; view origin on the 320 x 240 screen
VY0 = 12
TURN = 6                        ; angle units per frame while a turn button is held
.data
pxl:    .byte 0
pxh:    .byte 0
pyl:    .byte 0
pyh:    .byte 0
pal:    .byte 0
pah:    .byte 0
col:    .byte 0
cal:    .byte 0
cah:    .byte 0
cosv:   .byte 0
vdxl:   .byte 0
vdxh:   .byte 0
vdyl:   .byte 0
vdyh:   .byte 0
vstx:   .byte 0
vsty:   .byte 0
sdxl:   .byte 0
sdxh:   .byte 0
sdyl:   .byte 0
sdyh:   .byte 0
idx:    .byte 0
side:   .byte 0
hv:     .byte 0
ax:     .byte 0
t1:     .byte 0
t2:     .byte 0
d8:     .byte 0
hh:     .byte 0
rem:    .byte 0
top:    .byte 0
btn:    .byte 0
mx:     .byte 0
my:     .byte 0
npl:    .byte 0
nph:    .byte 0
idx0:   .byte 0
bx:     .byte 0
.include "lib/raycast_tables.inc"
.code
        JUMP start
        RETI
start:  CALL init_tables
        LOAD A, #0x80           ; start at cell (2,2) centre, facing +x
        STORE [pxl], A
        STORE [pyl], A
        LOAD A, #2
        STORE [pxh], A
        STORE [pyh], A
        CALL status_bar
        LCDCMD 0x36             ; MADCTL: the view is streamed column by column
        LCDBYTE 0x20
frame:  LOAD A, [FRAME]
        TEST #1
        JUMP Z, frame
        CALL input
        CALL render
        JUMP frame

; ---- buttons: turn, walk with per-axis wall collision ----
input:  LOAD A, [BTN]
        STORE [btn], A
        TEST #4
        JUMP Z, in_r
        LOAD A, [pal]           ; turn left
        SUB #TURN
        STORE [pal], A
        LOAD A, [pah]
        SBC #0
        AND #3
        STORE [pah], A
in_r:   LOAD A, [btn]
        TEST #8
        JUMP Z, in_w
        LOAD A, [pal]           ; turn right
        ADD #TURN
        STORE [pal], A
        LOAD A, [pah]
        ADC #0
        AND #3
        STORE [pah], A
in_w:   LOAD A, [btn]
        TEST #1
        JUMP NZ, fwd
        TEST #2
        RET Z
        LOAD A, [pah]           ; walk back = walk along angle + half a turn
        ADD #2
        AND #3
        JUMP walk
fwd:    LOAD A, [pah]
walk:   STORE [t1], A           ; angle high byte
        LOAD XL, [pal]
        LOAD A, [t1]
        ADD #hi(mvx)
        MOVE XH, A
        LOAD A, [X]
        STORE [mx], A
        LOAD A, [t1]
        ADD #hi(mvy)
        MOVE XH, A
        LOAD A, [X]
        STORE [my], A
        LOAD A, [mx]            ; x: 16-bit add of a signed byte
        ADD [pxl]
        STORE [npl], A
        LOAD A, [mx]
        TEST #0x80              ; sign (flags: Z only, the carry survives)
        LOAD A, #0
        JUMP Z, xs
        LOAD A, #0xFF
xs:     ADC [pxh]
        STORE [nph], A
        LOAD A, [pyh]           ; map cell (pyh, nph)
        MUL #16
        OR [nph]
        MOVE XL, A
        LOAD XH, #hi(map)
        LOAD A, [X]
        TEST #255
        JUMP NZ, ytry
        LOAD A, [npl]
        STORE [pxl], A
        LOAD A, [nph]
        STORE [pxh], A
ytry:   LOAD A, [my]
        ADD [pyl]
        STORE [npl], A
        LOAD A, [my]
        TEST #0x80
        LOAD A, #0
        JUMP Z, ys
        LOAD A, #0xFF
ys:     ADC [pyh]
        STORE [nph], A
        MUL #16
        OR [pxh]
        MOVE XL, A
        LOAD XH, #hi(map)
        LOAD A, [X]
        TEST #255
        RET NZ
        LOAD A, [npl]
        STORE [pyl], A
        LOAD A, [nph]
        STORE [pyh], A
        RET

; ---- one table lookup by ray angle: var = table[cah * 256 + XL] ----
.macro TBL
        LOAD A, [cah]
        ADD #hi(\1)
        MOVE XH, A
        LOAD A, [X]
        STORE [\2], A
.endm
; ---- initial side distance: sd = (distance to the first grid line, 0..255) * dd / 256 ----
.macro SIDE
        LOAD A, [\2]
        TEST #0x80
        LOAD A, [\1]            ; fraction inside the cell
        JUMP NZ, sd\@           ; ray goes towards smaller coordinates: distance = fraction
        NOT                     ; else 255 - fraction
sd\@:   STORE [ax], A
        MUL [\3]
        STORE [t1], A
        LOAD A, [ax]
        MULH [\3]
        STORE [\5], A
        LOAD A, [ax]
        MULH [\4]
        ADD [t1]
        STORE [\6], A
        LOAD A, [\5]
        ADC #0
        STORE [\5], A
.endm

render: LCDCMD 0x2A             ; view window, then 16000 pixels column by column
        LCDBYTE 0
        LCDBYTE VX0
        LCDBYTE 0
        LCDBYTE (VX0 + 159)
        LCDCMD 0x2B
        LCDBYTE 0
        LCDBYTE VY0
        LCDBYTE 0
        LCDBYTE (VY0 + 99)
        LCDCMD 0x2C
        LOAD A, [pyh]
        MUL #16
        OR [pxh]
        STORE [idx0], A         ; map index of the player's cell
        LOAD A, #0
        STORE [col], A
cast:   LOAD XL, [col]          ; ray angle = player angle + column offset
        LOAD XH, #hi(offl)
        LOAD A, [X]
        ADD [pal]
        STORE [cal], A
        LOAD XH, #hi(offh)
        LOAD A, [X]
        ADC [pah]
        AND #3
        STORE [cah], A
        LOAD XH, #hi(coso)
        LOAD A, [X]
        STORE [cosv], A
        LOAD XL, [cal]
        TBL ddxl, vdxl
        TBL ddxh, vdxh
        TBL ddyl, vdyl
        TBL ddyh, vdyh
        TBL stx, vstx
        TBL sty, vsty
        SIDE pxl, vstx, vdxh, vdxl, sdxh, sdxl
        SIDE pyl, vsty, vdyh, vdyl, sdyh, sdyl
        LOAD A, [idx0]
        STORE [idx], A
dda:    LOAD A, [sdxh]          ; step along the axis whose next grid line is nearer
        CMP [sdyh]
        JUMP C, stepx
        JUMP NZ, stepy
        LOAD A, [sdxl]
        CMP [sdyl]
        JUMP NC, stepy
stepx:  LOAD A, [sdxl]
        ADD [vdxl]
        STORE [sdxl], A
        LOAD A, [sdxh]
        ADC [vdxh]
        STORE [sdxh], A
        LOAD A, [idx]
        ADD [vstx]
        STORE [idx], A
        MOVE XL, A
        LOAD XH, #hi(map)
        LOAD A, [X]
        TEST #255
        JUMP Z, dda
        STORE [hv], A
        LOAD A, [sdxl]          ; ray length = sd - dd
        SUB [vdxl]
        STORE [t1], A
        LOAD A, [sdxh]
        SBC [vdxh]
        STORE [t2], A
        LOAD A, #0
        STORE [side], A
        JUMP hit
stepy:  LOAD A, [sdyl]
        ADD [vdyl]
        STORE [sdyl], A
        LOAD A, [sdyh]
        ADC [vdyh]
        STORE [sdyh], A
        LOAD A, [idx]
        ADD [vsty]
        STORE [idx], A
        MOVE XL, A
        LOAD XH, #hi(map)
        LOAD A, [X]
        TEST #255
        JUMP Z, dda
        STORE [hv], A
        LOAD A, [sdyl]
        SUB [vdyl]
        STORE [t1], A
        LOAD A, [sdyh]
        SBC [vdyh]
        STORE [t2], A
        LOAD A, #1
        STORE [side], A
hit:    LOAD A, [t2]            ; distance in 1/16 cell = (hi << 4) | (lo >> 4)
        CMP #15
        JUMP NC, far
        MUL #16
        STORE [t2], A
        LOAD A, [t1]
        MULH #16
        OR [t2]
        JUMP near
far:    LOAD A, #255
near:   MULH [cosv]             ; fish-eye correction: distance * cos(offset)
        MOVE XL, A
        LOAD XH, #hi(hgt)
        LOAD A, [X]
        STORE [hh], A           ; wall height in pixels
        LOAD A, #100
        SUB [hh]
        STORE [rem], A
        SHR
        STORE [top], A
        LOAD X, #CEIL
        LOAD A, [top]
        CALL emit
        LOAD A, [hv]            ; wall colour by (cell type, side)
        SHL
        ADD [side]
        SHL
        MOVE XL, A
        LOAD XH, #hi(wcol)
        LOAD A, [X+]
        STORE [t1], A
        LOAD A, [X]
        MOVE XL, A
        LOAD XH, [t1]
        LOAD A, [hh]
        CALL emit
        LOAD X, #FLOOR
        LOAD A, [rem]
        SUB [top]
        CALL emit
        LOAD A, [col]
        ADD #1
        STORE [col], A
        CMP #160
        JUMP NZ, cast
        RET

emit:                           ; write A pixels of colour X to the LCD (A = 0: nothing)
        TEST #255
        RET Z
        MOVE C, A
em1:    STORE [LCD_DATA], XH
        STORE [LCD_DATA], XL
        DJNZ em1
        RET

; ---- static screen: black view area, grey status bar with three boxes (drawn once) ----
.macro BOX
        LCDCMD 0x2A
        LCDBYTE 0
        LCDBYTE \1
        LCDBYTE 0
        LCDBYTE (\1 + 39)
        LCDCMD 0x2B
        LCDBYTE 0
        LCDBYTE 130
        LCDBYTE 0
        LCDBYTE 169
        LCDCMD 0x2C
        LOAD X, #\2
        LOAD A, #40
        STORE [t2], A
bx\@:   LOAD A, #40
        CALL emit
        LOAD A, [t2]
        SUB #1
        STORE [t2], A
        JUMP NZ, bx\@
.endm
status_bar:
        LCDCMD 0x2A
        LCDBYTE 0
        LCDBYTE 0
        LCDBYTE 1
        LCDBYTE 0x3F
        LCDCMD 0x2B
        LCDBYTE 0
        LCDBYTE 0
        LCDBYTE 0
        LCDBYTE 239
        LCDCMD 0x2C
        LOAD A, #0
        STORE [t1], A
sb_row: LOAD A, [t1]
        CMP #120
        LOAD X, #0
        JUMP C, sb_c
        LOAD X, #BARC
sb_c:   LOAD A, #160
        CALL emit
        LOAD A, #160
        CALL emit
        LOAD A, [t1]
        ADD #1
        STORE [t1], A
        CMP #240
        JUMP NZ, sb_row
        BOX 20, 0xF800
        BOX 110, 0xFFE0
        BOX 200, 0x07E0
        RET
.include "lib/init_tables.inc"
