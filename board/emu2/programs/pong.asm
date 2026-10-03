; Pong on the LCD: 40 x 30 field of 8 x 8 pixel cells.  Left paddle: UP / DOWN buttons (polled from BTN).
; Right paddle: simple AI (moves every second frame).  LED port: left score in the high nibble, right in the low.
; LOOKUP MUL/MULH #8 turn cell coordinates into pixel coordinates (needs the tables).
.include "lib/lcd.inc"
PADH = 6
PADL = 1                          ; left paddle column
PADR = 38                         ; right paddle column
WHITE = 0xFFFF
YELLOW = 0xFFE0
BLACK = 0
.data
pl:     .byte 12                ; top row of the left paddle
pr:     .byte 12
bx:     .byte 20
by:     .byte 15
vx:     .byte 1                 ; +1 or 255 (-1)
vy:     .byte 1
nx:     .byte 0
ny:     .byte 0
sl:     .byte 0
sr:     .byte 0
par:    .byte 0
t:      .byte 0
rx:     .byte 0
ry:     .byte 0
rw:     .byte 0
rh:     .byte 0
cells:  .byte 0
.code
        JUMP start
        RETI                    ; interrupt vector: unused here
start:  CALL init_tables
        LOAD X, #WHITE
        CALL pl_draw
        CALL pr_draw
        LOAD X, #YELLOW
        CALL draw_ball
frame:  LOAD A, [FRAME]
        TEST #1
        JUMP Z, frame
update:
        ; ---- player ----
        LOAD A, [BTN]
        TEST #1
        JUMP NZ, p_up
        TEST #2
        JUMP NZ, p_dn
        JUMP ai
p_up:   LOAD A, [pl]
        TEST #255
        JUMP Z, ai
        CALL pl_erase
        LOAD A, [pl]
        SUB #1
        JUMP p_set
p_dn:   LOAD A, [pl]
        CMP #(30 - PADH)
        JUMP NC, ai
        CALL pl_erase
        LOAD A, [pl]
        ADD #1
p_set:  STORE [pl], A
        CALL pl_draw
        ; ---- right paddle AI, every second frame ----
ai:     LOAD A, [par]
        XOR #1
        STORE [par], A
        JUMP Z, ball
        LOAD A, [pr]
        ADD #2
        STORE [t], A
        LOAD A, [by]
        CMP [t]
        JUMP C, ai_up           ; ball above the paddle centre
        LOAD A, [t]
        ADD #1
        STORE [t], A
        LOAD A, [by]
        CMP [t]
        JUMP LE, ball           ; ball level with the centre
        LOAD A, [pr]
        CMP #(30 - PADH)
        JUMP NC, ball
        CALL pr_erase
        LOAD A, [pr]
        ADD #1
        JUMP ai_set
ai_up:  LOAD A, [pr]
        TEST #255
        JUMP Z, ball
        CALL pr_erase
        LOAD A, [pr]
        SUB #1
ai_set: STORE [pr], A
        CALL pr_draw
        ; ---- ball ----
ball:   LOAD X, #BLACK
        CALL draw_ball
        LOAD A, [by]
        ADD [vy]
        CMP #30                 ; unsigned: also catches -1
        JUMP C, vok
        LOAD A, #0
        SUB [vy]
        STORE [vy], A           ; bounce off top / bottom
        LOAD A, [by]
        ADD [vy]
vok:    STORE [ny], A
        LOAD A, [bx]
        ADD [vx]
        STORE [nx], A
        CMP #PADL
        JUMP Z, hit_l
        CMP #PADR
        JUMP Z, hit_r
        JUMP bmove
hit_l:  LOAD A, [ny]
        SUB [pl]
        CMP #PADH               ; carry: 0 <= ny - pl < PADH
        JUMP NC, miss_l
        JUMP bounce
hit_r:  LOAD A, [ny]
        SUB [pr]
        CMP #PADH
        JUMP NC, miss_r
bounce: LOAD A, #0
        SUB [vx]
        STORE [vx], A
        LOAD A, [bx]
        ADD [vx]
        STORE [nx], A
bmove:  LOAD A, [nx]
        STORE [bx], A
        LOAD A, [ny]
        STORE [by], A
bdraw:  LOAD X, #YELLOW
        CALL draw_ball
        JUMP frame
miss_l: LOAD A, [sr]
        ADD #1
        STORE [sr], A
        LOAD A, #255            ; serve towards the left player
        JUMP serve
miss_r: LOAD A, [sl]
        ADD #1
        STORE [sl], A
        LOAD A, #1
serve:  STORE [vx], A
        LOAD A, #20
        STORE [bx], A
        LOAD A, #15
        STORE [by], A
        LOAD A, [RNG]
        TEST #1
        LOAD A, #1
        JUMP NZ, sv
        LOAD A, #255
sv:     STORE [vy], A
        LOAD A, [sl]
        SHL
        SHL
        SHL
        SHL
        OR [sr]
        STORE [LED], A
        JUMP bdraw

; ---- drawing ----
pl_erase:
        LOAD X, #BLACK
pl_draw_x:
        LOAD A, [pl]
        STORE [ry], A
        LOAD A, #PADL
        JUMP draw_pad
pl_draw:
        LOAD X, #WHITE
        JUMP pl_draw_x
pr_erase:
        LOAD X, #BLACK
pr_draw_x:
        LOAD A, [pr]
        STORE [ry], A
        LOAD A, #PADR
        JUMP draw_pad
pr_draw:
        LOAD X, #WHITE
        JUMP pr_draw_x

draw_ball:                      ; X = colour; ball cell ([bx],[by])
        LOAD A, [by]
        STORE [ry], A
        LOAD A, [bx]
        STORE [rx], A
        LOAD A, #1
        STORE [rh], A
        JUMP draw_rect1
draw_pad:                       ; A = column, [ry] = top row, X = colour
        STORE [rx], A
        LOAD A, #PADH
        STORE [rh], A
draw_rect1:
        LOAD A, #1
        STORE [rw], A
draw_rect:                      ; rect in cells ([rx],[ry],[rw],[rh]), X = RGB565 colour
        LCDCMD 0x2A
        LOAD A, [rx]
        MULH #8
        STORE [LCD_DATA], A
        LOAD A, [rx]
        MUL #8
        STORE [LCD_DATA], A
        LOAD A, [rx]
        ADD [rw]
        SUB #1
        STORE [t], A
        MULH #8
        STORE [LCD_DATA], A
        LOAD A, [t]
        MUL #8
        ADD #7
        STORE [LCD_DATA], A
        LCDCMD 0x2B
        LCDBYTE 0
        LOAD A, [ry]
        MUL #8
        STORE [LCD_DATA], A
        LCDBYTE 0
        LOAD A, [ry]
        ADD [rh]
        SUB #1
        MUL #8
        ADD #7
        STORE [LCD_DATA], A
        LCDCMD 0x2C
        LOAD A, [rw]
        MUL [rh]
        STORE [cells], A
cell:   LOAD C, #64
px:     STORE [LCD_DATA], XH
        STORE [LCD_DATA], XL
        DJNZ px
        LOAD A, [cells]
        SUB #1
        STORE [cells], A
        JUMP NZ, cell
        RET
.include "lib/init_tables.inc"
