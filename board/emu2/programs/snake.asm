; Snake on the LCD: 16 x 15 board, 16 x 16 pixel cells (256 x 240 of the 320 x 240 screen).
; Buttons arrive by interrupt (cause -> [pend]); the game steps every STEP_TICKS 60 Hz ticks.
; Cell index = y*16+x (fits a byte).  Snake body is a 256-entry ring buffer of cell indices.
; LED port shows the score.
.include "lib/lcd.inc"
STEP_TICKS = 8
GREEN = 0x07E0
RED   = 0xF800
WHITE = 0xFFFF
.data
dir:    .byte 0                 ; 1 up 2 down 4 left 8 right
pend:   .byte 0                 ; button presses since last move (set by the interrupt)
head:   .byte 0                 ; cell index of the head
nh:     .byte 0                 ; new head cell
hptr:   .byte 0                 ; ring buffer index of the head
tptr:   .byte 0                 ; ring buffer index of the tail
score:  .byte 0
tc:     .byte 0                 ; ticks until next step
dc_idx: .byte 0
amask:  .byte 0
pf:     .byte 0
over:   .byte 0
.org 0x0300
body:   .space 256
.org 0x0400
board:  .space 240              ; 0 empty, 1 snake, 2 food
.code
        JUMP start
        JUMP irq                ; interrupt vector
irq:    PUSH A
        LOAD A, [IRQ_CAUSE]
        OR [pend]
        STORE [pend], A
        POP A
        RETI

start:  LOAD A, #0
        STORE [LED], A
        LOAD A, #8              ; moving right
        STORE [dir], A
        LOAD A, #STEP_TICKS
        STORE [tc], A
        ; initial snake: cells 115,116,117 (row 7, x = 3..5)
        LOAD A, #117
        STORE [head], A
        LOAD A, #2
        STORE [hptr], A
        LOAD XH, #hi(body)
        LOAD XL, #0
        LOAD A, #115
        STORE [X+], A
        LOAD A, #116
        STORE [X+], A
        LOAD A, #117
        STORE [X+], A
        LOAD XH, #hi(board)
        LOAD XL, #115
        LOAD A, #1
        STORE [X+], A
        STORE [X+], A
        STORE [X+], A
        LOAD X, #GREEN
        LOAD A, #115
        CALL draw_cell
        LOAD X, #GREEN
        LOAD A, #116
        CALL draw_cell
        LOAD X, #GREEN
        LOAD A, #117
        CALL draw_cell
        LOAD A, #122            ; first food, fixed
        CALL put_food
        LOAD A, #15
        STORE [IRQ_EN], A       ; all four buttons interrupt

frame:  LOAD A, [FRAME]
        TEST #1
        JUMP Z, frame
        LOAD A, [tc]
        SUB #1
        STORE [tc], A
        JUMP NZ, frame
        LOAD A, #STEP_TICKS
        STORE [tc], A
step:                           ; one game step starts here
        ; ---- take a turn request from the buttons ----
        LOAD A, [dir]
        TEST #3                 ; moving vertically? then only left/right are allowed
        LOAD A, #12
        JUMP NZ, am
        LOAD A, #3
am:     STORE [amask], A
        LOAD A, [pend]
        STORE [pf], A
        LOAD A, #0
        STORE [pend], A         ; a press landing between these two lines is lost
        LOAD A, [pf]
        AND [amask]
        JUMP Z, move
        STORE [pf], A
        TEST #1
        LOAD A, #1
        JUMP NZ, setd
        LOAD A, [pf]
        TEST #2
        LOAD A, #2
        JUMP NZ, setd
        LOAD A, [pf]
        TEST #4
        LOAD A, #4
        JUMP NZ, setd
        LOAD A, #8
setd:   STORE [dir], A
        ; ---- compute the new head cell ----
move:   LOAD A, [dir]
        TEST #1
        JUMP NZ, mv_up
        TEST #2
        JUMP NZ, mv_dn
        TEST #4
        JUMP NZ, mv_lf
        LOAD A, [head]          ; right
        AND #15
        CMP #15
        JUMP Z, dead
        LOAD A, [head]
        ADD #1
        JUMP moved
mv_up:  LOAD A, [head]
        SUB #16
        JUMP C, dead
        JUMP moved
mv_dn:  LOAD A, [head]
        ADD #16
        CMP #240
        JUMP NC, dead
        JUMP moved
mv_lf:  LOAD A, [head]
        AND #15
        JUMP Z, dead
        LOAD A, [head]
        SUB #1
moved:  STORE [nh], A
        LOAD XH, #hi(board)
        MOVE XL, A
        LOAD A, [X]
        CMP #1
        JUMP Z, dead
        CMP #2
        JUMP Z, eat
        ; ---- plain move: free the tail ----
        LOAD XH, #hi(body)
        LOAD XL, [tptr]
        LOAD A, [X]             ; tail cell
        MOVE XL, A
        LOAD XH, #hi(board)
        LOAD A, #0
        STORE [X], A
        MOVE A, XL
        LOAD X, #0
        CALL draw_cell
        LOAD A, [tptr]
        ADD #1
        STORE [tptr], A
        CALL new_head
        JUMP frame
eat:    LOAD A, [score]
        ADD #1
        STORE [score], A
        STORE [LED], A
        CALL new_head
rf:     LOAD A, [RNG]           ; random free cell for the next food
        CMP #240
        JUMP NC, rf
        STORE [dc_idx], A
        LOAD XH, #hi(board)
        MOVE XL, A
        LOAD A, [X]
        TEST #255
        JUMP NZ, rf
        LOAD A, [dc_idx]
        CALL put_food
        JUMP frame

dead:   LOAD A, #0
        STORE [IRQ_EN], A
        LOAD A, #1
        STORE [over], A
        LOAD X, #WHITE
        LOAD A, [head]
        CALL draw_cell
        JUMP $

new_head:                       ; push [nh] as the new head and draw it
        LOAD A, [hptr]
        ADD #1
        STORE [hptr], A
        MOVE XL, A
        LOAD XH, #hi(body)
        LOAD A, [nh]
        STORE [X], A
        MOVE XL, A
        LOAD XH, #hi(board)
        LOAD A, #1
        STORE [X], A
        LOAD A, [nh]
        STORE [head], A
        LOAD X, #GREEN
        JUMP draw_cell          ; tail call

put_food:                       ; A = cell: mark food on the board and draw it
        STORE [dc_idx], A
        LOAD XH, #hi(board)
        MOVE XL, A
        LOAD A, #2
        STORE [X], A
        LOAD A, [dc_idx]
        LOAD X, #RED
        JUMP draw_cell

draw_cell:                      ; A = cell index, X = RGB565 colour; fills a 16x16 window
        STORE [dc_idx], A
        LCDCMD 0x2A             ; column window: x*16 .. x*16+15
        LCDBYTE 0
        LOAD A, [dc_idx]
        AND #15
        SHL
        SHL
        SHL
        SHL
        STORE [LCD_DATA], A
        LCDBYTE 0
        LOAD A, [dc_idx]
        AND #15
        SHL
        SHL
        SHL
        SHL
        ADD #15
        STORE [LCD_DATA], A
        LCDCMD 0x2B             ; row window: y*16 .. y*16+15
        LCDBYTE 0
        LOAD A, [dc_idx]
        AND #0xF0
        STORE [LCD_DATA], A
        LCDBYTE 0
        LOAD A, [dc_idx]
        AND #0xF0
        ADD #15
        STORE [LCD_DATA], A
        LCDCMD 0x2C
        LOAD C, #0              ; 256 pixels
px:     STORE [LCD_DATA], XH
        STORE [LCD_DATA], XL
        DJNZ px
        RET
