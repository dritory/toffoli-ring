; Scrolling text on the LCD: 5x7 font, every font pixel is 4 x 4 LCD pixels, one font column per frame.
; The band (320 x 28 pixels) is streamed down the columns (MADCTL bit 5): 80 font columns x 4 LCD columns.
; ring[] holds the visible font columns; ring[(start+80)&255] receives the next column of the text.
.include "lib/lcd.inc"
FG = 0xFD20
BG = 0x0010
YTOP = 106
.macro ROWBIT
        LOAD A, [cb]            ; next font row bit -> carry
        SHR
        STORE [cb], A
        LOAD X, #BG
        JUMP NC, rb\@
        LOAD X, #FG
rb\@:
.endm
.macro PIX4                     ; 4 pixels of the current colour (8 byte writes)
        STORE [LCD_DATA], XH
        STORE [LCD_DATA], XL
        STORE [LCD_DATA], XH
        STORE [LCD_DATA], XL
        STORE [LCD_DATA], XH
        STORE [LCD_DATA], XL
        STORE [LCD_DATA], XH
        STORE [LCD_DATA], XL
.endm
.data
start:  .byte 0
rp:     .byte 0
cb:     .byte 0
cb0:    .byte 0
rep:    .byte 0
n:      .byte 0
tp:     .byte 0
cc:     .byte 0
t:      .byte 0
t2:     .byte 0
.org 0x0300
txt:    .string "HELLO FROM THE VISIBLE 8-BIT COMPUTER   "
        .byte 0
.org 0x0500
.include "lib/font5x7.inc"
.data
.org 0x0800
ring:   .space 256
.code
        JUMP start_
        RETI
start_: CALL init_tables
        LCDCMD 0x36             ; MADCTL: row/column exchange, cursor walks down first
        LCDBYTE 0x20
frame:  LOAD A, [FRAME]
        TEST #1
        JUMP Z, frame
        LCDCMD 0x2A             ; columns 0..319
        LCDBYTE 0
        LCDBYTE 0
        LCDBYTE 1
        LCDBYTE 0x3F
        LCDCMD 0x2B             ; rows YTOP .. YTOP+27
        LCDBYTE 0
        LCDBYTE YTOP
        LCDBYTE 0
        LCDBYTE (YTOP + 27)
        LCDCMD 0x2C
        LOAD A, [start]
        STORE [rp], A
        LOAD A, #80
        STORE [n], A
fc:     LOAD XH, #hi(ring)      ; one font column
        LOAD XL, [rp]
        LOAD A, [X+]
        STORE [cb0], A
        STORE [rp], XL          ; XL wraps at 256: the ring
        LOAD A, #4
        STORE [rep], A
rep4:   LOAD A, [cb0]
        STORE [cb], A
        ROWBIT
        PIX4
        ROWBIT
        PIX4
        ROWBIT
        PIX4
        ROWBIT
        PIX4
        ROWBIT
        PIX4
        ROWBIT
        PIX4
        ROWBIT
        PIX4
        LOAD A, [rep]
        SUB #1
        STORE [rep], A
        JUMP NZ, rep4
        LOAD A, [n]
        SUB #1
        STORE [n], A
        JUMP NZ, fc
        ; ---- scroll by one font column ----
        CALL next_col
        STORE [t], A
        LOAD A, [start]
        ADD #80
        MOVE XL, A
        LOAD XH, #hi(ring)
        LOAD A, [t]
        STORE [X], A
        LOAD A, [start]
        ADD #1
        STORE [start], A
        JUMP frame

next_col:                       ; A = next font column of the text
        LOAD A, [cc]
        CMP #5
        JUMP NZ, glyph
        LOAD A, #0              ; 6th column: blank, then the next character
        STORE [cc], A
        LOAD A, [tp]
        ADD #1
        STORE [tp], A
        LOAD A, #0
        RET
glyph:  LOAD XH, #hi(txt)
        LOAD XL, [tp]
        LOAD A, [X]
        TEST #255
        JUMP NZ, havech
        LOAD A, #0              ; end of text: start again
        STORE [tp], A
        JUMP glyph
havech: SUB #32
        STORE [t], A
        MULH #5                 ; 16-bit glyph offset = char * 5
        ADD #hi(font)
        STORE [t2], A
        LOAD A, [t]
        MUL #5
        ADD [cc]
        MOVE XL, A
        LOAD A, [t2]
        ADC #0
        MOVE XH, A
        LOAD A, [X]
        STORE [t], A
        LOAD A, [cc]
        ADD #1
        STORE [cc], A
        LOAD A, [t]
        RET
.include "lib/init_tables.inc"
